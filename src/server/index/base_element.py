import pickle
import os, sys

class BaseElement():


    def __init__(self, filename_path, cache_name):

        self.filename_path = filename_path
        self.cache_name = cache_name
        self.element = {}


    def save(self):
        self.save_disk()

    def init(self):
        print('-Init element')
        self.element = {}

    def get(self):
        element = self.load_disk()
        if element:
            self.element = element

        return None

    def load_disk(self):
        print('- Loading from disk')
        try:
            return pickle.load( open(self.filename_path, 'rb' ))
        except FileNotFoundError:
            print('Warning! File not found!')
            return None

    def save_disk(self):
        print('- Saving to disk')
        with open(self.filename_path, 'wb') as output:  # Overwrites any existing file.
            pickle.dump(self.element, output, pickle.HIGHEST_PROTOCOL)
