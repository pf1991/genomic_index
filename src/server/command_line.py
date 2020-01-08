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

# set up

parser.add_argument(
    '--set_up',
    action='store_true',
    help='Initialize index and reset all its configurations and saved data!',
)

# index file

parser.add_argument(
    '--index_reference',
    nargs=2,
    metavar=('ref_id', 'ref_path'),
    help='Add and index a new reference!',
)

parser.add_argument(
    '--index_file',
    nargs=2,
    metavar=('ref_id', 'vcf_path'),
    help='Index a vcf file specifying the corresponding reference',
)

parser.add_argument(
    '--stats',
    action='store_true',
    help='Index statistics',
)

# parser.add_argument(
#     '--test_consistency',
#     action='store_true',
#     help='test consistency index',
# )

parser.add_argument(
    '--search',
    help='Search for a sequence',
)
 

# parser.add_argument(
#     '--evaluating',
#     action='store_true',
#     help='Evaluate index',
# )

args = parser.parse_args()

#Commands

index = Index()

if args.set_up:

    index.set_up(max_pos = 20000, seq_ids = ['1'], max_samples_to_index = 2,
                     window_sizes = [32, 64, 128], sept_unit = 1, max_bloom_false_prob = 0.005)

if args.index_reference:
    print('ref id:', args.index_reference[0], 'ref path:', args.index_reference[1])
    index.index_reference(args.index_reference[0], args.index_reference[1])


if args.index_file:
    print('ref id:', args.index_file[0], 'vcf path:', args.index_file[1])
    index.index_file(args.index_file[0], args.index_file[1])


# if args.generate:
#     start = time.time()
#     index.generate(max_pos = 20000, seq_ids = ['1'], max_files_to_index = 2,
#                     window_sizes = [32, 64, 128], sept_unit = 1, max_bloom_false_prob = 0.005)
#     end = time.time()
#     print('Indexing time:', end - start)
#     index.summary()


elif args.stats:
    index.summary()

# elif args.index_files:
#     index.summary()
#     start = time.time()
#     index.index_files()
#     end = time.time()
#     print("Indexing files", end - start)

# elif args.test_consistency:
#     index.summary()
#     start = time.time()
#     index.test_consistency()
#     end = time.time()
#     print("Consistency", end - start)

elif args.search:

    search_str = args.search
    print("Searching for:", search_str)
    index.summary()
    start = time.time()
    result = index.search(search_str)
    end = time.time()
    print('Result', result)
    print('Search time:', end - start)

# elif args.evaluating:
#     print('Init benchmarking...')

#     tests = [
#         (100000, )
#     ]