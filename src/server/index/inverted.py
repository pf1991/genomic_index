from .base_element import BaseElement
import sys
import os
import pickle
from shutil import rmtree
import redis
import json
import time

class InvertedIndex(BaseElement):

    def __init__(self, filename_path, cache_name, repository_path):

        super().__init__(filename_path, cache_name)

        self._load_redis()
        self.time = [0,0,0,0,0]

    
    def reset_time(self):
        self.time = [0,0,0,0,0]


    def get_time(self):
        return self.time


    def add_to_fragment(self, kmer, value, fileid, pos_i):

        temp = time.time()
        fragment = {}
        if value:
            fragment = json.loads(value) 
        self.time[0] = self.time[0] + time.time() - temp

        temp = time.time()
        #init structure if doesnt exists
        if fileid not in fragment:
                fragment[fileid] = []

        fragment[fileid].append(pos_i)
        self.time[2] = self.time[2] + time.time() - temp

        temp = time.time()
        d = json.dumps(fragment) 
        self.time[3] = self.time[3] + time.time() - temp 

        return d 

    def process_batch(self, batch):
        
        batch_to_submit = {}
        keys = [ b[0] for b in batch ]
        values = self.redis.mget(keys)
        count = 0
        for b in batch:

            v = None
            if b[0] in batch_to_submit:
                # use the most recent value
                v = batch_to_submit[b[0]]
            else:
                v = values[count]

            d = self.add_to_fragment(b[0], v, b[1], b[2])

            #replace the tupple by the string fragment
            batch_to_submit[b[0]] = d
            count = count + 1

        return self.redis.mset(batch_to_submit)

    def clear(self):
        # self._load_redis()
        self.element = {}
        self.redis.flushdb()
        self.redis.flushall()
        self.redis.config_resetstat()
        self.redis.bgrewriteaof()
        self.redis.slowlog_reset()

    def get_posting_list(self, kmer):
        # self._load_redis()
        try:
            d = self.redis.get(kmer)
            fragment = json.loads(d) 
            return fragment
        except:
            return None

    def _getRepositoryInfo(self):
        # self._load_redis()
        info = self.redis.info()
        return (info['used_memory'], info['db0']['keys'])

        
    def summary(self):
        # self._load_redis()
        print("Inverted Index:")
        print("Info redis:", self.redis.info())


    def _convert_hash_key(self, key):
        key = str(key)
        key = key.replace('(', '')
        key = key.replace(')', '')
        key = key.replace(',', '')
        return key

    def _load_redis(self):
        self.redis = redis.Redis(host='localhost', port=6379, db=0)



