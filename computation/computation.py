"""get the newest compatible version of a dependency"""
import os
import concurrent.futures
import copy
import json
import tqdm
from constants import TQDM_LOG_PATH, REACHABLE_API_DIR
from computation.versions import get_all_versions
from computation.api import Api
from compuation.revapi import Revapi
from database.query import query_to_get_jar_location
from preprocess import Restore
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
        # method_caller_callee_pair and type_caller_callee_pair are used to compare with the Revapi result
        # these two list are got by get_entry_points_and_caller method
        self.method_entry_points = []
        self.type_entry_points = []
        
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
            self.cur_node['Versions'] = [{'version': version, 'breaking_reason':[]} for version in all_versions]

        if not all_versions:
            return self.cur_node['Original_Version']

        # get entry points and caller of the dependency
        for dependent in self.cur_node['Dependents']:
            self.get_entry_points_and_caller(dependent['GroupId'], dependent['ArtifactId'], dependent['Version'], dependent['Define_Version'], 'methods')
            self.get_entry_points_and_caller(dependent['GroupId'], dependent['ArtifactId'], dependent['Version'], dependent['Define_Version'], 'types')
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
        # find the dict in self.cur_node['Versions'] with the version
        for version_dict in self.cur_node['Versions']:
            if version_dict['version'] == version:
                ret_dict = version_dict
                break
        # clear ret_dict['breaking_reason'] first
        ret_dict['breaking_reason'] = []
        # judge if this node is direct dependency
        depth = self.cur_node['Depth']
        if depth == 1:
            binary_or_source = 'binary'
        else:
            binary_or_source = 'source'
        # for each dict in method_entry_points and type_entry_points, compare the entry points with BC api from Revapi result
        for method_entry_point in self.method_entry_points:
            baselineVersion = method_entry_point['baselineVersion']
            old_jar = query_to_get_jar_location(self.cur_node['GroupId'], self.cur_node['ArtifactId'], baselineVersion)
            Restore.get_dep_jar(self.cur_node['GroupId'], self.cur_node['ArtifactId'], baselineVersion)
            new_jar = query_to_get_jar_location(self.cur_node['GroupId'], self.cur_node['ArtifactId'], version)
            Restore.get_dep_jar(self.cur_node['GroupId'], self.cur_node['ArtifactId'], version)
            revapi = Revapi(old_jar, new_jar)
            bc_method, _ = revapi.get_bc_api(self.cur_node['GroupId'], self.cur_node['ArtifactId'], baselineVersion, version, binary_or_source)
            client_impacting_methods = self.intersect_api(bc_method, method_entry_point['api'])
            for client_impacting_method in client_impacting_methods:
                breaking_reason = {
                    'api': client_impacting_method,
                    'dependent': method_entry_point['dependent'],
                    'callers': [caller for caller in method_entry_point['api'][client_impacting_method]],
                    'record': bc_method[client_impacting_method]
                }
                ret_dict['breaking_reason'].append(breaking_reason)
        for type_entry_point in self.type_entry_points:
            baselineVersion = type_entry_point['baselineVersion']
            old_jar = query_to_get_jar_location(self.cur_node['GroupId'], self.cur_node['ArtifactId'], baselineVersion)
            Restore.get_dep_jar(self.cur_node['GroupId'], self.cur_node['ArtifactId'], baselineVersion)
            new_jar = query_to_get_jar_location(self.cur_node['GroupId'], self.cur_node['ArtifactId'], version)
            Restore.get_dep_jar(self.cur_node['GroupId'], self.cur_node['ArtifactId'], version)
            revapi = Revapi(old_jar, new_jar)
            _, bc_type = revapi.get_bc_api(self.cur_node['GroupId'], self.cur_node['ArtifactId'], baselineVersion, version, binary_or_source)
            client_impacting_types = self.intersect_api(bc_type, type_entry_point['api'])
            for client_impacting_type in client_impacting_types:
                breaking_reason = {
                    'api': client_impacting_type,
                    'dependent': type_entry_point['dependent'],
                    'callers': [caller for caller in type_entry_point['api'][client_impacting_type]],
                    'record': bc_type[client_impacting_type]
                }
                ret_dict['breaking_reason'].append(breaking_reason)
        return ret_dict

    @staticmethod
    def intersect_api(api1:dict, api2:dict):
        """intersect two api dicts to get the common api
        Args:
            api1 : the first api dict, its key is an api
            api2 : the second api dict, its key is an api
        """
        common_apis = set(api1.keys() & api2.keys())
        return common_apis

    def get_and_record_reachable_api(self, best_version = None):
        """record all reachable caller_callee_pairs of the dependency at the best version\n"""
        if best_version is None:
            # if best_version is None , then it is the client, and all methods are reachable
            # its actual best_version is the Original_Version
            # note : this branch is executed only once
            client_groupId = self.cur_node['GroupId']
            client_artifactId = self.cur_node['ArtifactId']
            client_api = Api(client_groupId, client_artifactId, self.cur_node['Original_Version'])
            client_cg = client_api.get_cg()
            client_cg_dict = Api.parse_call_relations(client_cg)
            self.record_reachable_apis(client_cg_dict, 'methods')
            client_dg = client_api.get_type_dg()
            client_dg_dict = Api.parse_call_relations(client_dg)
            self.record_reachable_apis(client_dg_dict, 'types')
        else:
            best_version_api = Api(self.cur_node['GroupId'], self.cur_node['ArtifactId'], best_version)
            best_version_cg = best_version_api.get_cg()
            entry_point_methods = self.get_entry_points_set('methods')
            method_call_relations = Api.parse_call_relations(best_version_cg)
            reachable_method_pairs = Api.find_reachable_calls(method_call_relations, entry_point_methods)
            self.record_reachable_apis(reachable_method_pairs, 'methods')
            entry_point_types = self.get_entry_points_set('types')
            best_version_dg = best_version_api.get_type_dg()
            type_call_relations = Api.parse_call_relations(best_version_dg)
            reachable_type_pairs = Api.find_reachable_calls(type_call_relations, entry_point_types)
            self.record_reachable_apis(reachable_type_pairs, 'types')

    def get_entry_points_and_caller(self, dependent_groupId:str, dependent_artifactId:str, dependent_version:str, defined_version:str, api_type:str):
        """get the entry points in the dependency and the corresponding caller in the dependent\n
        dict in reachable_method_callee or reachable_type_callee is like:\n
            {
                'dependent': dependent_groupId:dependent_artifactId:dependent_version
                'baselineVerison': defined_version
                'api': {
                    callee : the set of corresponding callers
                }
            }
        the callee is the entry point; 'api' is a dict of callee -> set of callers
        """
        defined_version_api = Api(self.cur_node['GroupId'], self.cur_node['ArtifactId'], defined_version)
        dependent_reachable_apis = self.read_reachable_apis(dependent_groupId, dependent_artifactId, api_type)
        if api_type == 'methods':
            defined_version_cg = defined_version_api.get_cg()
            all_methods = defined_version_api.extract_methods_from_cg(defined_version_cg)
            matching_method_pairs = Api.find_matching_relations(dependent_reachable_apis, all_methods)
            entry_point_dict = {
                'dependent': f'{dependent_groupId}:{dependent_artifactId}:{dependent_version}',
                'baselineVersion': defined_version,
                'api': {}
            }
            for pair in matching_method_pairs:
                entry_point_dict['api'].setdefault(pair[1], set()).add(pair[0])
            self.method_entry_points.append(entry_point_dict)
        elif api_type == 'types':
            defined_version_dg = defined_version_api.get_type_dg()
            all_types = defined_version_api.extract_types_from_dg(defined_version_dg)
            matching_type_pairs = Api.find_matching_relations(dependent_reachable_apis, all_types)
            entry_point_dict = {
                'dependent': f'{dependent_groupId}:{dependent_artifactId}:{dependent_version}',
                'baselineVersion': defined_version,
                'api': {}
            }
            for pair in matching_type_pairs:
                entry_point_dict['api'].setdefault(pair[1], set()).add(pair[0])
            self.type_entry_points.append(entry_point_dict)
        else:
            raise ValueError("Invalid api_type. Must be 'methods' or 'types'.")

    def get_entry_points_set(self, api_type:str):
        """get the set of entry points of the dependency for reachable api"""
        if api_type == 'methods':
            return set([api['callee'] for api in self.method_entry_points])
        elif api_type == 'types':
            return set([api['callee'] for api in self.type_entry_points])


    def create_folder(self, folder:str):
        """create a folder if not exists"""
        if not os.path.exists(folder):
            os.makedirs(folder)

    def record_reachable_apis(self, reachable_apis:dict , apis_type:str):
        """record the reachable apis (methods or types) of the dependency in this module\n
        usually record the reachable apis of this dependency at the best version
        Args:
            reachable_apis (list) : A dictionary of caller -> callees relations\n
            key: caller, value: a set of the corresponding callees\n
            apis_type (str) : 'methods' or 'types'
        """
        module_folder = os.path.join(REACHABLE_API_DIR, self.repo_name, self.relative_path_to_module, f'{self.cur_node["GroupId"]}', f'{self.cur_node["ArtifactId"]}')
        self.create_folder(module_folder)
        if apis_type == 'methods':
            module_file = os.path.join(module_folder, 'methods.txt')
        elif apis_type == 'types':
            module_file = os.path.join(module_folder, 'types.txt')
        else:
            raise ValueError("Invalid apis_type. Must be 'methods' or 'types'.")
        # write the reachable apis into the file
        with open(module_file, 'w', encoding='utf-8') as f:
            for caller, callees in reachable_apis.items():
                for callee in callees:
                    f.write(f'{caller} -> {callee}\n')

    def read_reachable_apis(self, group_id:str, artifact_id:str, apis_type:str):
        """read the reachable caller_callee_pairs (methods or types) of the dependency in this module\n
        usually read the reachable apis of the dependent of cur_node
        Return:
            reachable_apis : A dictionary of caller -> callees relations tuple\n
            key: caller, value: a set of the corresponding callees\n
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
            call_relations_str = f.read()
        reachable_apis = Api.parse_call_relations(call_relations_str)
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

if __name__ == '__main__':
    # test get caller and callee
    # # test case 1 : org.apache.druid.extensions.contrib:druid-influxdb-emitter:28.0.1
    # # -> joda-time:joda-time:2.12.5
    # client_dict = {
    #     'GroupId': 'org.apache.druid.extensions.contrib',
    #     'ArtifactId': 'druid-influxdb-emitter',
    #     'Original_Version': '28.0.1',
    #     'Best_Version': '',
    #     'Depth':0,
    #     'Count':0,
    #     'Dependents':[]
    # }
    # client = Computation(client_dict, [], '', 'test', 'example1')
    # client.get_and_record_reachable_api()
    
    # dep_dict = {
    #     'GroupId': 'joda-time',
    #     'ArtifactId': 'joda-time',
    #     'Original_Version': '2.12.5',
    #     'Best_Version': '',
    #     'Depth':1,
    #     'Count':0,
    #     'Dependents':[
    #         {
    #             'GroupId': 'org.apache.druid.extensions.contrib',
    #             'ArtifactId': 'druid-influxdb-emitter',
    #             'Version': '28.0.1',
    #             'Define_Version': '2.12.5'
    #         }
    #     ]
    # }
    # dep = Computation(dep_dict, [], '', 'test', 'example1')
    # # get dep's entry points and caller
    # dep.get_entry_points_and_caller('org.apache.druid.extensions.contrib', 'druid-influxdb-emitter', '28.0.1', '2.12.5', 'methods')
    # dep.get_entry_points_and_caller('org.apache.druid.extensions.contrib', 'druid-influxdb-emitter', '28.0.1', '2.12.5', 'types')
    # # print methods and types entry points
    # print(dep.method_entry_points)
    # print(dep.type_entry_points)
    # # result: method_entry_points is empty, and type_entry_points has one fp 'org.joda.time.DateTime' due to soot_Type_DG
    
    # test case 2 : cat.inspiracio:dwr:3.0.1 -> joda-time:joda-time:2.12.7
    client_dict = {
        'GroupId': 'cat.inspiracio',
        'ArtifactId': 'dwr',
        'Original_Version': '3.0.1',
        'Best_Version': '',
        'Depth':0,
        'Count':0,
        'Dependents':[]
    }
    client = Computation(client_dict, [], '', 'test', 'example2')
    client.get_and_record_reachable_api()
    
    dep_dict = {
        'GroupId': 'joda-time',
        'ArtifactId': 'joda-time',
        'Original_Version': '2.12.7',
        'Best_Version': '',
        'Depth':1,
        'Count':0,
        'Dependents':[
            {
                'GroupId': 'cat.inspiracio',
                'ArtifactId': 'dwr',
                'Version': '3.0.1',
                'Define_Version': '2.12.7'
            }
        ]
    }
    dep = Computation(dep_dict, [], '', 'test', 'example2')
    # get dep's entry points and caller
    dep.get_entry_points_and_caller('cat.inspiracio', 'dwr', '3.0.1', '2.12.7', 'methods')
    dep.get_entry_points_and_caller('cat.inspiracio', 'dwr', '3.0.1', '2.12.7', 'types')
    # print methods and types entry points
    print(dep.method_entry_points)
    print(dep.type_entry_points)
    # result : method_entry_points has 3 fn 'org.joda.time.LocalDateTime::toDateTime()', 'org.joda.time.base.AbstractInstant::toDate()'
    # and 'org.joda.time.base.BaseDateTime::getMillis()'. First two are called on line 56 of org.directwebremoting.convert.LocalDateTimeConverter.java
    # the last one is called on line 57 of org.directwebremoting.convert.LocalDateTimeConverter.java.
    # the reason is these 3 methods are not present in the call graph of dwr-3.0.1.jar, which reveals a fn of sootCG on dwr-3.0.1.jar