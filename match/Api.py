## all api operations are defined in Api class
import os
import subprocess
from collections import deque
import json
from match.CallGraph import CallGraph
from match.constants import BCEL_PATH, SOOTCG_PATH

class Api:
    # module:path to module folder
    def __init__(self, module:str, cg:CallGraph):
        # cg : the CallGraph object of a module
        self.cg = cg
        # client_folder : path to client folder
        self.client_folder = os.path.join(module, "client")
        # client : path to client jar
        contents = os.listdir(self.client_folder)
        for item in contents:
            if item.endswith(".jar"):
                self.client = os.path.join(self.client_folder, item)
                break
        # dep : path to dep folder   
        self.dep = os.path.join(module, "dep")
        # txt_path: path to client_api.txt
        self.txt_path = os.path.join(self.client_folder, f"client_api.txt")
        # match_path : path to match.json
        # self.match_path = os.path.join(self.dep, f"match.json")
        self.match_path = os.path.join(self.dep, f"../match.json")
        # self.reachable_apis : reachable apis in cg
        self.reachable_apis = set()
        
    ## extract client api and dep api
    def extract_api(self):
        # extract client api
        self.extract_client_api()
        # extract dep api of effective dep jars
        with open(self.match_path, 'r') as f:
            effective_deps = json.load(f)
        for effective_dep in effective_deps:
            self.extract_dep_api(effective_dep["JarFileName"])
        # contents = os.listdir(self.dep)
        # for item in contents:
        #     if item.endswith(".jar"):
        #         self.extract_dep_api(item)
        
    ## extract client api
    def extract_client_api(self):
        # command = f"java -jar {BCEL_PATH} {self.client} > {self.txt_path}"
        command = f"java -jar {BCEL_PATH} {self.client}"
        print(f"extract api of client jar: {self.client} ...")
        with open(self.txt_path, 'w') as f:
            result = subprocess.run(command, shell=True, stdout=f)
        # os.system(command)
        print(f"get api of client jar: {self.client}\n")
    ## extract api of a dep jar
    def extract_dep_api(self, dep_jar_name:str):
        txt_name = dep_jar_name + "_api.txt"
        api_txt_path = os.path.join(self.dep, txt_name)
        if os.path.exists(api_txt_path) is False:
            dep_path = os.path.join(self.dep, dep_jar_name)
            # command = f"java -jar {BCEL_PATH} {dep_path} > {api_txt_path}"
            command = f"java -jar {BCEL_PATH} {dep_path}"
            print(f"extract api of dep jar: {dep_path} ...")
            with open(api_txt_path, 'w') as f:
                result = subprocess.run(command, shell=True, stdout=f)
            # os.system(command)
            print(f"get api of dep jar: {dep_path}\n")
        # return path to api.txt
        return api_txt_path
        

    
    ## get apis which are reachable
    def get_reachable_api(self):
        print("**** get reachable api... ****")
        # Load APIs and the call graph
        apis = self.read_apis(self.txt_path)
        call_graph = self.load_call_graph(self.cg.json_path)
        # Find all reachable APIs from the given APIs using BFS
        self.reachable_apis = self.bfs(call_graph, apis)
        print("**** reachable api got ****\n")
    ## Read APIs from a file, returning a set of APIs.
    def read_apis(self, api_file:str):
        with open(api_file, 'r') as f:
            return set(line.strip() for line in f)
    ## Load the call graph from a JSON file.
    def load_call_graph(self, json_file:str):
        with open(json_file, 'r') as f:
            return json.load(f)
    ## Perform BFS to find all reachable APIs from the start APIs.
    def bfs(self, call_graph:dict, start_apis:set):
        visited = set()
        queue = deque(start_apis)
        while queue:
            node = queue.popleft()  # pop
            if node not in visited:
                visited.add(node)
                # Add all unvisited, reachable nodes to the queue
                queue.extend(call_graph.get(node, [])) # push
        return visited
    
    
    ## dep jar->reachable api mapping
    def jar_to_reachable_api(self):
        files = os.listdir(self.dep)
        print("****map dep jar to reachable api...****")
        # json_content is the content of match.json
        # get the reachable api of all effective deps
        json_content = self.update_format_of_json()
        for file in files:
            if file.endswith("_api.txt"):
                # file contains the api of an effective dep
                dep_jar_name = file[:file.find("_api.txt")]
                with open(os.path.join(self.dep, file), 'r') as f:
                    for line in f:
                        if line.strip() in self.reachable_apis:
                            # the jar contain a reachable api
                            self.add_api(json_content, dep_jar_name, line.strip())
        
        # get the reachable apis of all ommited deps
        for effective_dep in json_content:
            self.get_reachable_api_of_omitted_dep(effective_dep)
            
        # get the finished match.json
        with open(self.match_path,'w') as f:
            json.dump(json_content, f, indent=4)
        print("****map done****\n")
        
    # pass the related omitted dep of an effective dep to get their reachable api
    def get_reachable_api_of_omitted_dep(self, effective_dep:dict):
        # path_to_module : path to data/Jar/{module}
        path_to_module = os.path.join(self.client_folder, '..')
        for omitted_dep in effective_dep['Omitted']:
            # get the partial_cg about the omitted_dep
            print(f"\n====== generate partial call graph of omitted_dep by {effective_dep['JarFileName']}: {omitted_dep['JarFileName']} ======")
            partial_cg = self.gen_cg_of_an_omitted_dep(omitted_dep, path_to_module)
            print(f"====== partial call graph of omitted_dep : {omitted_dep['JarFileName']} got ======")
            # get reachable api of omitted_dep
            # change some member variables of Api class -->
            # cg = partial_cg
            # reachable_apis = set() , just clear it 
            print(f"====== generate reachable api of omitted_dep by {effective_dep['JarFileName']}: {omitted_dep['JarFileName']} ======")
            self.cg = partial_cg
            self.reachable_apis = set()
            # extract api of the omitted_dep
            api_txt_path = self.extract_dep_api(omitted_dep['JarFileName'])
            # get the reachable_api from client in the partial cg, stored in self.reachable_apis
            self.get_reachable_api()
            # get the reachable_api of the omitted_dep
            with open(api_txt_path, 'r') as f:
                for line in f:
                    if line.strip() in self.reachable_apis:
                        # add a reachable api to omitted_dep
                        omitted_dep["ReachableAPIs"].append(line.strip())
            print(f"====== reachable api of omitted_dep : {omitted_dep['JarFileName']} got ======\n")
            
            
            
    # generate the partial cg of an omitted_dep
    # path_to_module : path to data/Jar/{module}/
    def gen_cg_of_an_omitted_dep(self, omitted_dep:dict, path_to_module:str):
        # generate the partial cg
        partial_cg = CallGraph(path_to_module)
        # unlike total cg, should change some Member variable of CallGraph object
        # the variable doesn't need to change ==>
        # dep_folder : path to data/Jar/{module}/dep
        # client_folder : path to data/Jar/{module}/client
        # client_jar : path to client jar
        
        # other variable should be changed as follows ==>
        # dep_jars : omitted_dep["JarFileName"]+omitted_dep['DependedBy']
        partial_cg.dep_jars = [] # clear   
        partial_cg.dep_jars.append(os.path.join(partial_cg.dep_folder, omitted_dep["JarFileName"]))
        for dependant_jar_name in omitted_dep["DependedBy"]:
            partial_cg.dep_jars.append(os.path.join(partial_cg.dep_folder, dependant_jar_name))
        # json_path : path to data/Jar/{module}/dep/{omitted_dep["JarFileName"]}_Uber_call_grash.json
        # txt_path : path to data/Jar/{module}/dep/{omitted_dep["JarFileName"]}_Uber_call_grash.txt
        # so, partial cg file name is {omitted_dep["JarFileName"]}_Uber_call_grash.json contained in data/Jar/{module}/dep/
        partial_cg.json_path = os.path.join(partial_cg.dep_folder, f'{omitted_dep["JarFileName"]}_Uber_call_graph.json')
        partial_cg.txt_path = os.path.join(partial_cg.dep_folder, f'{omitted_dep["JarFileName"]}_Uber_call_graph.txt')
        # note: cg file of one jar is named with JarFileName_cg.txt
        
        # generate the partial cg using the variable above
        # just need to generate the cg of this omitted jar because the dependants are all effective and their cg have generated already
        omitted_cg_path = os.path.join(partial_cg.dep_folder, f'{omitted_dep["JarFileName"]}_cg.txt')
        if os.path.exists(omitted_cg_path) is False:
            # path to omitted_jar
            omitted_dep_jar_path = os.path.join(partial_cg.dep_folder, omitted_dep["JarFileName"])
            command = f"java -jar {SOOTCG_PATH} {omitted_dep_jar_path} > {omitted_cg_path}"
            os.system(command)
        partial_cg.get_total_cg()
        partial_cg.parse_cg(partial_cg.txt_path, partial_cg.json_path)
        
        return partial_cg
        
            
    ## create "ReachableAPIs" in json entries
    # return the changed json list
    def update_format_of_json(self):
        with open(self.match_path,'r') as f:
            deps = json.load(f)
        for dep in deps:
            dep["ReachableAPIs"] = []
            # add "ReachableAPIs" in Omitted deps
            for omitted_dep in dep["Omitted"]:
                omitted_dep["ReachableAPIs"] = []
        # for i in range(len(deps)):
        #     deps[i]["ReachableAPIs"] = []
        #     for j in range(len(deps[i]["Omitted"])):
        #         deps[i]["Omitted"][j]["ReachableAPIs"] = []
        return deps
    ## add a new reachable api into match.json
    # dep_jar_name : the name of dep jar
    # new_api : the new reachable api to be added
    # json_content : list of json entry
    def add_api(self, json_content:list, dep_jar_name:str, new_api:str):
        for dep in json_content:
            if dep["JarFileName"] == dep_jar_name:
                dep["ReachableAPIs"].append(new_api)
                break
    
    