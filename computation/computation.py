"""get the newest compatible version of a dependency"""
import os
import concurrent.futures
import copy
import json
import tqdm
from constants import TQDM_LOG_PATH, REACHABLE_API_DIR
from versions import get_all_versions
from api import Api
class Computation:
    def __init__(self, cur_node:dict, graph:list, json_path: str, repo_name:str, relative_path_to_module:str):
        """
        Args:
            cur_node : the dependency to be computed
            graph : the dependency graph
            json_path : the path to the json file to record the graph
        """
        self.cur_node = cur_node
        self.graph = graph
        self.json_path = json_path
        self.repo_name = repo_name
        self.relative_path_to_module = relative_path_to_module
        self.reachable_method_callee = []
        self.reachable_type_callee = []
        
    def get_old_deps(self):
        """get the old dependencies of the current dependency\n
        just return groupId and artifactId of the old dependencies
        """
        old_deps = []
        for dep in self.graph:
            dependents = dep['Dependents']
            for dependent in dependents:
                if dependent['GroupId'] == self.cur_node['GroupId'] and dependent['ArtifactId'] == self.cur_node['ArtifactId']:
                    old_deps.append({'GroupId': dep['GroupId'], 'ArtifactId': dep['ArtifactId']})
        return old_deps

    def compute_best_version(self):
        """main function to compute the newest compatible version of the dependency"""
        # get all versions
        # if self.cur_node has Versions, then use it, else fetch from maven repository
        if 'Versions' in self.cur_node:
            # the versions are already fetched
            all_versions = [Version['version'] for Version in self.cur_node['Versions']]
        else:
            all_versions = get_all_versions(self.cur_node['GroupId'], self.cur_node['ArtifactId'], self.cur_node['Original_Version'])
            # record the versions in the graph
            self.cur_node['Versions'] = [{'version': version, 'breaking_reason':''} for version in all_versions]
        
        if not all_versions:
            return self.cur_node['Original_Version']

        # get reachable methods and types of the dependency
        self.get_reachable_methods()
        self.get_reachable_types()
        # create a folder to store the log of tqdm
        tqdm_log_module_folder = os.path.join(TQDM_LOG_PATH, self.repo_name, self.relative_path_to_module)
        self.create_folder(tqdm_log_module_folder)
        
        # compute the newest compatible version
        # use process pool to compute the versions in all_versions in parallel
        # I'll compute all versions, finally choose the newest compatible version
        num_workers = os.cpu_count()
        with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
            # initializing the progress bar
            pbar = tqdm(total=len(all_versions), desc=f"Dep in {self.repo_name}/{self.relative_path_to_module}", position=0, leave=True)
            # submit the tasks to the executor
            tasks = {executor.submit(self.version_compatibility_checker, version): version for version in all_versions}

            for _ in concurrent.futures.as_completed(tasks):
                # update the progress bar
                pbar.update(1)
            pbar.close()

        # find the newest compatible version from self.cur_node['Versions']
        best_version = self.get_best_version(self.cur_node['Versions'])
        
        # record the graph into json file
        self.record_graph()
        return best_version
            

    def get_best_version(self, Versions:list):
        """find the newest compatible version from Versions"""
        # Iterate in reverse order to find the first version without breaking_reason
        for version in Versions[::-1]:
            if not version['breaking_reason']:
                return version

    def version_compatibility_checker(self, version:str):
        """check if the version is compatible 
        Return:
            version (dict) : {'version': version, 'breaking_reason': breaking_reason}\n
            if breaking_reason is empty, then the version is compatible\n
            this dict is extracted from the self.cur_node['Versions'], and will be updated in the self.cur_node['Versions']\n
            as well as the graph
        """
        print('to be continued...')


    def get_reachable_methods(self):
        """record all reachable methods of the dependency and return the reachable callees\n
        Return:
            callees (list) : a list of reachable callee methods
        """
        if self.judge_dependent_empty():
            # if dependent is empty, then it is the client, and all methods are reachable
            client_groupId = self.cur_node['GroupId']
            client_artifactId = self.cur_node['ArtifactId']
            client_api = Api(client_groupId, client_artifactId, self.cur_node['Original_Version']) 
            client_cg = client_api.get_cg()
            reachable_methods = client_api.extract_methods_from_cg(client_cg)
            self.record_reachable_apis(reachable_methods, 'methods')

        else:
            # dependent is not empty, then get the callees are the entry points
            for dependent in self.cur_node['Dependents']:
                dependent_groupId = dependent['GroupId']
                dependent_artifactId = dependent['ArtifactId']
                dependent_version = dependent['Version']
                defined_version = dependent['Defined_Version']
                self.append_callee(dependent_groupId, dependent_artifactId, defined_version, 'methods')
            print('to be continued...')

    def append_callee(self, dependent_groupId:str, dependent_artifactId:str, defined_version:str, api_type:str):
        """append the callee to the reachable_method_callee or reachable_type_callee
        dict in reachable_method_callee or reachable_type_callee is like:\n
            
        """
        if api_type == 'methods':
            callees = self.get_callee(dependent_groupId, dependent_artifactId, defined_version, api_type)
            self.reachable_method_callee.append()
        elif api_type == 'types':
            callees = self.get_callee(dependent_groupId, dependent_artifactId, defined_version, api_type)
            self.reachable_type_callee.extend(callees)
        else:
            raise ValueError("Invalid api_type. Must be 'methods' or 'types'.")

    def get_reachable_types(self):
        """get all reachable types of the dependency"""
        # if dependent is empty, then it is the client, and all types are reachable
        print('to be continued...')

    def get_callee(self, dependent_groupId:str, dependent_artifactId:str, defined_version:str, api_type:str):
        """get the callees in current dependency
        Return:
            reachable_pair (list) : a list of tuple, each tuple is a pair of caller and callee\n
            the caller is in the dependent, and the callee is in the current dependency
        """
        dependent_reachable_apis = self.read_reachable_apis(dependent_groupId, dependent_artifactId, api_type)
        api = Api(self.cur_node['GroupId'], self.cur_node['ArtifactId'], defined_version)
        if api_type == 'methods':
            cur_node_methods = api.extract_methods_from_cg(api.get_cg())
            method_set = set(cur_node_methods)
            callees = [api for api in dependent_reachable_apis if api in method_set]
            return callees
        elif api_type == 'types':
            cur_node_types = api.extract_types_from_dg(api.get_type_dg())
            type_set = set(cur_node_types)
            callees = [api for api in dependent_reachable_apis if api in type_set]
            return callees

    def create_folder(self, folder:str):
        """create a folder if not exists"""
        if not os.path.exists(folder):
            os.makedirs(folder)

    def record_reachable_apis(self, reachable_apis:list, apis_type:str):
        """record the reachable apis (methods or types) of the dependency in this module\n
        usually record the reachable apis of this dependency
        Args:
            reachable_apis (list) : a list of reachable api
            apis_type (str) : 'methods' or 'types'
        """
        module_folder = os.path.join(REACHABLE_API_DIR, self.repo_name, self.relative_path_to_module, f'{self.cur_node["GroupId"]}', f'{self.cur_node["ArtifactId"]}')
        self.create_folder(module_folder)
        if apis_type == 'methods':
            module_file = os.path.join(module_folder, 'methods.json')
        elif apis_type == 'types':
            module_file = os.path.join(module_folder, 'types.json')
        else:
            raise ValueError("Invalid apis_type. Must be 'methods' or 'types'.")
        # write the reachable apis into the file
        with open(module_file, 'w', encoding='utf-8') as f:
            for api in reachable_apis:
                f.write(api)
                f.write('\n')

    def read_reachable_apis(self, group_id:str, artifact_id:str, apis_type:str):
        """read the reachable apis (methods or types) of the dependency in this module\n
        usually read the reachable apis of the dependent of this dependency
        Return:
            reachable_apis (list) : a list of reachable api
        """
        module_folder = os.path.join(REACHABLE_API_DIR, self.repo_name, self.relative_path_to_module, group_id, artifact_id)
        if apis_type == 'methods':
            module_file = os.path.join(module_folder, 'methods.txt')
        elif apis_type == 'types':
            module_file = os.path.join(module_folder, 'types.txt')
        else:
            raise ValueError("Invalid apis_type. Must be 'methods' or 'types'.")
        # read the reachable apis from the file
        with open(module_file, 'r', encoding='utf-8') as f:
            reachable_apis = [line.strip() for line in f.readlines()]
        return reachable_apis

    def record_graph(self):
        """record the graph into json file"""
        with open(self.json_path, 'w', encoding='utf-8') as f:
            json.dump(self.graph, f, ensure_ascii=False, indent=4)

    def judge_dependent_empty(self):
        """judge if the dependent is empty"""
        if not self.cur_node['Dependents']:
            return True
        return False