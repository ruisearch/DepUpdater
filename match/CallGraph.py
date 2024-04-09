# a class that encapsulates all operations on the call graph of a Uber jar
import os 
import json
import re
from match.constants import SOOTCG_PATH

class CallGraph:
    def __init__(self,path_to_module:str):
        # get path to Uber folder
        self.Uber_folder = os.path.join(path_to_module, f"Uber")
        # get path to Uber jar
        contents = os.listdir(self.Uber_folder)
        for item in contents:
            if item.endswith('.jar'):
                self.Uber_jar = os.path.join(self.Uber_folder, item)
                break
        # set path to call_graph.txt
        self.txt_path = os.path.join(self.Uber_folder, f"call_graph.txt")
        # set path to call_graph.json
        self.json_path = os.path.join(self.Uber_folder, f"call_graph.json")
        
    ## generate call_graph.json
    def gen_json(self):
        # execute sootCG
        cg_command = f"java -jar {SOOTCG_PATH} {self.Uber_jar} > {self.txt_path}"
        print(f"**** generating call graph of {self.Uber_jar}...****")
        os.system(cg_command)
        print("**** call graph generated ****")
        self.parse_cg()
        
    ## parse the call graph to generate call_graph.json
    def parse_cg(self):
        # generate a dictionary containing the mapping from caller to its callees
        map_dict = {}
        with open(self.txt_path, 'r') as f:
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
        
        print(f"**** generating {self.json_path}...****")
        # dictionary to json
        with open(self.json_path, 'w') as J:
            json.dump(map_dict, J, indent=4)
        print("**** call_graph.json generated !****")
    
        