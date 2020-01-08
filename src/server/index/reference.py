from .base_element import BaseElement
import sys

class Reference(BaseElement):

    def __init__(self, filename_path, cache_name):

        super().__init__(filename_path, cache_name)
    
    def add(self, id, sequence):

        if  id not in self.element:
            self.element[id] = {
                'sequence': sequence,
            }
            return id
        
        return None
    
    def summary(self):
        print("Reference:")
        print("\tFiles ", len(self.element.keys()))
        print("\tObject Size %d Bytes" % (sys.getsizeof(self.element)))