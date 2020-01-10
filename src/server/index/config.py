from .base_element import BaseElement
from datetime import date
import sys
import pickle

class Config(BaseElement):

    def __init__(self, filename_path, cache_name):

        super().__init__(filename_path, cache_name)
    
        self.element = {
            'MAX_POS': 10000,
            'MAX_SAMPLES_TO_INDEX': 1,
            'WINDOW_SIZES': [4,6],
            'MAX_BLOOM_FALSE_POS_PROB': 0.1,
            'BUILD_OK': False,
            'RAM': True
        }

    def update(self, max_pos = 10000, MAX_SAMPLES_TO_INDEX = 50,
                    window_sizes = [4,6,8,16,32,64,128], max_bloom_false_prob = 0.005, ram = True):

        print('-update index config')
        self.element = {
            'MAX_POS': max_pos,
            'MAX_SAMPLES_TO_INDEX': MAX_SAMPLES_TO_INDEX,
            'WINDOW_SIZES': window_sizes,
            'MAX_BLOOM_FALSE_POS_PROB': max_bloom_false_prob,
            'BUILD_OK': False,
            'RAM': ram
        }
    
    def summary(self):
        print("Config:")
        print("\t", self.element)
        

    def save_disk(self):
        print('- Saving to disk')
        with open(self.filename_path, 'wb') as output:  # Overwrites any existing file.
            pickle.dump(self.element, output, pickle.HIGHEST_PROTOCOL)