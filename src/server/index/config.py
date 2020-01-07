from .base_element import BaseElement
from datetime import date
import sys
import pickle

class Config(BaseElement):

    def __init__(self, filename_path, cache_name):

        super().__init__(filename_path, cache_name)
    
        self.element = {
            'MAX_POS': 10000,
            'SEQ_IDS': ['1'],
            'MAX_FILES_TO_INDEX': 1,
            'WINDOW_SIZES': [4,6],
            'STEPS_UNIT': 1,
            'MAX_BLOOM_FALSE_POS_PROB': 0.1,
            'BUILD_OK': False
        }

    def update(self, max_pos = 10000, seq_ids = ['1'], max_files_to_index = 50,
                    window_sizes = [4,6,8,16,32,64,128], sept_unit = 1, max_bloom_false_prob = 0.005):

        print('-update index config')
        self.element = {
            'MAX_POS': max_pos,
            'SEQ_IDS': seq_ids,
            'MAX_FILES_TO_INDEX': max_files_to_index,
            'WINDOW_SIZES': window_sizes,
            'STEPS_UNIT': sept_unit,
            'MAX_BLOOM_FALSE_POS_PROB': max_bloom_false_prob,
            'BUILD_OK': False
        }
    
    def summary(self):
        print("Config:")
        print("\t", self.element)
        

    def save_disk(self):
        print('- Saving to disk')
        with open(self.filename_path, 'wb') as output:  # Overwrites any existing file.
            pickle.dump(self.element, output, pickle.HIGHEST_PROTOCOL)