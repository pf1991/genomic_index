# include standard modules
import argparse
from Bio import SeqIO
import os
import pickle
from index.index import Index
import time
import sys

# initiate the parser
# define the program description
text = 'This is a program to build the index via command line.'

# initiate the parser with a description
parser = argparse.ArgumentParser(description = text)

parser.add_argument("-V", "--version", help="show program version", action="store_true")

parser.add_argument(
    '--generate',
    action='store_true',
    help='Generate index',
)

parser.add_argument(
    '--index_files',
    action='store_true',
    help='Index files',
)

parser.add_argument(
    '--stats',
    action='store_true',
    help='Index statistics',
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
    '--evaluating',
    action='store_true',
    help='Evaluate index',
)

args = parser.parse_args()

#Commands

index = Index()

if args.generate:
    start = time.time()
    index.generate(max_pos = 100000, seq_ids = ['1'], max_files_to_index = 10,
                    window_sizes = [4,6,8,16,32,64,128], sept_unit = 1, max_bloom_false_prob = 0.005)
    end = time.time()
    print('Indexing time:', end - start)
    index.summary()


elif args.stats:
    index.summary()

elif args.index_files:
    index.summary()
    start = time.time()
    index.index_files()
    end = time.time()
    print("Indexing files", end - start)

elif args.test_consistency:
    index.summary()
    start = time.time()
    index.test_consistency()
    end = time.time()
    print("Consistency", end - start)

elif args.test_search:
    index.summary()
    start = time.time()
    result = index.search('CACTAA')
    end = time.time()
    print('Result', result)
    print('Search time:', end - start)

# elif args.evaluating:
#     print('Init benchmarking...')

#     tests = [
#         (100000, )
#     ]