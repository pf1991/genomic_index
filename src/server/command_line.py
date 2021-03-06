# include standard modules
import argparse
from Bio import SeqIO
import os
import pickle
from index.index import Index
import time
import sys
from os import listdir
from os.path import isfile, join
import string
import random

def random_string(length):
    return ''.join(random.choice(string.ascii_letters) for m in range(length))

# initiate the parser
# define the program description
text = 'This is a program to build the index via command line.'

# initiate the parser with a description
parser = argparse.ArgumentParser(description = text)

parser.add_argument("-V", "--version", help="show program version", action="store_true")

# set up

parser.add_argument(
    '--set_up',
    nargs=4,
    metavar=('max_pos', 'max_samples', 'window_sizes', 'batch_size'),
    help='Initialize index for max_pos (max length of a sequence), max_samples (samples on VCF file), k-mers sizes, batch_size',
)

# index file

parser.add_argument(
    '--index_reference',
    nargs=2,
    metavar=('ref_id', 'ref_path'),
    help='Add and index a new reference!',
)

parser.add_argument(
    '--index_vcf',
    nargs=2,
    metavar=('ref_id', 'vcf_path'),
    help='Index a vcf file specifying the corresponding reference',
)

parser.add_argument(
    '--stats',
    action='store_true',
    help='Index statistics',
)

parser.add_argument(
    '--evaluate',
    action='store_true',
    help='Evaluate Index',
)

parser.add_argument(
    '--search',
    help='Search for a sequence',
)
 
args = parser.parse_args()

#Commands

index = Index()

if args.set_up:

    window_arr = args.set_up[2].split(',')
    window_arr = list(map(int, window_arr)) 
    index.set_up(max_pos = int(args.set_up[0]), max_samples_to_index = int(args.set_up[1]),
                     window_sizes = window_arr, batch_size = int(args.set_up[3]))

if args.index_reference:
    start = time.time()
    print('ref id:', args.index_reference[0], 'ref path:', args.index_reference[1])
    index.index_reference(args.index_reference[0], args.index_reference[1])
    end = time.time()
    print('Index elapsed time:', end - start)

if args.index_vcf:
    print('ref id:', args.index_vcf[0], 'vcf path:', args.index_vcf[1])
    index.index_vcf(args.index_vcf[0], args.index_vcf[1])

elif args.stats:
    index.summary()

elif args.search:

    search_str = args.search
    print("Searching for:", search_str)
    index.summary()
    start = time.time()
    result = index.search(search_str)
    end = time.time()
    print('Result', result)
    print('Search time:', end - start)

elif args.evaluate:

    results = []

    # (max_sequence_length, k-meers size to use, batch size)
    test_conditions = [
        (100000, [16], 1000, None),
        (100000, [16], 1000, 4),
        (1000000, [16], 1000, None),
        (1000000, [16], 1000, 4),
        (5000000, [16], 1000, None),
        (5000000, [16], 1000, 4),
        (10000000, [16], 1000, None),
        (10000000, [16], 1000, 4),
        (15000000, [16], 1000, None),
        (15000000, [16], 1000, 4),
        (0, [16], 1000, None),
        (0, [16], 1000, 4),
    ]

    #files for testing
    test_path = '../files_for_testing/fungos'
    files = [ (f.split('.')[0], join(test_path, f)) for f in listdir(test_path) if isfile(join(test_path, f))]
    for t in test_conditions:

        r = {}

        # setup
        # max_samples_to_index is only relevant for vcf files (is not relevant for this case)
        index.set_up(max_pos = t[0], max_samples_to_index = 20,
                        window_sizes = t[1], batch_size = t[2], n_bases_to_hash = t[3])

        index_times = []
        total_t = 0
        r['N_files'] = len(files)
        r['max_length'] = t[0]
        r['k-meers_sizes'] = ','.join([str(x) for x in t[1]])
        r['batch_size'] = t[2]
        r['redis_hash'] = t[3]

        sequences_length = 0
        count_file = 0
        for f in files:      
            # index
            start = time.time()
            file_length = index.index_reference(str(count_file),f[1], f[0])    # ref_id, file path
            end = time.time()
            delta_t = end-start
            index_times.append(delta_t)
            sequences_length = sequences_length + file_length
            count_file = count_file + 1

        r['total_sequence_length'] = sequences_length

        # r['index_files'] = index_times
        r['indexing_time_total'] = sum(index_times)
        r['indexing_time_avg'] = sum(index_times) / len(files)
        r['indexing_time_min'] = min(index_times)
        r['indexing_time_max'] = max(index_times)

        #get inverted index total size
        size, fragments = index.inverted_index._getRepositoryInfo()
        r['fragments_total_size'] = size
        r['number_of_fragments'] = fragments


        # search
        string_test = [25, 50, 75, 100, 125]
        search_times = [0]*len(string_test)
        search_hits = [0]*len(string_test)
        n_tests = 20
        for i in range(0,n_tests):
            count_search = 0
            search_times_temp = []
            search_hits_temp = []
            for size in string_test:
                #read subsequence of the sequence
                f = open('_indexed_0.txt', 'rb')
                s = f.read(size).decode(encoding='utf-8')
                f.close()
                start = time.time()
                result = index.search(s)
                end = time.time()
                search_times_temp.append((end-start))
                hits = 0
                for res in result:
                    hits = hits + len(res['value']['locations'])
                search_hits_temp.append(hits)

            #sum all 
            for j in range(0,len(string_test)):
                search_times[j] = search_times[j] + search_times_temp[j]
                search_hits[j] = search_hits[j] + search_hits_temp[j]

        count_temp = 0
        for j in string_test:
            r['search_time_%d' % j ] = search_times[count_temp] / n_tests
            count_temp = count_temp + 1
        
        count_temp = 0
        for j in string_test:
            r['search_time_%d_hits' % j] = search_hits[count_temp]/ n_tests
            count_temp = count_temp + 1

        redis_info = index.inverted_index.redis.info()
        r['used_memory'] = redis_info['used_memory']
        r['used_memory_rss'] = redis_info['used_memory_rss']
        r['used_memory_peak'] = redis_info['used_memory_peak']
        r['used_memory_dataset'] = redis_info['used_memory_dataset']


        results.append(r)

        #cada chave com uma key de 16chars e valor de 30 parece ocupar 104 bytes

    print('--results (copy and paste on Excel)--')
    keys = results[0].keys()
    for k in keys:
        print('%s ' % k, end='')
    print()
    for r in results:
        for k in r:
            print(r[k], ' ', sep='', end='')
        print()
