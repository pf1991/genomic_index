from .base_element import BaseElement
import sys
import os
import pickle
from shutil import rmtree

class InvertedIndex(BaseElement):

    def __init__(self, filename_path, cache_name, repository_path):

        super().__init__(filename_path, cache_name)

        #check if dir exists, if not create it
        if not os.path.exists(repository_path):
            os.makedirs(repository_path)

        self.repository_path = repository_path
        

    def add(self, diggest, kmer, fileid, pos_i, pos_f):
        # if  diggest not in self.element:
        #     self.element[diggest] = {}

        # if kmer not in self.element[diggest]:  
        #     self.element[diggest][kmer] = {}

        # if fileid not in self.element[diggest][kmer]:
        #     self.element[diggest][kmer][fileid] = []

        # self.element[diggest][kmer][fileid].append([pos_i, pos_f])

        if(sys.getsizeof(self.element) < 90000000): #50MB
            self._to_ram(diggest, kmer, fileid, pos_i, pos_f)
        else:
            print('-Deploying to disk!')
            self._deploy_to_disk()

        return (diggest, kmer, fileid)


    def clear(self):

        # delete all files
        print('-Deleting inverted index files')
        folder = self.repository_path
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    rmtree(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))


    def save_disk(self):
        self._deploy_to_disk()


    def load_disk(self):
        return None


    def get_posting_list(self, diggest, kmer):
        try:
            file_path = self.repository_path + '/' + str(diggest)
            fragment = pickle.load( open(file_path, 'rb' ))
            return fragment[kmer]
        except:
            return None


    def summary(self):
        size = self._getRepositorySize()
        print("Inverted Index:")
        print("\tRepository size %d Bytes, %d files" % size)


    def _getRepositorySize(self):
        folder = self.repository_path
        total_size = os.path.getsize(folder)
        count = 0
        for item in os.listdir(folder):
            itempath = os.path.join(folder, item)
            if os.path.isfile(itempath):
                total_size += os.path.getsize(itempath)
            count = count + 1
        return (total_size, count)


    def _to_ram(self, diggest, kmer, fileid, pos_i, pos_f):
        if  diggest not in self.element:
            self.element[diggest] = {}

        if kmer not in self.element[diggest]:  
            self.element[diggest][kmer] = {}

        if fileid not in self.element[diggest][kmer]:
            self.element[diggest][kmer][fileid] = []
        
        self.element[diggest][kmer][fileid].append([pos_i, pos_f])


    def _deploy_to_disk(self):

        print('--Save Batch to disk')
        keys =  self.element.keys()
        l = len(keys)
        count = 0
        for diggest in keys:

            file_path = self.repository_path + '/' + str(diggest)

            fragment = {}
            #print('File', file_path)
            if os.path.exists(file_path):
                #load
                fragment = pickle.load( open(file_path, 'rb' ))
                #print('Loaded posting list:', fragment)

            for kmer in self.element[diggest].keys():

                if kmer not in fragment:  
                    fragment[kmer] = {}
                    
                #extend positions found
                for f in self.element[diggest][kmer].keys():

                    if f not in fragment[kmer]:
                        fragment[kmer][f] = []

                    fragment[kmer][f].extend(self.element[diggest][kmer][f])
                
            #save    
            with open(file_path, 'wb') as output:  # Overwrites any existing file.
                pickle.dump(fragment, output, pickle.HIGHEST_PROTOCOL)
            
            count = count + 1

            if(count % (l/100) == 0):
                print("Progress (%d/%d)" % (count, l))

        print('--Save Complete')

        #clear var
        self.element = {}

