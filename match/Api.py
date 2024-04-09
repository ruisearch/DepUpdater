## all api operations are defined in Api class
import os
from match.CallGraph import CallGraph
from match.constants import BCEL_PATH

class Api:
    # module:path to module folder
    def __init__(self, module:str, cg:CallGraph):
        # cg : the CallGraph object of Uber jar
        # cg.Uber_folder : path to Uber folder
        self.cg = cg
        # client_folder : path to client folder
        self.client_folder = os.path.join(module, "client")
        # client : path to client jar
        contents = os.listdir(self.client_folder)
        for item in contents:
            if item.endswith(".jar"):
                self.client = os.path.join(self.client_folder, item)
        # dep : path to dep folder   
        self.dep = os.path.join(module, "dep")
        # txt_path: path to client_api.txt
        self.txt_path = os.path.join(self.client_folder, f"client_api.txt")
        
    ## extract client api and dep api
    def extract_api(self):
        # extract client api
        self.extract_client_api()
        # extract dep api of dep jars
        contents = os.listdir(self.dep)
        for item in contents:
            if item.endswith(".jar"):
                self.extract_dep_api(item)
                
    
    ## extract client api
    def extract_client_api(self):
        command = f"java -jar {BCEL_PATH} {self.client} > {self.txt_path}"
        print(f"**** extract api of client jar: {self.client} ...****")
        os.system(command)
        print(f"**** get api of client jar: {self.client}****\n")
    
    ## extract api of a dep jar
    def extract_dep_api(self, dep_jar_name:str):
        txt_name = dep_jar_name + ".txt"
        api_txt_path = os.path.join(self.dep, txt_name)
        dep_path = os.path.join(self.dep, dep_jar_name)
        command = f"java -jar {BCEL_PATH} {dep_path} > {api_txt_path}"
        print(f"**** extract api of dep jar: {dep_path} ...****")
        os.system(command)
        print(f"**** get api of dep jar: {dep_path}****\n")
         