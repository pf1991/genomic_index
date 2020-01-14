from .base_element import BaseElement
import sys
import os
import pickle
from shutil import rmtree
import redis
import json

class InvertedIndex(BaseElement):

    def __init__(self, filename_path, cache_name, repository_path, redis_host):

        super().__init__(filename_path, cache_name)

        self.redis_host = redis_host
        self._load_redis()
        

    def add_to_fragment(self, kmer, fileid, pos_i, pos_f):

        fragment = {}
        d = self.redis.get(kmer)
        if d:
            fragment = json.loads(d)  

        #init structure if doesnt exists
        if fileid not in fragment:
                fragment[fileid] = []

        fragment[fileid].append(pos_i)
 
        return json.dumps(fragment)  

    def add_batch(self, batch):
        return self.redis.mset(batch)

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
        self.redis = redis.Redis(host=self.redis_host, port=6379, db=0)



