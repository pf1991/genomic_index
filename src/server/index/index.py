import os
import sys
from Bio import SeqIO
from .bloom import Bloom
from .inverted import InvertedIndex
from .repository import Repository
from .base_element import BaseElement
from .config import Config
import time
import vcf
from pyfaidx import FastaVariant
from gzip import open as gzopen
from .settings import REF_FILE_PATH

class Index():

    def __init__(self):

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))

        #directory with files to index
        self.to_index = os.path.join(BASE_DIR, 'files/to_index')

        # files
        self.config_file = os.path.join(BASE_DIR, 'files/config.pickle')
        self.unique_kmers_file = os.path.join(BASE_DIR, 'files/unique_kmers.pickle')
        self.reference_file = os.path.join(BASE_DIR, 'files/reference.pickle')
        self.bloom_filters_file = os.path.join(BASE_DIR, 'files/bloom_filter.pickle')
        self.files_repo_file = os.path.join(BASE_DIR, 'files/files.pickle')
        self.inverted_index_file = os.path.join(BASE_DIR, 'files/inverted.pickle')
        self.reference_file_path = os.path.join(BASE_DIR, REF_FILE_PATH)

        #init 
        self._init_elements()

        #load elements from disk
        self._load()


    #===============================================
    # Private functions
    #===============================================


    def summary(self):
        #check if index is loaded and ok!     
        self._check_index_ready()
        
        #load summaries
        self.config.summary()
        self.inverted_index.summary()
        self.repository.summary()
        self.bloom_filters.summary()


    def search(self, record_str):
        
        # check consistency
        self._check_index_ready()

        start = time.time()

        #get unique k-mers from ref
        test_strings = self._generate_unique_kmers(record_str)

        print("Query K-mers:", test_strings)

        files = {}
        l = len(test_strings)
        len_kmer_last = None
        flag_found = None
        for kmer in test_strings:

            if(flag_found and len(kmer) < len_kmer_last):
                break
            
            len_kmer_last = len(kmer)

            #verify if bloom filters are working as expected
            hash = self.bloom_filters.element.check(kmer)
            if(not hash):
                continue

            #get posting list
            posting_list = self.inverted_index.get_posting_list(hash, kmer)
            if(not posting_list):
                continue

            #kmer found!
            flag_found = True

            files_in_posting = {}
            file_keys = list(posting_list.keys())
            for k in file_keys:
                files_in_posting[k] = {}

            for f in files_in_posting.keys():
                if f not in files:
                    files[f] = {
                        'score': 0,
                        'locations': []
                    }
                
                score = len(posting_list[f]) * (len(kmer) / max( self.config.element['WINDOW_SIZES']) )
                files[f]['score'] = files[f]['score'] + score
                files[f]['locations'].extend(posting_list[f])

                #get strings from reference
                count = 0
                for pos in files[f]['locations']:
                    files[f]['locations'][count] = pos + (self.reference.element[pos[0]:pos[1]], score)
                    count = count + 1

            #prepare output and sort results
            l = []
            [l.append({'file':k,'value':v}) for k,v in files.items()]
            l.sort(key=lambda x: x['value']['score'], reverse=True)

            return l


    def test_consistency(self):
        
        self._check_index_ready()

        #get unique k-mers from ref
        test_strings = self._generate_unique_kmers(self.reference.element)
        for kmer in test_strings:

            #verify if bloom filters are working as expected
            hash = self.bloom_filters.element.check(kmer)
            if(not hash):
                print("Bloom filters failed", kmer, hash)
                continue

            #get posting list
            posting_list = self.inverted_index.get_posting_list(hash, kmer)
            if(not posting_list):
                print("Posting list failed", kmer, hash)
                continue

            # has file?
            if('ref' not in posting_list):
                print("File not found failed", kmer, hash)
                continue

            # check values in posting list
            for pos in posting_list['ref']:
                ref_str = self._get_from_ref(pos[0], pos[1])
                if(ref_str != kmer):
                    print("Ref is not consistent", kmer, ref_str, pos[0], pos[1])
                    continue


    def index_files(self):

        self._check_index_ready()

        for filename in os.listdir(self.to_index):
            if filename.endswith(".vcf.gz"): 
                file_to_index = os.path.join(self.to_index, filename)

                samples = vcf.Reader(filename=file_to_index).samples[0: self.config.element['MAX_FILES_TO_INDEX']]

                count = 0
                last_time = None
                elapsed = 0
                for s in samples:
                    if(last_time):
                        elapsed = time.time() - last_time
                    last_time = time.time()
                    print('Samples: ', (count/len(samples)*100), '%', elapsed, 's')
                    print('-Mapping VCF to reference...')
                    consensus = FastaVariant(self.reference_file_path, file_to_index, sample=s, het=True, hom=True)
                    self._index_sequence(consensus['1'][1:self.config.element['MAX_POS']], s)
                    count = count + 1
        
        #save structures to ram and disk
        self._save()
                    

    def generate(self, max_pos, seq_ids, max_files_to_index,
                    window_sizes, sept_unit, max_bloom_false_prob):
        
        self._init_elements()
        self.config.update(max_pos, seq_ids, max_files_to_index,
                    window_sizes, sept_unit, max_bloom_false_prob)

        # generate index
        print('- Generating index...')

        file_id = 'ref'
        path = ''

        #load file list
        self.reference.element = ""
        key = self.repository.add(file_id, 'reference', path)
        for seq_record in SeqIO.parse(gzopen(self.reference_file_path,'rt'), "fasta"):

            if(seq_record.id not in  self.config.element['SEQ_IDS']):
                print('Not in SEQ_IDS. Skiping...')
                continue

            record_str = str(seq_record.seq)

            self.reference.element = self.reference.element + record_str

            #index
            self._index_sequence(record_str, file_id)

            #only first chromossome
            break

        #save structures to ram and disk
        self._save()


    #===============================================
    # Private functions
    #===============================================

    def _check_index_ready(self):
        if(not self.config.element['BUILD_OK']):
            ValueError('Index is not build! Please generate it with generate()')


    def _init_elements(self):

        self.config = Config(self.config_file,'config') # char

        # bloom filters
        # the number is actualy lower, genomes between genomes can differ in 2% between the
        max_inserts = int( len(self.config.element['WINDOW_SIZES']) * self.config.element['MAX_POS'] * 1.02 ) 

        self.bloom_filters = Bloom(self.bloom_filters_file, 'bloom', max_inserts, self.config.element['MAX_BLOOM_FALSE_POS_PROB'])
        self.bloom_filters.init()

        # repository (files references)
        self.repository = Repository(self.files_repo_file, 'repo')
        # inverted index
        self.inverted_index = InvertedIndex(self.inverted_index_file, 'inverted')
        #reference string
        self.reference = BaseElement(self.reference_file,'ref') # char


    def _load(self):

        print('- Loading index components from disk/ram...')
        print('[Config]')
        self.config.get()
        print('[Inverted Index]')
        self.inverted_index.get()
        print('[Loading Repository]')
        self.repository.get()
        print('[Loading Bloom Filter]')
        self.bloom_filters.get()
        print('[Loading Reference]')
        self.reference.get()


    def _save(self):

        start = time.time()

        print('- Saving index...')
        self.bloom_filters.save()
        self.repository.save()
        self.inverted_index.save()
        self.reference.save()
        self.config.element['BUILD_OK'] = True
        self.config.save()


    def _index_sequence(self, record_str, file_id):

        print('-Indexing sequence...')

        record_str = str(record_str)
        
        start = time.time()
        l = len(record_str)

        print("[%s]" % file_id)

        for i in range(1, l, self.config.element['STEPS_UNIT']):            
            if(i >  self.config.element['MAX_POS']):
                    break
            
            for w in  self.config.element['WINDOW_SIZES']:
                n_steps = (l - w)
                if(i > n_steps):
                    break

                kmer = record_str[i:i+w]       
                hash = self.bloom_filters.add(kmer)
                self.inverted_index.add(hash, kmer, file_id, i, i + w)        

            if(i % (self.config.element['MAX_POS']/50) == 0):
                print("#", end='', flush=True)
        print()

        self.repository.add(file_id, '', '')


    def _get_from_ref(self, start, stop):
        self._check_index_ready()

        return self.reference.element[start:stop]


    def _generate_unique_kmers(self, record_str):

        self._check_index_ready()

        print('- Generating unique kmers from record...')

        l = len(record_str)
        unique_kmers = {}

        for i in range(0, l,  self.config.element['STEPS_UNIT']):
        
            if(i >  self.config.element['MAX_POS']):
                    break
            
            for w in  self.config.element['WINDOW_SIZES']:
                
                n_steps = (l - w)
                if(i > n_steps):
                    break

                kmer = record_str[i:i+w]
                # unique_kmers[kmer] = 1
                if kmer not in unique_kmers:
                    unique_kmers[kmer] = 1

        l = list(unique_kmers.keys())

        #sort kmers, biggers first
        l.sort(key=lambda x: len(x), reverse=True)

        return l


    
