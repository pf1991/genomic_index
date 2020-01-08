from .base_element import BaseElement
from datetime import date
from shutil import copyfile, rmtree
import sys
import os

class Repository(BaseElement):

    def __init__(self, filename_path, cache_name, repository_path):

        super().__init__(filename_path, cache_name)

        #check if dir exists, if not create it
        if not os.path.exists(repository_path):
            os.makedirs(repository_path)

        self.repository_path = repository_path

    def clear(self):

        # delete all files
        print('-Deleting repository files')
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


    def add(self, id, description, path, extension, ref_id = None):

        # lets move the file to
        if  id not in self.element:
            dst = ''

            if(path):
                dst = self.repository_path + '/' + id + extension
                dst = copyfile(path, dst)
                print('- Copying file to repository', dst)


            print('-Adding new file to repository')

            self.element[id] = {
                'path': dst,
                'description': description,
                'date': date.today(),
                'ref_id': ref_id, 
            }
            
            return id
        
        return None

        
    

    def get_path(self, file_id):
        try:
            return self.element[file_id]['path']
        except KeyError:
            return None


    def summary(self):
        print("Repository:")
        print("\tFiles ", len(self.element.keys()))
        print("\tObject Size %d Bytes" % (sys.getsizeof(self.element)))