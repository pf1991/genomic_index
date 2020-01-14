import os
import sys
from Bio import SeqIO
import time
import vcf
from pyfaidx import FastaVariant
from gzip import open as gzopen
from .inverted import InvertedIndex
from .repository import Repository
from .base_element import BaseElement
from .config import Config
from .reference import Reference
import math 

class Index():

    def __init__(self, redis_host='redis'):

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))

        #directory with files to index
        self.to_index = os.path.join(BASE_DIR, 'files/to_index')

        # files
        self.config_file = os.path.join(BASE_DIR, 'files/config.pickle')
        self.unique_kmers_file = os.path.join(BASE_DIR, 'files/unique_kmers.pickle')
        self.reference_file = os.path.join(BASE_DIR, 'files/reference.pickle')
        self.files_repo_file = os.path.join(BASE_DIR, 'files/files.pickle')
        self.inverted_index_file = os.path.join(BASE_DIR, 'files/inverted.pickle')
        self.repository_path = os.path.join(BASE_DIR, 'files/repo')
        self.inverted_repository_path = os.path.join(BASE_DIR, 'files/inverted')

        self.redis_host = redis_host
        
        #init 
        self._init_elements()

        #load elements from disk
        self._load()

        self._search_redis_t = 0
        self._search_redis_n = 0


    #===============================================
    # public functions
    #===============================================

    def summary(self):

        #check if index is loaded and ok!     
        self._check_index_ready()
        
        #load summaries
        self.config.summary()
        self.inverted_index.summary()
        self.repository.summary()
        self.reference.summary()

    def search(self, record_str):

        start = time.time()
        # check consistency
        self._check_index_ready()

        #get unique k-mers from ref
        test_strings = self._generate_unique_kmers(record_str)
        print("Query K-mers:", test_strings)

        #result buffer
        files = {}

        #test each k-meer (substring of the dna sequence)
        l = len(test_strings)
        len_kmer_last = None
        flag_found = None
        for kmer in test_strings:

            #if longer k-meers are found let's avoid the smaller ones
            if(flag_found and len(kmer) < len_kmer_last):
                break   
            len_kmer_last = len(kmer)

            # get posting list
            posting_list = None
            posting_list = self.inverted_index.get_posting_list(kmer)

            if(not posting_list):
                # print('Not found posting:', kmer)
                continue

            # kmer found!
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
                
                #get strings from reference and insert them on the result array for evaluation
                if self.repository.element[f]['ref_id']:
                    ref_id = self.repository.element[f]['ref_id']
                    count = 0
                    for pos in posting_list[f]:
                        # str index starts at 0 but on vcf files at 1
                        pos_f = pos + len(kmer)
                        print(posting_list[f][count])
                        posting_list[f][count] = [posting_list[f][count]]
                        posting_list[f][count].extend([pos_f, self.reference.element[ref_id]['sequence'][pos:pos_f]]) 
                        count = count + 1

                #calculate score
                score = len(posting_list[f]) / ( max( self.config.element['WINDOW_SIZES']) + 1 - len(kmer) )
                files[f]['score'] = files[f]['score'] + score
                files[f]['locations'].extend(posting_list[f])

        #prepare output and sort results
        l = []
        [l.append({'file':k,'value':v}) for k,v in files.items()]
        l.sort(key=lambda x: x['value']['score'], reverse=True)
        
        print("Search time:", time.time() - start)
        
        return l


    def test_consistency(self):
        
        self._check_index_ready()

        #get unique k-mers from ref
        test_strings = self._generate_unique_kmers(self.reference.element)
        for kmer in test_strings:


            #get posting list
            posting_list = self.inverted_index.get_posting_list(kmer)
            if(not posting_list):
                print("Posting list failed", kmer, hash)
                continue

            # has file?
            if('ref' not in posting_list):
                print("File not found failed", kmer, hash)
                continue

            # # check values in posting list
            # for pos in posting_list['ref']:
            #     ref_str = self._get_from_ref(pos[0], pos[1])
            #     if(ref_str != kmer):
            #         print("Ref is not consistent", kmer, ref_str, pos[0], pos[1])
            #         continue


    def index_reference(self, file_id, file_path):

        print('- Indexing reference:', file_id, file_path)

        if(not file_path.endswith('.fa.gz')):
            raise Exception('Format not supported! Please use a fa.gz file')

        if not os.path.exists(file_path):
            raise Exception('File does not exists!')

        record_str = ""

        # we start by saving the file, moving it to a new location
        self.repository.add(file_id, 'reference file', file_path, '.fa.gz', file_id)

        #tem_seq_ids = self.config.element['SEQ_IDS'].copy()
        for seq_record in SeqIO.parse(gzopen(file_path,'rt'), "fasta"):
            print('Looking at seq id:', seq_record.id)
            # references has 1 cromossome per record, so here we specify which chromossomes should be indexed
            # if this configuration is empty everything will be indexed
            # Used to make it easier to test the indexing on large genomes
            # if(len(self.config.element['SEQ_IDS']) > 0 and len(tem_seq_ids) == 0):
            #     break
            # elif(len(self.config.element['SEQ_IDS']) > 0 and seq_record.id not in self.config.element['SEQ_IDS']):
            #     print('Not in SEQ_IDS. Skiping...')
            #     continue
            # elif(len(self.config.element['SEQ_IDS']) > 0):
            #     tem_seq_ids.pop(0)
            
            # convert record to a string
            record_str = record_str + str(seq_record.seq)

            # concatenate string
            #self.reference.element = self.reference.element + record_str

        # index
        # index string from the beginning to a max pos defined on the configuration
        if self.config.element['MAX_POS']:
            self._index(record_str[1:self.config.element['MAX_POS']], file_id)
        else:
            self._index(record_str, file_id)

        # add reference to the reference object
        self.reference.add(file_id, record_str)

        self._save()

        print('-Reference indexed!')


    def index_vcf(self, reference_id, vfc_file_path):

        print('- Indexing file!')
        self._check_index_ready()

        #get reference file path
        reference_file_path = self.repository.get_path(reference_id)
        if(not reference_file_path):
            raise Exception('Reference file path not defined! Perhaps the reference doesnt exist yet and should be indexed first!')

        # check if files are defined!
        # check file extension!
        if(not vfc_file_path.endswith('.vcf.gz')):
            raise Exception('Format not supported! Please use a vcf.gz file')

        if not os.path.exists(vfc_file_path):
            raise Exception('File does not exists!')


        print('Using reference:', reference_id, reference_file_path)
        # for filename in os.listdir(self.to_index):
        #     if filename.endswith(".vcf.gz"): 
        # file_to_index = os.path.join(self.to_index, filename)

        # Getting samples on VFC file
        samples = vcf.Reader(filename=vfc_file_path).samples
        if self.config.element['MAX_SAMPLES_TO_INDEX']:
            samples = samples[0: self.config.element['MAX_SAMPLES_TO_INDEX']]

        # iterate over all sample, reconstruct the sequence and index it!
        # this is a slow process
        count = 0
        last_time = None
        elapsed = 0
        for s in samples:
            if(last_time):
                elapsed = time.time() - last_time
            last_time = time.time()
            print('Samples: ', (count/len(samples)*100), '%', elapsed, 's')
            print('- Reconstructing VCF original sequence...')
            consensus = FastaVariant(reference_file_path, vfc_file_path, sample=s, het=True, hom=True)
            self._index(consensus['1'][1:self.config.element['MAX_POS']], s, reference_id)
            count = count + 1

        #save structures to ram and disk
        self._save()
                    
        print('- File indexed!')

    def set_up(self, max_pos, max_samples_to_index,
                    window_sizes):
        
        #reset all elements
        self._init_elements()

        #clear up repository
        self.repository.clear()
        self.inverted_index.clear()

        #update configuration values
        self.config.update(max_pos, max_samples_to_index,
                    window_sizes)

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

        # the number is actualy lower, genomes between genomes can differ in 2% between the
        max_inserts = int( len(self.config.element['WINDOW_SIZES']) * self.config.element['MAX_POS'] * 1.02 ) 

        # repository (files references)
        self.repository = Repository(self.files_repo_file, 'repo', self.repository_path)
        
        # inverted index
        self.inverted_index = InvertedIndex(self.inverted_index_file, 'inverted', self.inverted_repository_path, self.redis_host)

        #reference string
        self.reference = Reference(self.reference_file,'ref') # char


    def _load(self):

        print('- Loading index components from disk/ram...')

        print('[Config]')
        self.config.get()

        print('[Inverted Index]')
        self.inverted_index.get()

        print('[Loading Repository]')
        self.repository.get()

        print('[Loading Reference]')
        self.reference.get()


    def _save(self):
        print('- Saving index...')
        self.repository.save()
        self.inverted_index.save()
        self.reference.save()
        self.config.element['BUILD_OK'] = True
        self.config.save()


    def _index(self, record_str, file_id, reference_id = None):
        print('- Indexing sequence...')
        record_str = str(record_str)

        batch = {}
        BATCH_LIMIT = 20000
        batch_count = 0

        with open('_indexed_%s.txt' % file_id, 'w') as file:
            file.write(record_str)

        print("[%s]" % file_id)
        l = len(record_str)

        redis_t = 0
        start = time.time()
        for i in range(0, l):            

            for w in  self.config.element['WINDOW_SIZES']:
                n_steps = (l - w)
                if(i > n_steps):
                    break

                kmer = record_str[i:i+w] 
                
                # prepare batch
                inverted_index_fragment = self.inverted_index.add_to_fragment(kmer, file_id, i + 1, i + w + 1)
                batch[kmer] = inverted_index_fragment
                batch_count = batch_count + 1

            # deploy batch 
            if(batch_count > BATCH_LIMIT):
                temp = time.time()
                self._submit_index_batch(batch)
                redis_t = time.time() - temp
                batch = {}
                batch_count = 0
                print("Progress (%d/%d), total %.3f s, time to process a batch %.3f s" % (l, i, time.time()-start, redis_t))


            # if(i % 1000 == 0):
            #     print("Progress (%d/%d), total %.3f s, redis_total_t %.3f s" % (l, i, time.time()-start, redis_t))
            #     start = time.time()
            #     redis_t = 0
        
        #submit the remainning items
        if(batch_count > 0):
            self._submit_index_batch(batch)

        # add vcf file to repository
        self.repository.add(file_id, 'VCF file', None, None, reference_id)

    def _submit_index_batch(self, batch):
        result = self.inverted_index.add_batch(batch)
        if(not result):
            raise Exception('Batch not processed! Index failed to build!')

    def _get_from_ref(self, id, start, stop):
        self._check_index_ready()
        return self.reference.element[id]['sequence'][start:stop]


    def _generate_unique_kmers(self, record_str):
        self._check_index_ready()
        print('- Generating unique kmers from record...')

        l = len(record_str)
        unique_kmers = {}

        for i in range(0, l):
        
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


    
