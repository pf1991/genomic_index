from .base_element import BaseElement
from datetime import date
import sys

class Repository(BaseElement):

    def __init__(self, filename_path, cache_name):

        super().__init__(filename_path, cache_name)
    
    def add(self, id, description, path):

        if  id not in self.element:
            self.element[id] = {
                'path': path,
                'description': description,
                'date': date.today()
            }
            return id
        
        return None
    
    def summary(self):
        print("Repository:")
        print("\tFiles ", len(self.element.keys()))
        print("\tObject Size %d Bytes" % (sys.getsizeof(self.element)))