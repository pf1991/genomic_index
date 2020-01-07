from django.core.management.base import BaseCommand, CommandError
from django.core.cache import cache
from Bio import SeqIO
import os
import pickle
#from search.helpers.index import Index
import time
import sys
#from django.core.cache import cache

class Command(BaseCommand):
    help = 'help'

    def add_arguments(self, parser):
        
        # Named (optional) arguments
        parser.add_argument(
            '--generate',
            action='store_true',
            help='Generate index',
        )

        parser.add_argument(
            '--stats',
            action='store_true',
            help='Index statistics',
        )

        parser.add_argument(
            '--init',
            action='store_true',
            help='init index',
        )

        parser.add_argument(
            '--test_consistency',
            action='store_true',
            help='test consistency index',
        )

        parser.add_argument(
            '--test_search',
            action='store_true',
            help='test search',
        )

        parser.add_argument(
            '--test_memcached',
            action='store_true',
            help='test_memcached',
        )
        

    # def handle(self, *args, **options):

    #     if options['test_memcached']:

    #         print(variable_global)
            
    #         cache.set('bloom', {}, None)
    #         a = cache.get('bloom')
    #         if a == None:
    #             print('Nok')
    #         return

    #     #index
    #     index = Index()

    #     if options['generate']:
    #         start = time.time()
    #         index.generate()
    #         end = time.time()
    #         print('Indexing time:', end - start)
    #         index.summary()

    #     if options['init']:
    #         start = time.time()
    #         index.init()
    #         end = time.time()
    #         print('Time indexing reference:', end - start)
    #         index.summary()
        
    #     if options['stats']:
    #         start = time.time()
    #         index.summary()
    #         print("Index Size %d Bytes" % (sys.getsizeof(index)))
    #         end = time.time()

    #     if options['test_consistency']:
    #         start = time.time()
    #         index.test_consistency()
    #         end = time.time()

    #     # if options['test_consistency']:
    #     #     start = time.time()
    #     #     index.test_search('AAATCGGGCATCATCT')
    #     #     end = time.time()




