# a class that extract all types of references used by a module
# note : generate client-reference in client/, dep-reference in dep/
import os
from tqdm import tqdm
import subprocess
from match.constants import BCEL_REFERENCE

class Reference:
    def __init__(self,path_to_module:str):
        # get path to dep/
        self.dep_folder = os.path.join(path_to_module, f"dep/")
        # get path to client/
        self.client_folder = os.path.join(path_to_module, f"client/")
        # get path to client jar
        contents = os.listdir(self.client_folder)
        for item in contents:
            if item.endswith('.jar'):
                self.client_jar = os.path.join(self.client_folder, item)
                break
        # get paths to dep jars
        self.dep_jars = []
        contents = os.listdir(self.dep_folder)
        for item in contents:
            if item.endswith(".jar"):
                self.dep_jars.append(os.path.join(self.dep_folder,item))
        
    # generate reference used by  client and deps
    def gen_ref(self):
        self.gen_client_ref()
        self.gen_deps_ref()
    
    # generate reference used by client
    def gen_client_ref(self):
        # path to the resulting file, ended with '_ref.txt'
        client_ref_path = self.client_jar+'_ref.txt'
        with open(client_ref_path, 'w') as f:
            # run BCEL_reference to get reference used by client jar 
            subprocess.run(['java','-jar',f'{BCEL_REFERENCE}', f'{self.client_jar}'], stdout=f)
            print(f"**** reference used by {self.client_jar} got ****")
        
    # generate reference used by deps
    def gen_deps_ref(self):
        for dep_jar in tqdm(self.dep_jars, desc='Extracting reference used by deps'):
            dep_ref_path = dep_jar+'_ref.txt'
            with open(dep_ref_path, 'w') as f:
                subprocess.run(['java', '-jar', f'{BCEL_REFERENCE}', f'{dep_jar}'], stdout=f)
                print(f'"**** reference used by {dep_jar} got ****"')
                