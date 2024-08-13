# a class that encapsulates all operations on the call graphs of a module
# note : generate client cg in client/, dep cg in dep/
import os 
import json
import re
from tqdm import tqdm
from match.constants import SOOTCG_PATH

class CallGraph:
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
        # contents = os.listdir(self.dep_folder)
        # for item in contents:
        #     if item.endswith(".jar"):
        #         self.dep_jars.append(os.path.join(self.dep_folder,item))
        
        # pass match.json to get path to effective_dep_jar
        match_json_path = os.path.join(self.dep_folder, '../match.json')
        with open(match_json_path, 'r') as f:
            data = json.load(f)
        for dep in data:
            self.dep_jars.append(os.path.join(self.dep_folder, dep["JarFileName"]))
        
        # path to call_graph.json containing the total call graph
        self.json_path = os.path.join(path_to_module, 'Uber/call_graph.json')
        # path to Uber/call_graph.txt
        self.txt_path = os.path.join(path_to_module, 'Uber/call_graph.txt')
        
    ## generate call_graph.json
    def gen_json(self):
        # execute sootCG
        self.gen_client_cg()
        self.gen_deps_cg()
        self.get_total_cg()
        self.parse_cg(self.txt_path, self.json_path)
        
    ## generate client call graph
    def gen_client_cg(self):
        cg_command = f"java -jar {SOOTCG_PATH} {self.client_jar} > {self.client_jar}_cg.txt"
        print(f"**** start generating call graph of client: {self.client_jar}... ****")
        os.system(cg_command)
        # self.parse_cg(f"{self.client_jar}_cg.txt",f"{self.client_jar}_cg.json")
        print(f"**** call graph of {self.client_jar} generated ****")
        
    ## generate call graphs of deps
    def gen_deps_cg(self):
        # for dep_jar in self.dep_jars:
        for dep_jar in tqdm(self.dep_jars, desc='Generating call graphs of deps'):
            cg_command = f"java -jar {SOOTCG_PATH} {dep_jar} > {dep_jar}_cg.txt"
            print(f"**** generating call graph of dep: {dep_jar}... ****")
            os.system(cg_command)
            # self.parse_cg(f"{dep_jar}_cg.txt",f"{dep_jar}_cg.json")
            print(f"**** call graph of {dep_jar} generated ****")
            
    ##  *_cg.txt into Uber/call_graph.txt
    def get_total_cg(self):
        total_call_graph = ""
        with open(f"{self.client_jar}_cg.txt", "r") as f:
            total_call_graph = total_call_graph + f.read()
        for dep_jar in self.dep_jars:
            with open(f"{dep_jar}_cg.txt", 'r') as f:
                total_call_graph = total_call_graph + f.read()
        with open(self.txt_path, 'w') as f:
            f.write(total_call_graph)
            
    ## parse the call_graph.txt to generate call_graph.json
    def parse_cg(self, txt_path, json_path):
        # generate a dictionary containing the mapping from caller to its callees
        print("**** generating total call graph ... ****")
        map_dict = {}
        with open(txt_path, 'r') as f:
            for line in f:
                pattern = r"<(.*?)> ==> <(.*?)>$"
                matches = re.findall(pattern, line)
                for match in matches:
                    caller = match[0]
                    callee = match[1]
                # make sure the caller is the last fraction before ==>
                # it is the part after the last " in <" of the caller above
                idx = caller.rfind(" in <")
                if idx != -1:
                    caller = caller[idx+len(" in <"):]
                
                if caller in map_dict:
                    map_dict[caller].append(callee)
                else :
                    map_dict[caller] = [callee]        
        # dictionary to json
        with open(json_path, 'w') as J:
            json.dump(map_dict, J, indent=4)
        # remove call_graph.txt
        os.remove(txt_path)
        print("**** total call graph got ****")
    
        