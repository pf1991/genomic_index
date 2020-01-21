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
import math 

class Index():

    def __init__(self):

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))

        #directory with files to index
        self.to_index = os.path.join(BASE_DIR, 'files/to_index')

        # files
        self.config_file = os.path.join(BASE_DIR, 'files/config.pickle')
        self.unique_kmers_file = os.path.join(BASE_DIR, 'files/unique_kmers.pickle')
        self.files_repo_file = os.path.join(BASE_DIR, 'files/files.pickle')
        self.inverted_index_file = os.path.join(BASE_DIR, 'files/inverted.pickle')
        self.repository_path = os.path.join(BASE_DIR, 'files/repo')
        self.inverted_repository_path = os.path.join(BASE_DIR, 'files/inverted')
        
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

    def search(self, record_str):

        start = time.time()
        # check consistency
        self._check_index_ready()

        #get unique k-mers from ref
        test_strings = self._generate_unique_kmers(record_str)
        # print("Query K-mers:", test_strings)

        #result buffer
        files = {}

        # check which window size should be used to calculate the score 
        l = len(test_strings)
        window_sizes = self.config.element['WINDOW_SIZES'].copy()
        window_sizes.sort(reverse=True)
        max_kmer_size = None
        for w in window_sizes:
            if w <= len(record_str):
                max_kmer_size = w
                break
        if max_kmer_size is None:
            return []

        #test each k-meer (substring of the dna sequence)
        len_kmer_last = None

        results = self.inverted_index.get_posting_list(test_strings)
        if not results:
            return []

        file_found = {}
        for kmer in results.keys():
            
            #if longer k-meers are found let's avoid the smaller ones
            # if(len_kmer_last is not None and len(kmer) < len_kmer_last):
            #     break
            # len_kmer_last = len(kmer)

            files_in_posting = {}

            file_keys = list(results[kmer].keys())

            for file_id in file_keys:
                
                # discard lower kmers from the score
                if file_id in file_found and len(kmer) != file_found[file_id]:
                    continue
                file_found[file_id] = len(kmer)

                if file_id not in files:
                    files[file_id] = {
                        'score': 0,
                        'max_kmers': 0,
                        'search_length': len(record_str),
                        'max_kmer_length': max_kmer_size,
                        'exact_match': False,
                        'locations': []
                    }
                
                #get strings from reference and insert them on the result array for evaluation
                if self.repository.element[file_id]['ref_id']:
                    ref_id = self.repository.element[file_id]['ref_id']
                    count = 0
                    for pos in results[kmer][file_id]:
                        pos_f = pos + len(kmer)
                        #convert to array
                        results[kmer][file_id][count] = [results[kmer][file_id][count]]
                        #extend structure to add re
                        results[kmer][file_id][count].extend([pos_f, self._get_from_ref(ref_id, pos, pos_f)]) 
                        count = count + 1

                # calculate score
                # 
                number_of_hits = len(results[kmer][file_id])
                n_kmers_to_exact_match =  len(record_str) - len(kmer)  + 1
                weight = 1 / 10**(max_kmer_size - len(kmer))
                score = number_of_hits * weight / n_kmers_to_exact_match
                # score = weight / n_kmers_to_exact_match
                files[file_id]['score'] = files[file_id]['score'] + score
                if max_kmer_size == len(kmer):
                    files[file_id]['max_kmers'] = files[file_id]['max_kmers'] + 1
                if files[file_id]['max_kmers'] == ( len(record_str) - max_kmer_size  + 1) :
                    files[file_id]['exact_match'] = True
                files[file_id]['locations'].extend(results[kmer][file_id])

        #prepare output and sort results
        l = []
        [l.append({'file':k,'value':v}) for k,v in files.items()]
        l.sort(key=lambda x: x['value']['score'], reverse=True)
        
        print("Search time:", time.time() - start)
        
        return l


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

        # index
        # index string from the beginning to a max pos defined on the configuration
        if self.config.element['MAX_POS']:
            record_str = record_str[1:self.config.element['MAX_POS']]
        
        self._index(record_str, file_id)

        self._save()

        print('-Reference indexed!')
        return len(record_str)


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
                    window_sizes, batch_size, n_bases_to_hash = None):
        
        if n_bases_to_hash is not None and min(window_sizes) <= n_bases_to_hash:
            raise Exception('n_bases_to_hash should be smaller than the smallest k-mer window!')

        #reset all elements
        self._init_elements()

        #clear up repository
        self.repository.clear()
        self.inverted_index.clear()

        self.inverted_index.element['N_BASES_TO_HASH'] = n_bases_to_hash

        #update configuration values
        self.config.update(max_pos, max_samples_to_index,
                    window_sizes, batch_size)

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
        # repository (files references)
        self.repository = Repository(self.files_repo_file, 'repo', self.repository_path)     
        # inverted index
        self.inverted_index = InvertedIndex(self.inverted_index_file, 'inverted', self.inverted_repository_path)


    def _load(self):

        print('- Loading index components from disk/ram...')

        print('[Config]')
        self.config.get()

        print('[Inverted Index]')
        self.inverted_index.get()

        print('[Loading Repository]')
        self.repository.get()


    def _save(self):
        print('- Saving index...')
        self.repository.save()
        self.inverted_index.save()
        # self.reference.save()
        self.config.element['BUILD_OK'] = True
        self.config.save()


    def _index(self, record_str, file_id, reference_id = None):
        print('- Indexing sequence...')
        record_str = str(record_str)

        batch = []
        batch_count = 0

        with open('_indexed_%s.txt' % file_id, 'w') as file:
            file.write(record_str)
        
        print("[%s]" % file_id)
        l = len(record_str)
        record_str = None

        redis_t = 0
        start = time.time()
        fragment_time = 0

        f = open('_indexed_%s.txt' % file_id, 'rb')

        for i in range(0, l):            

            for w in  self.config.element['WINDOW_SIZES']:
                
                n_steps = (l - w)
                if(i > n_steps):
                    break

                f.seek(i)
                kmer = f.read(w).decode(encoding='utf-8')
                
                # skip bad zones
                if 'N' in kmer:
                    continue
                
                #populate batch
                batch.append((kmer, file_id, i))
                batch_count = batch_count + 1

            # deploy batch 
            if(batch_count > self.config.element['BATCH_SIZE']):            
                
                temp = time.time()
                
                self._submit_index_batch(batch)
                redis_t = time.time() - temp
                batch = []
                batch_count = 0
                print("Progress (%d/%d), total %.3f s, time to process a batch %.3f s" % (l, i, time.time()-start, redis_t), self.inverted_index.get_time())
                fragment_time = 0
                self.inverted_index.reset_time()

        #close file
        f.close()

        #submit the remainning items
        if(batch_count > 0):
            self._submit_index_batch(batch)

        # add vcf file to repository
        self.repository.add(file_id, 'VCF file', None, None, reference_id)

    def _submit_index_batch(self, batch):
        #order keys, biggers first
        batch.sort(key=lambda x: len(x[0]), reverse=True)
        result = self.inverted_index.process_batch(batch)
        if(not result):
            raise Exception('Batch not processed! Index failed to build!')

    def _get_from_ref(self, id, start, stop):
        self._check_index_ready()
        f = open('_indexed_%s.txt' % id, 'rb')
        f.seek(start)
        kmer = f.read(stop - start).decode(encoding='utf-8')
        f.close()

        return kmer


    def _generate_unique_kmers(self, record_str):
        self._check_index_ready()
        print('- Generating unique kmers from record...')

        l = len(record_str)
        unique_kmers = {}

        for i in range(0, l):
            
            for w in  self.config.element['WINDOW_SIZES']:
                
                n_steps = (l - w)
                if(i > n_steps):
                    break

                kmer = record_str[i:i+w]
                # unique_kmers[kmer] = 1
                if kmer not in unique_kmers:
                    unique_kmers[kmer] = 1
                else:
                    unique_kmers[kmer] = unique_kmers[kmer] + 1

        l = list(unique_kmers.keys())

        #sort kmers, biggers first
        l.sort(key=lambda x: len(x), reverse=True)

        return l


    
