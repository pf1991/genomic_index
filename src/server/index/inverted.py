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
        

    def add(self, hash_keys, kmer, fileid, pos_i, pos_f):

        self._load_redis()

        key = self._convert_hash_key(hash_keys)

        fragment = {}
        d = self.redis.get(key)
        if d:
            fragment = json.loads(d)  

        #init structure if doesnt exists
        if kmer not in fragment:  
            fragment[kmer] = {}
        if fileid not in fragment[kmer]:
                fragment[kmer][fileid] = []

        fragment[kmer][fileid].append([pos_i, pos_f])
            
        #save    
        d = json.dumps(fragment)  
        self.redis.set(key, d)

        return (hash_keys, kmer, fileid)

    def clear(self):
        self._load_redis()
        self.element = {}
        keys = self.redis.keys()
        for k in keys:
            self.redis.delete(k) 

    def get_posting_list(self, hash_keys, kmer):
        self._load_redis()
        try:
            key = self._convert_hash_key(hash_keys)
            d = self.redis.get(key)
            fragment = json.loads(d) 
            return fragment[kmer]
        except:
            return None

    def _getRepositoryInfo(self):
        self._load_redis()
        info = self.redis.info()
        return (info['used_memory'], info['db0']['keys'])

        
    def summary(self):
        self._load_redis()
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



