from .base_element import BaseElement
import sys

class InvertedIndex(BaseElement):

    def __init__(self, filename_path, cache_name):

        super().__init__(filename_path, cache_name)
        

    def add(self, diggest, kmer, fileid, pos_i, pos_f):
        if  diggest not in self.element:
            self.element[diggest] = {}

        if kmer not in self.element[diggest]:  
            self.element[diggest][kmer] = {}

        if fileid not in self.element[diggest][kmer]:
            self.element[diggest][kmer][fileid] = []

        self.element[diggest][kmer][fileid].append((pos_i, pos_f))

        return (diggest, kmer, fileid)

    def get_posting_list(self, diggest, kmer):
        try:
            return self.element[diggest][kmer]
        except:
            return None

    def summary(self):
        print("Inverted Index:")
        print("\tIndexed %d hashes" % len(self.element.keys()))
        print("\tObject Size %d Bytes" % (sys.getsizeof(self.element)))

