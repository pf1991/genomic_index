from .base_element import BaseElement
import sys
import os
import pickle
from shutil import rmtree
import redis
import json
import time

class InvertedIndex(BaseElement):

    def __init__(self, filename_path, cache_name, repository_path, n_bases_to_hash = None):

        super().__init__(filename_path, cache_name)

        self.element['N_BASES_TO_HASH'] = n_bases_to_hash
        self._load_redis()
        self.time = [0,0,0,0,0]

    
    def reset_time(self):
        self.time = [0,0,0,0,0]


    def get_time(self):
        return self.time


    def add_to_fragment(self, value, fileid, pos_i):
        temp = time.time()
        fragment = {}
        if value:
            fragment = json.loads(value) 
        self.time[0] = self.time[0] + time.time() - temp

        temp = time.time()
        #init structure if doesnt exists
        if fileid not in fragment:
                fragment[fileid] = []

        if isinstance(pos_i, list):
            fragment[fileid].extend(pos_i)
        else:
            fragment[fileid].append(pos_i)

        self.time[2] = self.time[2] + time.time() - temp

        temp = time.time()
        d = json.dumps(fragment) 
        self.time[3] = self.time[3] + time.time() - temp 

        return d 

    def process_batch(self, batch):     

        keys = [ b[0] for b in batch ]
        if self.element['N_BASES_TO_HASH']:
            return self.process_batch_kmer_collection(keys, batch)
        else:
            return self.process_batch_kmer(keys, batch)
        
    def process_batch_kmer(self, keys, batch):
        batch_to_submit = {}
        values = self.redis.mget(keys)
        count = 0
        for b in batch:
            v = None
            if b[0] in batch_to_submit:
                v = batch_to_submit[b[0]]
            else:
                v = values[count]

            d = self.add_to_fragment(v, b[1], b[2])

            #replace the tupple by the string fragment
            batch_to_submit[b[0]] = d
            count = count + 1

        return self.redis.mset(batch_to_submit)

    def process_batch_kmer_collection(self, keys, batch):
        batch_collections = {}
        
        #init batch collection
        count = 0
        for k in keys:
            name, key = self.split_kmer(k)
            file_id = batch[count][1]

            #init dict if not set
            if(name not in batch_collections):
                batch_collections[name] = {}
            
            #map batches to the corresponding position on the collection
            if key not in batch_collections[name]:
                batch_collections[name][key] = {}

            if file_id not in batch_collections[name][key]:
                batch_collections[name][key][file_id] = []
            
            batch_collections[name][key][file_id].append(batch[count][2])
            count = count + 1
        
        #process each batch collection
        for name in batch_collections.keys():
        
            # get values from redis
            keys = batch_collections[name].keys()    
            values = self.redis.hmget(name, keys)

            # prepare data to submit
            count = 0
            batch_to_submit = {}
            for subkmer in keys:
                
                if values[count]:                 
                    v = values[count]
                else:
                    v = "{}"

                # complement values on v with all values that are about to be processed
                # add several files
                for file_id in batch_collections[name][subkmer].keys():
                    pos = batch_collections[name][subkmer][file_id]
                    v = self.add_to_fragment(v, file_id, pos)
                
                batch_to_submit[subkmer] = v
                
                # replace the tupple by the string fragment               
                count = count + 1
            
            # print('Submitting sub-batch with %d elements', len(batch_to_submit))
            result = self.redis.hmset(name, batch_to_submit)
            if(not result):
                raise Exception('Cannot save sub-batch! Check redis logs!')
        
        return True


    def split_kmer(self, kmer):
        return (kmer[0:self.element['N_BASES_TO_HASH']], kmer[self.element['N_BASES_TO_HASH']:])


    def clear(self):
        # self._load_redis()
        self.element = {}
        self.redis.flushdb()
        self.redis.flushall()
        self.redis.config_resetstat()
        self.redis.slowlog_reset()

    def get_posting_list(self, kmer_list):
        if self.element['N_BASES_TO_HASH']:
            return self.get_posting_list_collection(kmer_list)
        else:
            return self.get_posting_list_kmer(kmer_list)


    def get_posting_list_kmer(self, kmer_list):

        results = {}
        values = self.redis.mget(kmer_list)
        count = 0
        for k in kmer_list:
            if values[count]:
                results[k] = json.loads(values[count]) 
                count = count + 1

        return results


    def get_posting_list_collection(self, kmer_list):
        # try:
        names_and_keys = {}
        results = {}

        #init search structure to get hashs and corresponding keys
        for kmer in kmer_list:
            name, key = self.split_kmer(kmer)
            #init dict if not set
            if(name not in names_and_keys):
                names_and_keys[name] = {}
            #map batches to the corresponding position on the collection
            names_and_keys[name][key] = None

        # collect values and map them to an output structure
        for name in names_and_keys.keys():
            keys = names_and_keys[name].keys()
            values = self.redis.hmget(name, keys)
            count = 0
            for k in keys:
                if values[count]:
                    results[name+k] = json.loads(values[count])
                count = count + 1

        return results
        # except:
        #     return None

    def _getRepositoryInfo(self):
        # self._load_redis()
        info = self.redis.info()
        return (info['used_memory'], info['db0']['keys'])

        
    def summary(self):
        # self._load_redis()
        print("Inverted Index:")
        print("Info redis:", self.redis.info())
        print("N bases to hash:", self.element['N_BASES_TO_HASH'])


    def _convert_hash_key(self, key):
        key = str(key)
        key = key.replace('(', '')
        key = key.replace(')', '')
        key = key.replace(',', '')
        return key

    def _load_redis(self):
        self.redis = redis.Redis(host='localhost', port=6379, db=0)



