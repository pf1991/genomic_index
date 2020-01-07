from .base_element import BaseElement
from .bloom_filter import BloomFilter
import sys

class Bloom(BaseElement):

    def __init__(self, filename_path, cache_name, max_inserts, false_pos_prob):

        super().__init__(filename_path, cache_name)

        self.max_inserts = max_inserts
        self.false_pos_prob = false_pos_prob

    def init(self):
        self.element = BloomFilter(self.max_inserts, self.false_pos_prob)

    def add(self, k):
        return self.element.add(k) 
    
    def summary(self):
        print("Bloom filter:")
        print("\tAddress %d, Size %d Bytes, Endianness %s, Unused %d bits, allocated %d bytes" % self.element.bit_array.buffer_info())
        print("\tElements set to true %d" % (self.element.bit_array.count()))
        print("\tObject Size %d Bytes" % (sys.getsizeof(self.element)))