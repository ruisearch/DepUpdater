## all api operations are defined in Api class
import os
from collections import deque
import json
from match.CallGraph import CallGraph
from match.constants import BCEL_PATH

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
        self.match_path = os.path.join(self.dep, f"match.json")
        # self.reachable_apis : reachable apis in cg
        self.reachable_apis = set()
        
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
        print(f"extract api of client jar: {self.client} ...")
        os.system(command)
        print(f"get api of client jar: {self.client}\n")
    ## extract api of a dep jar
    def extract_dep_api(self, dep_jar_name:str):
        txt_name = dep_jar_name + "_api.txt"
        api_txt_path = os.path.join(self.dep, txt_name)
        dep_path = os.path.join(self.dep, dep_jar_name)
        command = f"java -jar {BCEL_PATH} {dep_path} > {api_txt_path}"
        print(f"extract api of dep jar: {dep_path} ...")
        os.system(command)
        print(f"get api of dep jar: {dep_path}\n")

    
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
        json_content = self.update_format_of_json()
        for file in files:
            if file.endswith("_api.txt"):
                dep_jar_name = file[:file.find("_api.txt")]
                with open(os.path.join(self.dep, file), 'r') as f:
                    for line in f:
                        if line.strip() in self.reachable_apis:
                            # the jar contain a reachable api
                            self.add_api(json_content, dep_jar_name, line.strip())
        # get the finished match.json
        with open(self.match_path,'w') as f:
            json.dump(json_content, f, indent=4)
        print("****map done****\n")
    ## create "ReachableAPIs" in json entries
    # return the changed json list
    def update_format_of_json(self):
        with open(self.match_path,'r') as f:
            deps = json.load(f)
        for dep in deps:
            dep["ReachableAPIs"] = []
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
    
    