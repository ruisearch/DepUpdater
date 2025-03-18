"""restore tree to graph"""
import concurrent.futures
import json
import os
import re
import shutil
import time

import requests

from constants import JAR_DIR, TREE_DIR, VERSIONS_DIR
from database.query import query_to_get_jar_location
from computation.versions import get_candidate_versions
from logger.logger import log_debug


class Restore:
    def __init__(self, path_to_cloned_folder:str, relative_path_to_module:str,\
        tree_path:str, local_module_inform:dict, local_dep_jar:list):
        """
        Args :
            path_to_cloned_folder : path to cloned folder
            relative_path_to_module : relative path from project root
            tree_path : path to tree file
            local_module_inform : all local modules' gav --> their relative path
            local_dep_jar : the input relative path to the local dep jar
        """
        self.path_to_cloned_folder = path_to_cloned_folder
        self.relative_path_to_module = relative_path_to_module
        self.tree_path = tree_path
        self.client_groupId = None
        self.client_artifactId = None
        self.client_version = None
        self.local_module_inform = local_module_inform
        self.path_to_local_dep_jar = local_dep_jar
        self.create_folder(TREE_DIR)
        self.create_folder(JAR_DIR)

    def create_folder(self, folder_path:str):
        """create a folder"""
        # Check if the folder already exists
        if os.path.exists(folder_path):
            return
        # Create an empty folder
        os.makedirs(folder_path)

    def restore(self, client_jar_path:str):
        """main method in this file,restore
        Args:
            client_jar_path : relative path to client jar
            
        """
        # create TREE folder
        self.create_folder(TREE_DIR)
        # parse
        with open(self.tree_path, 'r', encoding='utf-8') as tree:
            dependency_tree = tree.read()
        # parse tree
        all_deps = self.parse_tree_for_deps(dependency_tree, self.path_to_cloned_folder, self.relative_path_to_module, client_jar_path)
        # filter the deps into valid_deps and omitted_deps
        valid_deps, omitted_deps = self.filter_dep(all_deps)
        # parse the dep in valid_deps and omitted_deps to get jar and version.json
        json_path, original_json_path, local_dep_gav = self.parse_for_jar_and_json(valid_deps, omitted_deps)
        return json_path, original_json_path,  local_dep_gav

    def filter_dep(self, all_deps:list):
        """filter the deps into valid_deps and omitted_deps"""
        valid_deps = []
        omitted_deps = []
        for dep in all_deps:
            if dep['dep'].startswith('('):
                # omitted dep
                omitted_deps.append(dep)
            else:
                valid_deps.append(dep)
        return valid_deps, omitted_deps

    @staticmethod
    def get_dep_jar(group_id:str, artifact_id:str, version:str)->bool:
        """get dep jar using GAV from maven central repository and store them in data/jar
            
        Returns:
            True means downloading success while False means downloading fail
        """
        # debug
        # print(f'dep {group_id}:{artifact_id}:{version}')

        def handle_error_get(jar_url,  retries=3, backoff_factor=0.3):
        # This inner function attempts to get the content from the jar_url with retries
            for attempt in range(retries):
                try:
                    response = requests.get(jar_url, timeout=10)  # Set timeout to prevent hanging
                    response.raise_for_status()  # Will raise an HTTPError for bad responses
                    return response
                except requests.RequestException as e:
                    # print(f"Attempt {attempt + 1} failed for {artifact_id}-{version}.jar: {str(e)}")
                    time.sleep(backoff_factor * (2 ** attempt))  # Exponential backoff
                    if attempt == retries - 1:
                        raise  # Re-raise the last exception if all retries fail

        jar_url = f"https://repo1.maven.org/maven2/{group_id.replace('.', '/')}/{artifact_id}/{version}/{artifact_id}-{version}.jar"
        
        # Call the function with retry logic
        try:
            file_name = query_to_get_jar_location(group_id, artifact_id, version)
            # prevent download repeatly
            if os.path.exists(file_name):
                # print(f"{artifact_id}-{version}.jar has been downloaded before.")
                return True
            response = handle_error_get(jar_url)
            # Proceed if the download was successful
            if response and response.status_code == 200:
                with open(file_name, "wb") as jar_file:
                    jar_file.write(response.content)
                    print(f"{artifact_id}-{version}.jar downloaded successfully.")
                    return True
        except Exception as e:
            # print(f"Failed to download {artifact_id}-{version}.jar from central repository; Reason: {str(e)}")
            log_debug(f"Failed to download {artifact_id}-{version}.jar from central repository; Reason: {str(e)}")
            return False

    def parse_tree_for_deps(self, dependency_tree:str, path_to_cloned_folder:str, relative_path_to_module:str, relative_path_to_client_jar:str):
        """parse tree(verbose) to get a list of deps\
            (without information like GAV, just the record as well as the dependents and depth)\n
            create the Jar folder and copy client jar as well

            Returns:
                a list containing all deps
        """
        ## regular expression to get a block
        block_pattern = r'\[INFO\] Building .+?\n\[INFO\].+?from (.*?)pom.xml\n\[INFO\] -+?\[ (.+?) \]-+?\n.*?\[INFO\] (\S+?):(\S+?):\S+?:(\S+?)\n(.+?)\[INFO\] -'
        blocks = re.finditer(block_pattern, dependency_tree, flags=re.DOTALL)
        print("\n****** extract deps... ******\n")
        for block in blocks:
            # print(block.group(0)) # block
            # print(block.group(1)) # module folder
            # print(block.group(2)) # type(like jar)
            # print(block.group(3)) # client groupId
            # print(block.group(4)) # client artifactId
            # print(block.group(5)) # client version
            # print(block.group(6)) # deps

            # only handle the specific module in the tree(may contain multiple modules)
            # if relative_path_to_module is ., the module's pom is at the root
            if relative_path_to_module == '.':
                flag = (block.group(1) == '')
            elif relative_path_to_module.endswith('/'):
                # the second parameter represents the relative path to the module ends with '/'
                # block.group(1) endswith '/'
                flag = (block.group(1) == relative_path_to_module)
            else :
                flag = (block.group(1) == relative_path_to_module+'/')
            if block.group(2) == 'jar' and flag:
                self.client_groupId = block.group(3)
                self.client_artifactId = block.group(4)
                self.client_version = block.group(5)
                # get the module name(replace '/' with '_' to appear in folder name)
                module = block.group(1)
                if module == '':
                    # the module pom is at the root of project
                    module = '_'
                if not relative_path_to_client_jar:
                    # jar is in target and the name follows this format: artifactId-version.jar
                    # copy client jar
                    target = os.path.join(path_to_cloned_folder, f"{block.group(1)}target")
                    # normal name follows this format: artifactId-version.jar
                    client_jar = f"{self.client_artifactId}-{self.client_version}.jar"
                    path_to_client_jar_in_repo = os.path.join(target, client_jar)
                    path_to_client_jar_storage = query_to_get_jar_location(self.client_groupId,\
                        self.client_artifactId, self.client_version)
                else:
                    # location of client jar is specified by user input, naming args.jar
                    path_to_client_jar_in_repo = os.path.join(path_to_cloned_folder, relative_path_to_client_jar)
                    path_to_client_jar_storage = query_to_get_jar_location(self.client_groupId,\
                        self.client_artifactId, self.client_version)
                # store client jar
                try:
                    shutil.copy(path_to_client_jar_in_repo, path_to_client_jar_storage)
                except FileNotFoundError as e:
                    # the jar name is not as expect
                    print(e)
                    print("the client jar is not in ... target/artifactId-version.jar, please input its relative path!")
                    exit(1)
                # client jar has been stored in data/jar/
                
                # parse tree to get all deps
                deps = self.parse_all_dep(block.group(6))
                
                # debug : write deps to RET_DIR/{repo_name}/{relative_path_to_module}/deps.json
                # ret_folder = os.path.join(RET_DIR, f'{os.path.basename(path_to_cloned_folder)}/{self.relative_path_to_module}')
                # self.create_folder(ret_folder)
                # dep_path = os.path.join(ret_folder, 'deps.json')
                # with open(dep_path, 'w', encoding='utf-8') as dep_file:
                #     json.dump(deps, dep_file, indent=4)
                return deps

    def parse_all_dep(self,tree:str):
        """return a list containing all deps as well as the dependent and dep\n
        the list contains valid deps as well as omitted deps denoted by dict{dep, Depth, Dependents}
        """
        dep_pattern = r"^\[INFO\] (.*?)- (.+?)$"
        dep_matches = re.finditer(dep_pattern, tree, re.MULTILINE)
        # group(1): lag
        # group(2): dep

        deps = []
        for dep_match in dep_matches:
            # is_test = ":test" in dep_match.group(2)
            # is_provided = ":provided" in dep_match.group(2)
            # # exclude the dependency for test or provided
            # if is_test is False and is_provided is False:
            #     dep = {}
            #     # {'dep': the record in tree list 'org.junit-pioneer:junit-pioneer:jar:1.9.1:compile'}
            #     dep.update({'dep':dep_match.group(2)})
            #     # get depth from the length of substring between "[INFO] " and "-"
            #     depth = (int)((len(dep_match.group(1))+2) / 3)
            #     # depth == 1 means direct while depth > 1 means transitive
            #     dep.update({'Depth':depth})
            #     deps.append(dep)

            dep = {}
            # {'dep': the record in tree list 'org.junit-pioneer:junit-pioneer:jar:1.9.1:compile'}
            dep.update({'dep':dep_match.group(2)})
            # get depth from the length of substring between "[INFO] " and "-"
            depth = (int)((len(dep_match.group(1))+2) / 3)
            # depth == 1 means direct while depth > 1 means transitive
            dep.update({'Depth':depth})
            deps.append(dep)

        # get dependent(parent in tree actually) of all deps
        for idx, one_dep in enumerate(deps):
            dependent_depth = one_dep['Depth'] - 1
            Dependents = []
            if dependent_depth == 0:
                    # dependent is client
                    Dependent = {'GroupId':self.client_groupId, 'ArtifactId':self.client_artifactId,\
                        'Version': self.client_version}
                    Dependents.append(Dependent)
            else:
                for i in range(idx, -1, -1):
                    if deps[i]['Depth'] == dependent_depth:
                        # note: "Dependents" above are dependents like "org.mockito:mockito-core:jar:4.11.0:compile"
                        # and Dependents are always valid deps or client
                        # so, I change the record into the dict in order to relate the dependent with the dep when clearing the local module
                        # dict is {'GroupId', 'ArtifactId', 'Version'}

                        # note: record_to_dict may return None means the record cannot be parsed like "org.apache.activemq:activemq-broker:test-jar:tests:5.18.6:test"
                        # the Dependent is ignored and such one_dep should be removed from deps finally
                        Dependent = self.record_to_dict(deps[i]['dep'])
                        Dependents.append(Dependent)
                        break
            one_dep.update({"Dependents":Dependents})
        # # remove dep that dependent cannot be parsed
        # for i in range(len(deps)-1, -1, -1):
        #     if None in deps[i]['Dependents']:
        #         del deps[i]
        return deps

    # dep key:{dep, Depth, Dependents}
    def parse_for_jar_and_json(self, valid_deps:list, omitted_deps:list):
        """parse the dep in valid_deps and omitted_deps to get jar and version.json
        
        Args:
            module_folder : path to data/Jar/{module_name}
        Returns:
            json_path : path to the version.json
            original_json_path : path to the original_version.json(graph before updating)
            original_tech_lag : the original tech lag of the module
            local_dep_gav : a list of local dep
        """
        # change the valid_deps
        self.change_valid_deps(valid_deps)
        # change the omitted_deps
        self.change_omitted_deps(omitted_deps)
        # # clearing the local modules which couldn't be downloaded from maven central repository
        # # and optional transitive deps as well
        # self.clear_spare_deps(valid_deps, omitted_deps)
        # get dep jar and update the list of dicts which will be displayed in json
        # jarname ----> gav
        mappings = [{'GroupId':self.client_groupId, 'ArtifactId':self.client_artifactId,\
            'Original_Version':self.client_version, 'Best_Version':'', 'Type':'',\
                'Depth':0, 'Count':0, 'Dependents':[]}] # add client at first
        # traverse the valid_deps using processPool
        num_workers = os.cpu_count()
        with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
            futures = []
            for valid_dep in valid_deps:
                futures.append(executor.submit(self.process_a_valid_dep, valid_dep, omitted_deps))
        for future in futures:
            mappings.append(future.result())
            
        # add omitted deps which have no corresponding valid dep
        self.process_omitted_deps(valid_deps, omitted_deps, mappings)

        # prune the graph: remove the dependencies aren't compile or runtime and local module
        local_dep_gav = self.prune_graph(mappings)
        # remove the nodes which have been removed
        mappings = [node for node in mappings if node['Dependents'] or node['Depth'] == 0]
        # get original tech lag(sum and each depth 1 ~10 and >10)
        # original_tech_lag = self.compute_original_tech_lag(mappings, local_dep_gav)
        # create json
        # stored in data/rq3_result/{repo_name}/{relative_path_to_module}/version.json
        repo_name = os.path.basename(self.path_to_cloned_folder)
        if self.relative_path_to_module == '.':
            json_folder = os.path.join(VERSIONS_DIR, f'{repo_name}', '_')
        else:
            json_folder = os.path.join(VERSIONS_DIR, f'{repo_name}', f'{self.relative_path_to_module}')
        self.create_folder(json_folder)
        json_path = os.path.join(json_folder, 'version.json')
        with open(json_path, 'w', encoding='utf-8') as json_file:
            json.dump(mappings, json_file, indent=4)
        # store the original mapping in original_version.json
        original_json_path = os.path.join(json_folder, 'original_version.json')
        with open(original_json_path, 'w', encoding='utf-8') as original_json_file:
            json.dump(mappings, original_json_file, indent=4)
        # return json_path, original_json_path, original_tech_lag, local_dep_gav
        return json_path, original_json_path, local_dep_gav

    # remove the dependencies aren't compile or runtime and local module(if necessary)
    def prune_graph(self, mappings:list):
        """prune the graph: remove the dependencies aren't compile or runtime
        Return:
            local_dep (list): a list of gav of the local deps
        """
        print('\n****** prune graph ... ******\n')
        log_debug('prune graph')
        # remove the dependencies aren't compile or runtime
        for node in mappings:
            if not node['Dependents']:
                # client or node has been removed
                continue
            if node['Type'] not in ['compile', 'runtime']:
                log_debug(f'{node["GroupId"]}:{node["ArtifactId"]} is not compile or runtime, so remove it')
                self.remove_node(node['GroupId']+':'+node['ArtifactId'], mappings)
        # download the jar of the nodes in the graph and remove the local module if not aim to handle multi-module
        local_dep_gav = []
        for node in mappings:
            if not node['Dependents']:
                # client or node has been removed
                continue
            flag = self.get_dep_jar(node['GroupId'], node['ArtifactId'], node['Original_Version'])
            if not flag:
                # the node cannot download
                # if want to handle multi-module which consider local dependency, use local_dep_handle
                flag = self.local_dep_handle(node['GroupId'], node['ArtifactId'], node['Original_Version'])
                if not flag:
                    # a dep not local dep and unavailable
                    # log_debug(f'{node["GroupId"]}:{node["ArtifactId"]} is a local module, so remove it')
                    log_debug(f'{node["GroupId"]}:{node["ArtifactId"]} is unavailable, so remove it')
                    self.remove_node(node['GroupId']+':'+node['ArtifactId'], mappings)
                else:
                    # a local dep
                    local_dep_gav.append(f"{node['GroupId']}:{node['ArtifactId']}:{node['Original_Version']}")

        return local_dep_gav

    def local_dep_handle(self, groupId:str, artifactId:str, version:str):
        """judge whether a node is a local dependency and return its jar path if it is
        Returns:
            flag (bool): whether it is a local dependency
        """
        if f'{groupId}:{artifactId}:{version}' not in self.local_module_inform:
            return False
        # a local dep
        module_path = self.local_module_inform[f'{groupId}:{artifactId}:{version}']
        target_folder_path = os.path.join(module_path, "target")
        # standard jar path
        local_dep_jar_path = os.path.join(self.path_to_cloned_folder, target_folder_path, f'{artifactId}-{version}.jar')
        # judge whether the path to jar is in self.path_to_local_dep_jar
        if self.path_to_local_dep_jar:
            # traverse the self.path_to_local_dep_jar
            for jar_path in self.path_to_local_dep_jar:
                if jar_path.startswith(target_folder_path):
                    local_dep_jar_path = os.path.join(self.path_to_cloned_folder, jar_path)
                    break
        # copy the local dep jar
        path_to_jar_storage = query_to_get_jar_location(groupId, artifactId, version)
        try:
            shutil.copy(local_dep_jar_path, path_to_jar_storage)
        except FileNotFoundError as e:
            # the jar name is not as expect
            print(e)
            print(f"the local dep {groupId}:{artifactId}:{version} is not \
                in {local_dep_jar_path}, please input its relative path!")
            exit(1)
        return True

    # remove a node from the graph
    def remove_node(self, ga:str, mappings:list):
        """remove the node and its outer-edges from the dependency graph recursively
        Args:
            ga (str): the groupId:artifactId of the dependency
            which should be removed from the graph
            mappings: list of dict representing the dependency graph
        """
        log_debug(f'{ga} removed')
        # handle the dependencies of ga first
        for node in mappings:
            if node['GroupId']+':'+node['ArtifactId'] == ga:
                # clear the dependents
                node['Dependents'] = []
                continue
            is_dependent = False
            dependent_idx = -1
            for idx, dependent in enumerate(node['Dependents']):
                if ga == dependent['GroupId']+':'+dependent['ArtifactId']:
                    # ga is a dependent of node
                    is_dependent = True
                    dependent_idx = idx
                    break
            if is_dependent:
                # remove ga from the dependents of node
                node['Dependents'].pop(dependent_idx)
                node_ga = node['GroupId']+':'+node['ArtifactId']
                if not node['Dependents']:
                    # if the node has no dependents now, remove the node from the graph
                    self.remove_node(node_ga, mappings)

    @staticmethod
    def compute_original_tech_lag(deps:list, local_dep_gav:list):
        """compute the original tech lag of the module
        Args:
            deps (list): a list of all dependencies in the graph
            local_dep_gav (list): a list of gav of local dep
        Returns:
            original_tech_lag (list): the original tech lag of the module\
            original_tech_lag[0] is the sum of the original tech lag\
            original_tech_lag[1] is the original tech lag of depth 1 and so on\
            original_tech_lag[11] is the original tech lag of depth > 10
        """
        original_tech_lag = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        for dep in deps:
            if dep['Depth'] == 0:
                # skip the client
                continue
            if f"{dep['GroupId']}:{dep['ArtifactId']}:{dep['Original_Version']}" in local_dep_gav:
                # local dep
                all_versions = [dep['Original_Version']]
            else:
                all_versions = get_candidate_versions(dep['GroupId'], dep['ArtifactId'], dep['Original_Version'])
            original_tech_lag[0] += len(all_versions) - 1
            if dep['Depth'] <= 10:
                original_tech_lag[dep['Depth']] += len(all_versions) - 1
            else:
                original_tech_lag[11] += len(all_versions) - 1
            # note: 'Versions' will be initialized in Computaion.initialize_breaking_reason
            # if 'Versions' not in dep:
            #     dep['Versions'] = [{'version': version, 'breaking_reason':[]} for version in all_versions]
        return original_tech_lag

    def process_omitted_deps(self, valid_deps:list, omitted_deps:list, mappings:list):
        """add omitted deps which have no corresponding valid dep,
        these valid deps are test or provided so that they are ignored
        Args:
            valid_deps : list of dict containing all valid_dep
            omitted_deps : list of dict containing all omitted_dep
            mappings: list of dict representing the dependency graph
        """
        valid_set = set()
        for valid_dep in valid_deps:
            valid_set.add(f"{valid_dep['GroupId']}:{valid_dep['ArtifactId']}")
        omitted_dict = {}
        for idx, omitted_dep in enumerate(omitted_deps):
            omitted_key = f"{omitted_dep['GroupId']}:{omitted_dep['ArtifactId']}"
            omitted_dict.setdefault(omitted_key, []).append(idx)
        omitted_set = set(omitted_dict.keys())

        added_omitted_deps = omitted_set - valid_set
        for ga in added_omitted_deps:
            first_idx = omitted_dict[ga][0]
            one_record = omitted_deps[first_idx]
            groupId = one_record['GroupId']
            artifactId = one_record['ArtifactId']
            original_version = one_record['Version']
            dtype = one_record['Type']
            depth = one_record['Depth']
            dependents = []
            for idx in omitted_dict[ga]:
                dependents.extend(omitted_deps[idx]['Dependents'])
            mappings.append(
                {
                    'GroupId': groupId,
                    'ArtifactId': artifactId,
                    'Original_Version': original_version,
                    'Best_Version': '',
                    'Type': dtype,
                    'Depth': depth,
                    'Count': 0,
                    'Dependents': dependents
                }
            )

    def clear_spare_deps(self,valid_deps:list, omitted_deps:list) -> None:
        """clear spare deps and their dependencies as well\n
            consider two kinds of deps : local module which couldn't be downloaded from maven central \
            repository(usually local module); optional transitive deps

        Args: 
            path_to_dep : path to Jar/{module}/dep
            valid_deps : {GroupId, ArtifactId, Version, Type, Depth, Dependents}\
                (from change_valid_deps)
        """
        valid_flag_list = [True for _ in valid_deps] # False means the element should be deleted
        omitted_flag_list = [True for _ in omitted_deps]
        for i, valid_dep in enumerate(valid_deps):
            optional_transitive_flag = valid_dep['Depth'] > 1 and valid_dep['isoptional'] == True
            if valid_flag_list[i] is True: # has not been removed
                flag = self.get_dep_jar(valid_dep['GroupId'], valid_dep['ArtifactId'], valid_dep['Version'])
                if flag is False or optional_transitive_flag is True:
                    # a local module or optional transitive dep
                    valid_flag_list[i] = False
                    # mark valid deps of spare dep
                    self.mark_dep_of_spare_deps(valid_dep, valid_deps, valid_flag_list)
                    # mark omitted dep of spare dep
                    self.mark_dep_of_spare_deps(valid_dep, omitted_deps, omitted_flag_list)
        self.remove_dep_of_spare_deps(valid_deps, valid_flag_list)
        self.remove_dep_of_spare_deps(omitted_deps, omitted_flag_list)

    def mark_dep_of_spare_deps(self, spare_dep:dict, dep_list:list, flag_list:list)->None:
        """mark the dependency(valid or omitted) of spare dep from tree
        
        Args:
            spare_dep : a dict presents a spare dep (from clear_spare_deps)
            dep_list : valid list or omitted list (from clear_spare_deps)
            flag_list : mark the elements in dep_list that should be deleted (from clear_spare_deps)
        """
        for i, dep in enumerate(dep_list):
            for dependent in dep['Dependents']:
                if dependent['GroupId'] == spare_dep['GroupId'] and \
                    dependent['ArtifactId'] == spare_dep['ArtifactId']:
                    # the dep is a dependency of the spare_dep
                    flag_list[i] = False
                    break

    def remove_dep_of_spare_deps(self, dep_list:list, flag_list:list)->None:
        """remove dep of local from dep_list from flags in flag_list
        
        Args:
            dep_list : valid list or omitted list (from clear_spare_deps)
            flag_list : mark the elements in dep_list that should be deleted (from clear_spare_deps)
        """
        for i in range(len(flag_list)-1, -1, -1):
            if flag_list[i] is False:
                del dep_list[i]

    def process_a_valid_dep(self, valid_dep:dict, omitted_deps:list)->dict:
        """process an valid dep: get the related omitted dep and restore the omitted dependency edge
        
        Args:
            valid_dep : a valid dep (from change_valid_deps)
            omitted_deps : the list of dict containing all Omitted_dep \n
                from change_omitted_deps \n

        Returns:
            the computed valid_dep which will be displayed in version.json\n
            {GroupId, ArtifactId, Original_Version, Best_Version, Type, Depth, Dependents}\n
            Dependents is a list of dict {GroupId, ArtifactId, Version, Define_Version}
        """
        valid_dep.pop('isoptional') # isoptional is not in need
        # find the related omitted_deps with the valid_dep and restore the omitted dependents of the tree
        for omitted_dep in omitted_deps:
            # # debug
            # print(omitted_dep)

            if omitted_dep['GroupId'] == valid_dep['GroupId'] and omitted_dep['ArtifactId'] == valid_dep['ArtifactId']:
                # omitted_dep is the omitted dep of valid_dep
                # download this omitted jar
                self.get_dep_jar(omitted_dep['GroupId'], omitted_dep['ArtifactId'],\
                    omitted_dep['Version'])
                self.add_omitted_dependents_of_a_dep(valid_dep['Dependents'], omitted_dep['Dependents'])
        result_dep = {
            'GroupId': valid_dep['GroupId'],
            'ArtifactId': valid_dep['ArtifactId'],
            'Original_Version': valid_dep['Version'],
            'Best_Version': '',
            'Type': valid_dep['Type'],
            'Depth': valid_dep['Depth'],
            'Count': 0,
            'Dependents': valid_dep['Dependents']
        }
        return result_dep

    def add_omitted_dependents_of_a_dep(self, existing_dependents:list, omitted_dependents:list)->None:
        """add the omitted_dependents to existing_dependents"""
        for omitted_dependent in omitted_dependents:
            # prevent add dependents repeatedly
            if omitted_dependent not in existing_dependents:
                existing_dependents.append(omitted_dependent)

    def record_to_dict(self, record:str):
        """transform a record(valid) in tree to dep{GroupId, ArtifactId, Version}"""
        # # debug
        # print(record)
        
        pattern = r"(.+?):(.+?):jar(.*):(.+?):.+?\b"
        match = re.search(pattern, record)
        if not match:
            # no match
            # like "org.apache.activemq:activemq-broker:test-jar:tests:5.18.6:test"
            pattern_1 = r"(.+?):(.+?):test-jar:tests(.*):(.+?):.+?\b"
            match = re.search(pattern_1, record)
        return {'GroupId':match.group(1), 'ArtifactId':match.group(2), 'Version':match.group(4)}

    def change_valid_deps(self, valid_deps:list):
        """change the valid_deps \n
        dep key:{dep, Depth, Dependents} --> dep key:{GroupId, ArtifactId, Version, Type, Depth, Dependents, isoptional}
        
        Args:
            valid_deps : from parse_all_dep
        """
        gav_pattern = r"(.+?):(.+?):jar(.*):(.+?):(.+?)\b"
        for i, valid_dep in enumerate(valid_deps):
            dep = {}
            match = re.search(gav_pattern, valid_dep['dep'])
            if not match:
                # like "org.apache.activemq:activemq-broker:test-jar:tests:5.18.6:test"
                gav_pattern_1 = r"(.+?):(.+?):test-jar:tests(.*):(.+?):(.+?)\b"
                match = re.search(gav_pattern_1, valid_dep['dep'])
            dep.update({'GroupId':match.group(1)})
            dep.update({'ArtifactId':match.group(2)})
            dep.update({'Version':match.group(4)})
            dep.update({'Type':match.group(5)})
            dep.update({'Depth':valid_dep['Depth']})
            Dependent = valid_dep['Dependents'][0]
            # Define_Version is the version defined by the dependent
            Dependent.update({'Define_Version':match.group(4)})
            dep.update({'Dependents':[Dependent]})
            isoptional_flag = 'optional' in match.group(5)
            dep.update({'isoptional': isoptional_flag})
            # test
            # print(dep)
            valid_deps[i] = dep


    def change_omitted_deps(self, omitted_deps:list):
        """change the omitted_deps \n
            dep key:{dep, Depth, Dependents} --> dep key:{GroupId, ArtifactId, Version, Type, Depth, Dependents}
            
        Args:
            omitted_deps : from parse_all_dep
        """
        # duplicate and covered by pom
        # eg:
        # (org.junit.platform:junit-platform-engine:jar:1.10.2:runtime - version managed from 1.10.2; omitted for duplicate)
        gav_pattern_1 = r"\((.+?):(.+?):jar(.*):(.+?):(.+?) - version managed from (.+?); omitted for duplicate\)"
        # duplicate but not covered by pom
        # eg:
        # (org.eclipse.sisu:org.eclipse.sisu.inject:jar:0.9.0.M2:compile - omitted for duplicate)
        gav_pattern_2 = r"\((.+?):(.+?):jar(.*):(.+?):(.+?) - omitted for duplicate\)"
        # conflict
        # eg:
        # (org.codehaus.plexus:plexus-classworlds:jar:2.6.0:compile - omitted for conflict with 2.7.0)
        gav_pattern_3 = r"\((.+?):(.+?):jar(.*):(.+?):(.+?) - omitted for conflict with (.+?)\)"
        # conflict and covered by pom
        # eg:
        # (org.glassfish.jaxb:jaxb-runtime:jar:2.3.8:test - version managed from 2.3.1; omitted for conflict with 2.3.2)
        gav_pattern_4 = r"\((.+?):(.+?):jar(.*):(.+?):(.+?) - version managed from (.+?); omitted for conflict with (.+?)\)"
        for i, omitted_dep in enumerate(omitted_deps):
            dep = {}
            match = re.search(gav_pattern_1, omitted_dep['dep'])
            if match is not None:
                # duplicate and covered by pom
                dep.update({'GroupId':match.group(1)})
                dep.update({'ArtifactId':match.group(2)})
                # dep.update({'Version':match.group(6)})
                dep.update({'Version':match.group(4)})
                dep.update({'Type':match.group(5)})
                dep.update({'Depth':omitted_deps[i]['Depth']})
                # Define_Version is the version defined by the dependent
                Dependent = omitted_dep['Dependents'][0]
                Dependent.update({'Define_Version':match.group(6)})
                dep.update({'Dependents':[Dependent]})
                omitted_deps[i] = dep
                continue
            match = re.search(gav_pattern_2, omitted_dep['dep'])
            if match is not None:
                # duplicate but not covered by pom
                dep.update({'GroupId':match.group(1)})
                dep.update({'ArtifactId':match.group(2)})
                dep.update({'Version':match.group(4)})
                dep.update({'Type':match.group(5)})
                dep.update({'Depth':omitted_deps[i]['Depth']})
                # Define_Version is the version defined by the dependent
                Dependent = omitted_dep['Dependents'][0]
                Dependent.update({'Define_Version':match.group(4)})
                dep.update({'Dependents':[Dependent]})
                omitted_deps[i] = dep
                continue
            match = re.search(gav_pattern_3, omitted_dep['dep'])
            if match is not None:
                # conflict
                dep.update({'GroupId':match.group(1)})
                dep.update({'ArtifactId':match.group(2)})
                # dep.update({'Version':match.group(4)})
                dep.update({'Version':match.group(6)})
                dep.update({'Type':match.group(5)})
                dep.update({'Depth':omitted_deps[i]['Depth']})
                # Define_Version is the version defined by the dependent
                Dependent = omitted_dep['Dependents'][0]
                Dependent.update({'Define_Version':match.group(4)})
                dep.update({'Dependents':[Dependent]})
                omitted_deps[i] = dep
                continue
            match = re.search(gav_pattern_4, omitted_dep['dep'])
            if match is not None:
                # conflict and covered by pom
                dep.update({'GroupId':match.group(1)})
                dep.update({'ArtifactId':match.group(2)})
                dep.update({'Version':match.group(7)})
                dep.update({'Type':match.group(5)})
                dep.update({'Depth':omitted_deps[i]['Depth']})
                # Define_Version is the version defined by the dependent
                Dependent = omitted_dep['Dependents'][0]
                Dependent.update({'Define_Version':match.group(4)})
                dep.update({'Dependents':[Dependent]})
                omitted_deps[i] = dep
                continue
# test
if __name__ == "__main__":
    # # test remove_dep_of_local_module
    # test_list = [1, 2, 3, 4, 5]
    # test_flag_list = [True, False, True, False, True]
    # ex = Restore(None, None, None)
    # # ex.remove_dep_of_local_module(test_list, test_flag_list)
    # print(test_list)

    # test
    tree = """[INFO] Scanning for projects...
[WARNING] 
[WARNING] Some problems were encountered while building the effective model for org.eolang:eo-parser:jar:0.51.6
[WARNING] 'build.plugins.plugin.version' for org.codehaus.gmaven:groovy-maven-plugin is missing. @ line 197, column 15
[WARNING] 
[WARNING] It is highly recommended to fix these problems because they threaten the stability of your build.
[WARNING] 
[WARNING] For this reason, future Maven versions might no longer support building such malformed projects.
[WARNING] 
[INFO] ------------------------------------------------------------------------
[INFO] Reactor Build Order:
[INFO] 
[INFO] eo                                                                 [pom]
[INFO] eo-parser                                                          [jar]
[INFO] eo-maven-plugin                                           [maven-plugin]
[INFO] 
[INFO] ------------------------< org.eolang:eo-parent >------------------------
[INFO] Building eo 0.51.6                                                 [1/3]
[INFO]   from pom.xml
[INFO] --------------------------------[ pom ]---------------------------------
[INFO] 
[INFO] --- dependency:3.7.1:tree (default-cli) @ eo-parent ---
[INFO] org.eolang:eo-parent:pom:0.51.6
[INFO] +- org.openjdk.jmh:jmh-core:jar:1.37:test
[INFO] |  +- net.sf.jopt-simple:jopt-simple:jar:5.0.4:test
[INFO] |  \- org.apache.commons:commons-math3:jar:3.6.1:test (version managed from 3.6.1)
[INFO] +- org.apache.groovy:groovy:jar:5.0.0-alpha-12:test
[INFO] \- org.apache.groovy:groovy-xml:jar:5.0.0-alpha-12:test
[INFO]    \- (org.apache.groovy:groovy:jar:5.0.0-alpha-12:test - omitted for duplicate)
[INFO] 
[INFO] ------------------------< org.eolang:eo-parser >------------------------
[INFO] Building eo-parser 0.51.6                                          [2/3]
[INFO]   from eo-parser/pom.xml
[INFO] --------------------------------[ jar ]---------------------------------
[WARNING] The artifact xml-apis:xml-apis:jar:2.0.2 has been relocated to xml-apis:xml-apis:jar:1.0.b2
[INFO] 
[INFO] --- dependency:3.7.1:tree (default-cli) @ eo-parser ---
[INFO] org.eolang:eo-parser:jar:0.51.6
[INFO] +- org.projectlombok:lombok:jar:1.18.36:provided
[INFO] +- commons-io:commons-io:jar:2.18.0:test
[INFO] +- org.cactoos:cactoos:jar:0.56.1:compile
[INFO] +- xml-apis:xml-apis:jar:1.0.b2:compile
[INFO] +- com.yegor256:xsline:jar:0.23.1:compile
[INFO] |  \- (com.jcabi:jcabi-xml:jar:0.33.5:compile - version managed from 0.33.5; omitted for duplicate)
[INFO] +- com.github.volodya-lombrozo:xnav:jar:0.1.8:compile
[INFO] |  +- org.slf4j:slf4j-api:jar:2.0.16:compile
[INFO] |  \- (com.jcabi:jcabi-log:jar:0.24.3:compile - version managed from 0.24.3; omitted for duplicate)
[INFO] +- net.sf.saxon:Saxon-HE:jar:12.5:runtime
[INFO] |  +- org.xmlresolver:xmlresolver:jar:5.2.2:runtime
[INFO] |  |  +- org.apache.httpcomponents.client5:httpclient5:jar:5.1.3:runtime
[INFO] |  |  |  +- (org.apache.httpcomponents.core5:httpcore5:jar:5.1.3:runtime - omitted for duplicate)
[INFO] |  |  |  +- org.apache.httpcomponents.core5:httpcore5-h2:jar:5.1.3:runtime
[INFO] |  |  |  |  \- (org.apache.httpcomponents.core5:httpcore5:jar:5.1.3:runtime - omitted for duplicate)
[INFO] |  |  |  +- (org.slf4j:slf4j-api:jar:1.7.25:runtime - omitted for conflict with 2.0.16)
[INFO] |  |  |  \- commons-codec:commons-codec:jar:1.17.1:runtime (version managed from 1.15)
[INFO] |  |  \- org.apache.httpcomponents.core5:httpcore5:jar:5.1.3:runtime
[INFO] |  \- org.xmlresolver:xmlresolver:jar:data:5.2.2:runtime
[INFO] |     +- (org.apache.httpcomponents.client5:httpclient5:jar:5.1.3:runtime - omitted for duplicate)
[INFO] |     \- (org.apache.httpcomponents.core5:httpcore5:jar:5.1.3:runtime - omitted for duplicate)
[INFO] +- org.antlr:antlr4-runtime:jar:4.13.2:compile
[INFO] +- com.jcabi:jcabi-xml:jar:0.33.5:compile
[INFO] |  +- (com.jcabi:jcabi-log:jar:0.24.3:compile - version managed from 0.24.3; omitted for duplicate)
[INFO] |  \- (org.cactoos:cactoos:jar:0.56.1:compile - version managed from 0.56.1; omitted for duplicate)
[INFO] +- com.jcabi:jcabi-manifests:jar:2.1.0:compile
[INFO] |  \- (com.jcabi:jcabi-log:jar:0.24.3:compile - version managed from 0.22.0; omitted for duplicate)
[INFO] +- com.jcabi:jcabi-log:jar:0.24.3:compile
[INFO] |  \- (org.slf4j:slf4j-api:jar:2.0.16:compile - omitted for duplicate)
[INFO] +- com.jcabi.incubator:xembly:jar:0.32.2:compile
[INFO] +- com.jcabi:jcabi-matchers:jar:1.8.0:test
[INFO] |  +- (org.hamcrest:hamcrest:jar:2.2:test - version managed from 3.0; omitted for duplicate)
[INFO] |  +- (com.jcabi:jcabi-log:jar:0.24.3:test - version managed from 0.24.3; omitted for duplicate)
[INFO] |  \- com.jcabi:jcabi-aspects:jar:0.26.0:test (version managed from 0.26.0)
[INFO] |     +- (com.jcabi:jcabi-log:jar:0.24.3:test - version managed from 0.24.1; omitted for duplicate)
[INFO] |     +- org.aspectj:aspectjrt:jar:1.9.22.1:test (version managed from 1.9.21.1)
[INFO] |     \- javax.validation:validation-api:jar:2.0.1.Final:test (version managed from 2.0.1.Final)
[INFO] +- com.google.code.findbugs:annotations:jar:3.0.1u2:provided
[INFO] |  +- net.jcip:jcip-annotations:jar:1.0:provided
[INFO] |  \- com.google.code.findbugs:jsr305:jar:3.0.2:provided (version managed from 3.0.1)
[INFO] +- org.junit.jupiter:junit-jupiter-api:jar:5.11.4:test
[INFO] |  +- org.opentest4j:opentest4j:jar:1.3.0:test
[INFO] |  +- org.junit.platform:junit-platform-commons:jar:1.11.4:test
[INFO] |  |  \- (org.apiguardian:apiguardian-api:jar:1.1.2:test - omitted for duplicate)
[INFO] |  \- org.apiguardian:apiguardian-api:jar:1.1.2:test
[INFO] +- org.junit.jupiter:junit-jupiter-params:jar:5.11.4:test
[INFO] |  +- (org.junit.jupiter:junit-jupiter-api:jar:5.11.4:test - version managed from 5.11.4; scope managed from compile; omitted for duplicate)
[INFO] |  \- (org.apiguardian:apiguardian-api:jar:1.1.2:test - omitted for duplicate)
[INFO] +- org.junit-pioneer:junit-pioneer:jar:2.3.0:test
[INFO] |  +- (org.junit.jupiter:junit-jupiter-api:jar:5.11.4:test - version managed from 5.11.2; scope managed from runtime; omitted for duplicate)
[INFO] |  +- (org.junit.jupiter:junit-jupiter-params:jar:5.11.4:test - version managed from 5.11.2; scope managed from runtime; omitted for duplicate)
[INFO] |  \- org.junit.platform:junit-platform-launcher:jar:1.11.2:test
[INFO] |     +- (org.junit.platform:junit-platform-engine:jar:1.11.2:test - omitted for conflict with 1.11.4)
[INFO] |     \- (org.apiguardian:apiguardian-api:jar:1.1.2:test - omitted for duplicate)
[INFO] +- org.slf4j:slf4j-reload4j:jar:2.0.16:test
[INFO] |  +- (org.slf4j:slf4j-api:jar:2.0.16:test - omitted for duplicate)
[INFO] |  \- ch.qos.reload4j:reload4j:jar:1.2.22:test
[INFO] +- log4j:log4j:jar:1.2.17:test
[INFO] +- org.apache.commons:commons-text:jar:1.13.0:compile
[INFO] |  \- org.apache.commons:commons-lang3:jar:3.17.0:compile (version managed from 3.17.0)
[INFO] +- org.eolang:jucs:jar:0.2.0:test
[INFO] |  +- (org.cactoos:cactoos:jar:0.56.1:test - version managed from 0.55.0; omitted for duplicate)
[INFO] |  \- (org.junit.jupiter:junit-jupiter-params:jar:5.11.4:test - version managed from 5.9.1; scope managed from compile; omitted for duplicate)
[INFO] +- com.yegor256:jping:jar:0.0.3:test
[INFO] +- com.yegor256:together:jar:0.1.0:test
[INFO] +- org.eolang:xax:jar:0.6.2:test
[INFO] |  +- org.yaml:snakeyaml:jar:2.3:test (version managed from 2.3; scope managed from compile)
[INFO] |  +- (com.jcabi:jcabi-xml:jar:0.33.5:test - version managed from 0.33.3; omitted for duplicate)
[INFO] |  +- (org.cactoos:cactoos:jar:0.56.1:test - version managed from 0.56.1; omitted for duplicate)
[INFO] |  +- (com.yegor256:xsline:jar:0.23.1:test - version managed from 0.22.1; omitted for duplicate)
[INFO] |  \- (net.sf.saxon:Saxon-HE:jar:12.5:runtime - version managed from 12.5; scope managed from runtime; omitted for duplicate)
[INFO] +- com.yegor256:mktmp:jar:0.0.5:test
[INFO] +- com.yegor256:farea:jar:0.14.2:test
[INFO] |  +- com.yegor256:jaxec:jar:0.4.0:test (version managed from 0.4.0)
[INFO] |  |  \- (com.jcabi:jcabi-log:jar:0.24.3:test - version managed from 0.24.2; omitted for duplicate)
[INFO] |  +- (com.jcabi:jcabi-log:jar:0.24.3:test - version managed from 0.24.3; omitted for duplicate)
[INFO] |  +- (com.jcabi:jcabi-xml:jar:0.33.5:test - version managed from 0.30.1; omitted for duplicate)
[INFO] |  \- (com.jcabi.incubator:xembly:jar:0.32.2:test - version managed from 0.31.1; omitted for duplicate)
[INFO] +- net.java.dev.jna:jna:jar:5.16.0:test
[INFO] +- org.openjdk.jmh:jmh-core:jar:1.37:test
[INFO] |  +- net.sf.jopt-simple:jopt-simple:jar:5.0.4:test
[INFO] |  \- org.apache.commons:commons-math3:jar:3.6.1:test (version managed from 3.6.1)
[INFO] +- org.apache.groovy:groovy:jar:5.0.0-alpha-12:test
[INFO] +- org.apache.groovy:groovy-xml:jar:5.0.0-alpha-12:test
[INFO] |  \- (org.apache.groovy:groovy:jar:5.0.0-alpha-12:test - omitted for duplicate)
[INFO] +- org.junit.jupiter:junit-jupiter-engine:jar:5.11.4:test
[INFO] |  +- org.junit.platform:junit-platform-engine:jar:1.11.4:test
[INFO] |  |  +- (org.opentest4j:opentest4j:jar:1.3.0:test - omitted for duplicate)
[INFO] |  |  +- (org.junit.platform:junit-platform-commons:jar:1.11.4:test - omitted for duplicate)
[INFO] |  |  \- (org.apiguardian:apiguardian-api:jar:1.1.2:test - omitted for duplicate)
[INFO] |  +- (org.junit.jupiter:junit-jupiter-api:jar:5.11.4:test - version managed from 5.11.4; scope managed from compile; omitted for duplicate)
[INFO] |  \- (org.apiguardian:apiguardian-api:jar:1.1.2:test - omitted for duplicate)
[INFO] +- org.hamcrest:hamcrest:jar:2.2:test (scope not updated to test)
[INFO] \- org.mockito:mockito-core:jar:5.12.0:test
[INFO]    +- net.bytebuddy:byte-buddy:jar:1.14.15:test
[INFO]    +- net.bytebuddy:byte-buddy-agent:jar:1.14.15:test
[INFO]    \- org.objenesis:objenesis:jar:3.3:test
[INFO] 
[INFO] ---------------------< org.eolang:eo-maven-plugin >---------------------
[INFO] Building eo-maven-plugin 0.51.6                                    [3/3]
[INFO]   from eo-maven-plugin/pom.xml
[INFO] ----------------------------[ maven-plugin ]----------------------------
[WARNING] The artifact xml-apis:xml-apis:jar:2.0.2 has been relocated to xml-apis:xml-apis:jar:1.0.b2
[INFO] 
[INFO] --- dependency:3.7.1:tree (default-cli) @ eo-maven-plugin ---
[INFO] org.eolang:eo-maven-plugin:maven-plugin:0.51.6
[INFO] +- org.eolang:eo-parser:jar:0.51.6:compile
[INFO] |  +- (org.cactoos:cactoos:jar:0.56.1:compile - version managed from 0.56.1; omitted for duplicate)
[INFO] |  +- (xml-apis:xml-apis:jar:1.0.b2:compile - omitted for duplicate)
[INFO] |  +- (com.yegor256:xsline:jar:0.23.1:compile - version managed from 0.23.1; omitted for duplicate)
[INFO] |  +- (com.github.volodya-lombrozo:xnav:jar:0.1.8:compile - version managed from 0.1.8; omitted for duplicate)
[INFO] |  +- (net.sf.saxon:Saxon-HE:jar:12.5:runtime - version managed from 12.5; scope managed from runtime; omitted for duplicate)
[INFO] |  +- (org.antlr:antlr4-runtime:jar:4.13.2:compile - version managed from 4.13.2; omitted for duplicate)
[INFO] |  +- (com.jcabi:jcabi-xml:jar:0.33.5:compile - version managed from 0.33.5; omitted for duplicate)
[INFO] |  +- (com.jcabi:jcabi-manifests:jar:2.1.0:compile - version managed from 2.1.0; omitted for duplicate)
[INFO] |  +- (com.jcabi:jcabi-log:jar:0.24.3:compile - version managed from 0.24.3; omitted for duplicate)
[INFO] |  +- (com.jcabi.incubator:xembly:jar:0.32.2:compile - version managed from 0.32.2; omitted for duplicate)
[INFO] |  \- org.apache.commons:commons-text:jar:1.13.0:compile (version managed from 1.13.0)
[INFO] |     \- (org.apache.commons:commons-lang3:jar:3.17.0:compile - version managed from 3.17.0; omitted for duplicate)
[INFO] +- org.eolang:lints:jar:0.0.38:compile
[INFO] |  +- (com.jcabi:jcabi-xml:jar:0.33.5:compile - version managed from 0.33.5; omitted for duplicate)
[INFO] |  +- io.github.secretx33:path-matching-resource-pattern-resolver:jar:0.1:compile
[INFO] |  +- (org.cactoos:cactoos:jar:0.56.1:compile - version managed from 0.56.1; omitted for duplicate)
[INFO] |  +- (net.sf.saxon:Saxon-HE:jar:12.5:runtime - version managed from 12.5; scope managed from runtime; omitted for duplicate)
[INFO] |  +- (com.jcabi:jcabi-manifests:jar:2.1.0:compile - version managed from 2.1.0; omitted for duplicate)
[INFO] |  +- (com.jcabi:jcabi-log:jar:0.24.3:compile - version managed from 0.24.3; omitted for duplicate)
[INFO] |  +- org.slf4j:slf4j-api:jar:2.0.16:compile
[INFO] |  +- (org.slf4j:slf4j-reload4j:jar:2.0.16:compile - version managed from 2.0.16; omitted for duplicate)
[INFO] |  +- (org.eolang:eo-parser:jar:0.51.1:compile - omitted for conflict with 0.51.6)
[INFO] |  +- (com.github.volodya-lombrozo:xnav:jar:0.1.8:compile - version managed from 0.1.8; omitted for duplicate)
[INFO] |  +- org.apache.opennlp:opennlp-tools:jar:2.1.1:compile
[INFO] |  \- (com.google.code.findbugs:jsr305:jar:3.0.2:compile - version managed from 3.0.2; omitted for duplicate)
[INFO] +- org.glassfish:jakarta.json:jar:1.1.6:compile
[INFO] +- com.yegor256:xsline:jar:0.23.1:compile
[INFO] |  \- (com.jcabi:jcabi-xml:jar:0.33.5:compile - version managed from 0.33.5; omitted for duplicate)
[INFO] +- com.jcabi.incubator:xembly:jar:0.32.2:compile
[INFO] +- org.antlr:antlr4-runtime:jar:4.13.2:runtime (scope not updated to compile)
[INFO] +- org.cactoos:cactoos:jar:0.56.1:compile
[INFO] +- com.jcabi:jcabi-log:jar:0.24.3:compile
[INFO] |  \- (org.slf4j:slf4j-api:jar:2.0.16:compile - omitted for duplicate)
[INFO] +- com.jcabi:jcabi-manifests:jar:2.1.0:compile
[INFO] |  \- (com.jcabi:jcabi-log:jar:0.24.3:compile - version managed from 0.22.0; omitted for duplicate)
[INFO] +- com.jcabi:jcabi-aspects:jar:0.26.0:compile
[INFO] |  +- (com.jcabi:jcabi-log:jar:0.24.3:compile - version managed from 0.24.1; omitted for duplicate)
[INFO] |  +- (org.aspectj:aspectjrt:jar:1.9.22.1:compile - version managed from 1.9.21.1; omitted for duplicate)
[INFO] |  \- javax.validation:validation-api:jar:2.0.1.Final:compile (version managed from 2.0.1.Final)
[INFO] +- org.aspectj:aspectjrt:jar:1.9.22.1:compile
[INFO] +- net.sf.saxon:Saxon-HE:jar:12.5:compile
[INFO] |  +- org.xmlresolver:xmlresolver:jar:5.2.2:compile
[INFO] |  |  +- org.apache.httpcomponents.client5:httpclient5:jar:5.1.3:runtime
[INFO] |  |  |  +- (org.apache.httpcomponents.core5:httpcore5:jar:5.1.3:runtime - omitted for duplicate)
[INFO] |  |  |  +- org.apache.httpcomponents.core5:httpcore5-h2:jar:5.1.3:runtime
[INFO] |  |  |  |  \- (org.apache.httpcomponents.core5:httpcore5:jar:5.1.3:runtime - omitted for duplicate)
[INFO] |  |  |  +- (org.slf4j:slf4j-api:jar:1.7.25:runtime - omitted for conflict with 2.0.16)
[INFO] |  |  |  \- commons-codec:commons-codec:jar:1.17.1:runtime (version managed from 1.15)
[INFO] |  |  \- org.apache.httpcomponents.core5:httpcore5:jar:5.1.3:runtime
[INFO] |  \- org.xmlresolver:xmlresolver:jar:data:5.2.2:compile
[INFO] |     +- (org.apache.httpcomponents.client5:httpclient5:jar:5.1.3:runtime - omitted for duplicate)
[INFO] |     \- (org.apache.httpcomponents.core5:httpcore5:jar:5.1.3:runtime - omitted for duplicate)
[INFO] +- com.jcabi:jcabi-xml:jar:0.33.5:compile
[INFO] |  +- (com.jcabi:jcabi-log:jar:0.24.3:compile - version managed from 0.24.3; omitted for duplicate)
[INFO] |  \- (org.cactoos:cactoos:jar:0.56.1:compile - version managed from 0.56.1; omitted for duplicate)
[INFO] +- org.apache.maven:maven-plugin-api:jar:3.9.9:provided
[INFO] |  +- (org.apache.maven:maven-model:jar:3.9.9:provided - omitted for duplicate)
[INFO] |  +- org.apache.maven:maven-artifact:jar:3.9.9:provided
[INFO] |  |  \- (org.codehaus.plexus:plexus-utils:jar:3.5.1:provided - omitted for conflict with 3.6.0)
[INFO] |  +- org.eclipse.sisu:org.eclipse.sisu.plexus:jar:0.9.0.M3:provided
[INFO] |  |  +- (org.eclipse.sisu:org.eclipse.sisu.inject:jar:0.9.0.M3:provided - omitted for duplicate)
[INFO] |  |  +- (org.codehaus.plexus:plexus-component-annotations:jar:2.1.0:provided - omitted for duplicate)
[INFO] |  |  +- (org.codehaus.plexus:plexus-classworlds:jar:2.6.0:provided - omitted for conflict with 2.8.0)
[INFO] |  |  +- (org.codehaus.plexus:plexus-utils:jar:3.5.1:provided - omitted for conflict with 3.6.0)
[INFO] |  |  \- (org.codehaus.plexus:plexus-xml:jar:3.0.0:provided - omitted for conflict with 4.0.4)
[INFO] |  +- (org.codehaus.plexus:plexus-utils:jar:3.5.1:provided - omitted for conflict with 3.6.0)
[INFO] |  \- org.codehaus.plexus:plexus-classworlds:jar:2.8.0:provided
[INFO] +- org.apache.maven:maven-model:jar:3.9.9:provided (scope not updated to provided)
[INFO] |  \- (org.codehaus.plexus:plexus-utils:jar:3.5.1:provided - omitted for conflict with 3.6.0)
[INFO] +- org.apache.maven:maven-core:jar:3.9.9:provided
[INFO] |  +- (org.apache.maven:maven-model:jar:3.9.9:provided - omitted for duplicate)
[INFO] |  +- org.apache.maven:maven-settings:jar:3.9.9:provided
[INFO] |  |  \- (org.codehaus.plexus:plexus-utils:jar:3.5.1:provided - omitted for conflict with 3.6.0)
[INFO] |  +- org.apache.maven:maven-settings-builder:jar:3.9.9:provided
[INFO] |  |  +- (org.apache.maven:maven-builder-support:jar:3.9.9:provided - omitted for duplicate)
[INFO] |  |  +- (javax.inject:javax.inject:jar:1:provided - omitted for duplicate)
[INFO] |  |  +- (org.codehaus.plexus:plexus-interpolation:jar:1.27:provided - omitted for duplicate)
[INFO] |  |  +- (org.codehaus.plexus:plexus-utils:jar:3.5.1:provided - omitted for conflict with 3.6.0)
[INFO] |  |  +- (org.apache.maven:maven-settings:jar:3.9.9:provided - omitted for duplicate)
[INFO] |  |  \- org.codehaus.plexus:plexus-sec-dispatcher:jar:2.0:provided
[INFO] |  |     +- (org.codehaus.plexus:plexus-utils:jar:3.4.1:provided - omitted for conflict with 3.6.0)
[INFO] |  |     +- org.codehaus.plexus:plexus-cipher:jar:2.0:provided
[INFO] |  |     |  \- (javax.inject:javax.inject:jar:1:provided - omitted for duplicate)
[INFO] |  |     \- (javax.inject:javax.inject:jar:1:provided - omitted for duplicate)
[INFO] |  +- org.apache.maven:maven-builder-support:jar:3.9.9:provided
[INFO] |  +- org.apache.maven:maven-repository-metadata:jar:3.9.9:provided
[INFO] |  |  \- (org.codehaus.plexus:plexus-utils:jar:3.5.1:provided - omitted for conflict with 3.6.0)
[INFO] |  +- (org.apache.maven:maven-artifact:jar:3.9.9:provided - omitted for duplicate)
[INFO] |  +- (org.apache.maven:maven-plugin-api:jar:3.9.9:provided - omitted for duplicate)
[INFO] |  +- org.apache.maven:maven-model-builder:jar:3.9.9:provided
[INFO] |  |  +- (org.codehaus.plexus:plexus-interpolation:jar:1.27:provided - omitted for duplicate)
[INFO] |  |  +- (javax.inject:javax.inject:jar:1:provided - omitted for duplicate)
[INFO] |  |  +- (org.apache.maven:maven-model:jar:3.9.9:provided - omitted for duplicate)
[INFO] |  |  +- (org.apache.maven:maven-artifact:jar:3.9.9:provided - omitted for duplicate)
[INFO] |  |  +- (org.apache.maven:maven-builder-support:jar:3.9.9:provided - omitted for duplicate)
[INFO] |  |  \- (org.eclipse.sisu:org.eclipse.sisu.inject:jar:0.9.0.M3:provided - omitted for duplicate)
[INFO] |  +- org.apache.maven:maven-resolver-provider:jar:3.9.9:provided
[INFO] |  |  +- (org.apache.maven:maven-model:jar:3.9.9:provided - omitted for duplicate)
[INFO] |  |  +- (org.apache.maven:maven-model-builder:jar:3.9.9:provided - omitted for duplicate)
[INFO] |  |  +- (org.apache.maven:maven-repository-metadata:jar:3.9.9:provided - omitted for duplicate)
[INFO] |  |  +- (org.apache.maven.resolver:maven-resolver-api:jar:1.9.22:provided - omitted for duplicate)
[INFO] |  |  +- (org.apache.maven.resolver:maven-resolver-spi:jar:1.9.22:provided - omitted for duplicate)
[INFO] |  |  +- (org.apache.maven.resolver:maven-resolver-util:jar:1.9.22:provided - omitted for duplicate)
[INFO] |  |  +- (org.apache.maven.resolver:maven-resolver-impl:jar:1.9.22:provided - omitted for duplicate)
[INFO] |  |  +- (org.codehaus.plexus:plexus-utils:jar:3.5.1:provided - omitted for conflict with 3.6.0)
[INFO] |  |  \- (javax.inject:javax.inject:jar:1:provided - omitted for duplicate)
[INFO] |  +- org.apache.maven.resolver:maven-resolver-impl:jar:1.9.22:provided
[INFO] |  |  +- (org.apache.maven.resolver:maven-resolver-api:jar:1.9.22:provided - omitted for duplicate)
[INFO] |  |  +- (org.apache.maven.resolver:maven-resolver-spi:jar:1.9.22:provided - omitted for duplicate)
[INFO] |  |  +- org.apache.maven.resolver:maven-resolver-named-locks:jar:1.9.22:provided
[INFO] |  |  |  \- (org.slf4j:slf4j-api:jar:1.7.36:provided - omitted for conflict with 2.0.16)
[INFO] |  |  +- (org.apache.maven.resolver:maven-resolver-util:jar:1.9.22:provided - omitted for duplicate)
[INFO] |  |  \- (org.slf4j:slf4j-api:jar:1.7.36:provided - omitted for conflict with 2.0.16)
[INFO] |  +- org.apache.maven.resolver:maven-resolver-api:jar:1.9.22:provided
[INFO] |  +- org.apache.maven.resolver:maven-resolver-spi:jar:1.9.22:provided
[INFO] |  |  \- (org.apache.maven.resolver:maven-resolver-api:jar:1.9.22:provided - omitted for duplicate)
[INFO] |  +- org.apache.maven.resolver:maven-resolver-util:jar:1.9.22:provided
[INFO] |  |  \- (org.apache.maven.resolver:maven-resolver-api:jar:1.9.22:provided - omitted for duplicate)
[INFO] |  +- org.apache.maven.shared:maven-shared-utils:jar:3.4.2:provided
[INFO] |  |  \- (org.slf4j:slf4j-api:jar:1.7.36:provided - omitted for conflict with 2.0.16)
[INFO] |  +- (org.eclipse.sisu:org.eclipse.sisu.plexus:jar:0.9.0.M3:provided - omitted for duplicate)
[INFO] |  +- org.eclipse.sisu:org.eclipse.sisu.inject:jar:0.9.0.M3:provided
[INFO] |  +- com.google.inject:guice:jar:5.1.0:provided
[INFO] |  |  +- (javax.inject:javax.inject:jar:1:provided - omitted for duplicate)
[INFO] |  |  \- aopalliance:aopalliance:jar:1.0:provided
[INFO] |  +- com.google.guava:guava:jar:33.2.1-jre:provided (version managed from 33.2.1-jre)
[INFO] |  +- com.google.guava:failureaccess:jar:1.0.2:provided
[INFO] |  +- javax.inject:javax.inject:jar:1:provided
[INFO] |  +- (org.codehaus.plexus:plexus-utils:jar:3.5.1:provided - omitted for conflict with 3.6.0)
[INFO] |  +- (org.codehaus.plexus:plexus-classworlds:jar:2.8.0:provided - omitted for duplicate)
[INFO] |  +- org.codehaus.plexus:plexus-interpolation:jar:1.27:provided
[INFO] |  +- org.codehaus.plexus:plexus-component-annotations:jar:2.1.0:provided
[INFO] |  \- (org.slf4j:slf4j-api:jar:1.7.36:provided - omitted for conflict with 2.0.16)
[INFO] +- org.apache.maven.plugin-tools:maven-plugin-annotations:jar:3.15.1:provided
[INFO] +- org.apache.maven.plugin-testing:maven-plugin-testing-harness:jar:3.3.0:test
[INFO] |  +- commons-io:commons-io:jar:2.18.0:test (version managed from 2.2)
[INFO] |  \- org.codehaus.plexus:plexus-archiver:jar:2.2:test
[INFO] |     +- org.codehaus.plexus:plexus-container-default:jar:1.0-alpha-9-stable-1:test
[INFO] |     |  +- junit:junit:jar:3.8.1:test
[INFO] |     |  +- (org.codehaus.plexus:plexus-utils:jar:1.0.4:test - omitted for conflict with 3.6.0)
[INFO] |     |  \- classworlds:classworlds:jar:1.1-alpha-2:test
[INFO] |     +- (org.codehaus.plexus:plexus-utils:jar:3.0.7:test - omitted for conflict with 3.6.0)
[INFO] |     \- org.codehaus.plexus:plexus-io:jar:2.0.4:test
[INFO] |        \- (org.codehaus.plexus:plexus-utils:jar:3.0:test - omitted for conflict with 3.6.0)
[INFO] +- org.apache.maven:maven-compat:jar:3.9.9:test
[INFO] |  +- (org.apache.maven:maven-model:jar:3.9.9:test - omitted for duplicate)
[INFO] |  +- (org.apache.maven:maven-model-builder:jar:3.9.9:test - omitted for duplicate)
[INFO] |  +- (org.apache.maven:maven-settings:jar:3.9.9:test - omitted for duplicate)
[INFO] |  +- (org.apache.maven:maven-settings-builder:jar:3.9.9:test - omitted for duplicate)
[INFO] |  +- (org.apache.maven:maven-artifact:jar:3.9.9:test - omitted for duplicate)
[INFO] |  +- (org.apache.maven:maven-core:jar:3.9.9:test - omitted for duplicate)
[INFO] |  +- (org.apache.maven:maven-resolver-provider:jar:3.9.9:test - omitted for duplicate)
[INFO] |  +- (org.apache.maven:maven-repository-metadata:jar:3.9.9:test - omitted for duplicate)
[INFO] |  +- (org.apache.maven.resolver:maven-resolver-api:jar:1.9.22:test - omitted for duplicate)
[INFO] |  +- (org.apache.maven.resolver:maven-resolver-util:jar:1.9.22:test - omitted for duplicate)
[INFO] |  +- (org.apache.maven.resolver:maven-resolver-impl:jar:1.9.22:test - omitted for duplicate)
[INFO] |  +- (org.codehaus.plexus:plexus-utils:jar:3.5.1:test - omitted for conflict with 3.6.0)
[INFO] |  +- (org.codehaus.plexus:plexus-interpolation:jar:1.27:test - omitted for duplicate)
[INFO] |  +- (org.eclipse.sisu:org.eclipse.sisu.plexus:jar:0.9.0.M3:test - omitted for duplicate)
[INFO] |  +- (org.codehaus.plexus:plexus-component-annotations:jar:2.1.0:test - omitted for duplicate)
[INFO] |  \- org.apache.maven.wagon:wagon-provider-api:jar:3.5.3:test
[INFO] |     \- (org.codehaus.plexus:plexus-utils:jar:3.3.1:test - omitted for conflict with 3.6.0)
[INFO] +- org.twdata.maven:mojo-executor:jar:2.4.1:compile
[INFO] |  \- (org.codehaus.plexus:plexus-utils:jar:3.0.24:compile - omitted for conflict with 3.6.0)
[INFO] +- com.google.code.findbugs:jsr305:jar:3.0.2:compile
[INFO] +- com.google.code.findbugs:annotations:jar:3.0.1u2:provided
[INFO] |  +- net.jcip:jcip-annotations:jar:1.0:provided
[INFO] |  \- (com.google.code.findbugs:jsr305:jar:3.0.2:provided - version managed from 3.0.1; omitted for duplicate)
[INFO] +- com.jcabi:jcabi-matchers:jar:1.8.0:test
[INFO] |  +- (org.hamcrest:hamcrest:jar:2.2:test - version managed from 3.0; omitted for duplicate)
[INFO] |  +- (com.jcabi:jcabi-log:jar:0.24.3:test - version managed from 0.24.3; omitted for duplicate)
[INFO] |  \- (com.jcabi:jcabi-aspects:jar:0.26.0:test - version managed from 0.26.0; omitted for duplicate)
[INFO] +- org.junit.jupiter:junit-jupiter-api:jar:5.11.4:test
[INFO] |  +- org.opentest4j:opentest4j:jar:1.3.0:test
[INFO] |  +- org.junit.platform:junit-platform-commons:jar:1.11.4:test
[INFO] |  |  \- (org.apiguardian:apiguardian-api:jar:1.1.2:test - omitted for duplicate)
[INFO] |  \- org.apiguardian:apiguardian-api:jar:1.1.2:test
[INFO] +- org.junit.jupiter:junit-jupiter-engine:jar:5.11.4:test
[INFO] |  +- org.junit.platform:junit-platform-engine:jar:1.11.4:test
[INFO] |  |  +- (org.opentest4j:opentest4j:jar:1.3.0:test - omitted for duplicate)
[INFO] |  |  +- (org.junit.platform:junit-platform-commons:jar:1.11.4:test - omitted for duplicate)
[INFO] |  |  \- (org.apiguardian:apiguardian-api:jar:1.1.2:test - omitted for duplicate)
[INFO] |  +- (org.junit.jupiter:junit-jupiter-api:jar:5.11.4:test - version managed from 5.11.4; scope managed from compile; omitted for duplicate)
[INFO] |  \- (org.apiguardian:apiguardian-api:jar:1.1.2:test - omitted for duplicate)
[INFO] +- org.junit.jupiter:junit-jupiter-params:jar:5.11.4:test
[INFO] |  +- (org.junit.jupiter:junit-jupiter-api:jar:5.11.4:test - version managed from 5.11.4; scope managed from compile; omitted for duplicate)
[INFO] |  \- (org.apiguardian:apiguardian-api:jar:1.1.2:test - omitted for duplicate)
[INFO] +- org.junit-pioneer:junit-pioneer:jar:2.3.0:test
[INFO] |  +- (org.junit.jupiter:junit-jupiter-api:jar:5.11.4:test - version managed from 5.11.2; scope managed from runtime; omitted for duplicate)
[INFO] |  +- (org.junit.jupiter:junit-jupiter-params:jar:5.11.4:test - version managed from 5.11.2; scope managed from runtime; omitted for duplicate)
[INFO] |  \- org.junit.platform:junit-platform-launcher:jar:1.11.2:test
[INFO] |     +- (org.junit.platform:junit-platform-engine:jar:1.11.2:test - omitted for conflict with 1.11.4)
[INFO] |     \- (org.apiguardian:apiguardian-api:jar:1.1.2:test - omitted for duplicate)
[INFO] +- xml-apis:xml-apis:jar:1.0.b2:compile
[INFO] +- com.yegor256:farea:jar:0.14.2:test
[INFO] |  +- com.yegor256:jaxec:jar:0.4.0:test (version managed from 0.4.0)
[INFO] |  |  \- (com.jcabi:jcabi-log:jar:0.24.3:test - version managed from 0.24.2; omitted for duplicate)
[INFO] |  +- (com.jcabi:jcabi-log:jar:0.24.3:test - version managed from 0.24.3; omitted for duplicate)
[INFO] |  +- (com.jcabi:jcabi-xml:jar:0.33.5:test - version managed from 0.30.1; omitted for duplicate)
[INFO] |  \- (com.jcabi.incubator:xembly:jar:0.32.2:test - version managed from 0.31.1; omitted for duplicate)
[INFO] +- com.yegor256:together:jar:0.1.0:test
[INFO] +- com.yegor256:mktmp:jar:0.0.5:test
[INFO] +- com.github.volodya-lombrozo:xnav:jar:0.1.8:compile
[INFO] |  +- (org.slf4j:slf4j-api:jar:2.0.16:compile - omitted for duplicate)
[INFO] |  \- (com.jcabi:jcabi-log:jar:0.24.3:compile - version managed from 0.24.3; omitted for duplicate)
[INFO] +- com.yegor256:tojos:jar:0.18.5:compile
[INFO] |  \- org.yaml:snakeyaml:jar:2.3:test (version managed from 2.2; scope managed from compile)
[INFO] +- javax.json:javax.json-api:jar:1.1.4:provided
[INFO] +- org.glassfish:javax.json:jar:1.1.4:runtime
[INFO] +- com.opencsv:opencsv:jar:5.10:runtime
[INFO] |  +- (org.apache.commons:commons-lang3:jar:3.17.0:runtime - version managed from 3.17.0; omitted for duplicate)
[INFO] |  +- (org.apache.commons:commons-text:jar:1.13.0:runtime - version managed from 1.13.0; omitted for duplicate)
[INFO] |  +- commons-beanutils:commons-beanutils:jar:1.10.0:runtime
[INFO] |  |  +- commons-logging:commons-logging:jar:1.3.4:runtime
[INFO] |  |  \- commons-collections:commons-collections:jar:3.2.2:runtime
[INFO] |  \- org.apache.commons:commons-collections4:jar:4.4:runtime (version managed from 4.4)
[INFO] +- org.apache.commons:commons-lang3:jar:3.17.0:compile
[INFO] +- org.slf4j:slf4j-reload4j:jar:2.0.16:provided (scope not updated to compile)
[INFO] |  +- (org.slf4j:slf4j-api:jar:2.0.16:provided - omitted for duplicate)
[INFO] |  \- (ch.qos.reload4j:reload4j:jar:1.2.22:provided - omitted for conflict with 1.2.26)
[INFO] +- org.codehaus.plexus:plexus-utils:jar:3.6.0:compile (scope not updated to compile)
[INFO] +- org.codehaus.plexus:plexus-xml:jar:4.0.4:provided (scope not updated to provided)
[INFO] |  \- org.apache.maven:maven-xml-impl:jar:4.0.0-alpha-9:provided
[INFO] |     +- org.apache.maven:maven-api-xml:jar:4.0.0-alpha-9:provided
[INFO] |     |  \- org.apache.maven:maven-api-meta:jar:4.0.0-alpha-9:provided
[INFO] |     \- com.fasterxml.woodstox:woodstox-core:jar:6.5.1:provided
[INFO] |        \- org.codehaus.woodstox:stax2-api:jar:4.2.1:provided
[INFO] +- ch.qos.reload4j:reload4j:jar:1.2.26:runtime
[INFO] +- com.jcabi:jcabi-maven-slf4j:jar:0.12.2:compile
[INFO] |  \- (org.slf4j:slf4j-api:jar:2.0.0-beta1:compile - omitted for conflict with 2.0.16)
[INFO] +- com.yegor256:jhome:jar:0.0.5:test
[INFO] +- org.eolang:jucs:jar:0.2.0:test
[INFO] |  +- (org.cactoos:cactoos:jar:0.56.1:test - version managed from 0.55.0; omitted for duplicate)
[INFO] |  \- (org.junit.jupiter:junit-jupiter-params:jar:5.11.4:test - version managed from 5.9.1; scope managed from compile; omitted for duplicate)
[INFO] +- org.eolang:xax:jar:0.6.2:test
[INFO] |  +- (org.yaml:snakeyaml:jar:2.3:test - version managed from 2.3; scope managed from compile; omitted for duplicate)
[INFO] |  +- (com.jcabi:jcabi-xml:jar:0.33.5:test - version managed from 0.33.3; omitted for duplicate)
[INFO] |  +- (org.cactoos:cactoos:jar:0.56.1:test - version managed from 0.56.1; omitted for duplicate)
[INFO] |  +- (com.yegor256:xsline:jar:0.23.1:test - version managed from 0.22.1; omitted for duplicate)
[INFO] |  \- (net.sf.saxon:Saxon-HE:jar:12.5:runtime - version managed from 12.5; scope managed from runtime; omitted for duplicate)
[INFO] +- com.yegor256:jping:jar:0.0.3:test
[INFO] +- com.tngtech.archunit:archunit:jar:1.4.0:test
[INFO] |  \- (org.slf4j:slf4j-api:jar:2.0.16:test - omitted for duplicate)
[INFO] +- org.openjdk.jmh:jmh-core:jar:1.37:test
[INFO] |  +- net.sf.jopt-simple:jopt-simple:jar:5.0.4:test
[INFO] |  \- org.apache.commons:commons-math3:jar:3.6.1:test (version managed from 3.6.1)
[INFO] +- org.apache.groovy:groovy:jar:5.0.0-alpha-12:test
[INFO] +- org.apache.groovy:groovy-xml:jar:5.0.0-alpha-12:test
[INFO] |  \- (org.apache.groovy:groovy:jar:5.0.0-alpha-12:test - omitted for duplicate)
[INFO] +- org.hamcrest:hamcrest:jar:2.2:test (scope not updated to test)
[INFO] +- org.mockito:mockito-core:jar:5.12.0:test
[INFO] |  +- net.bytebuddy:byte-buddy:jar:1.14.15:test
[INFO] |  +- net.bytebuddy:byte-buddy-agent:jar:1.14.15:test
[INFO] |  \- org.objenesis:objenesis:jar:3.3:test
[INFO] \- log4j:log4j:jar:1.2.17:test
[INFO] ------------------------------------------------------------------------
[INFO] Reactor Summary for eo 0.51.6:
[INFO] 
[INFO] eo ................................................. SUCCESS [  0.440 s]
[INFO] eo-parser .......................................... SUCCESS [  0.136 s]
[INFO] eo-maven-plugin .................................... SUCCESS [  0.172 s]
[INFO] ------------------------------------------------------------------------
[INFO] BUILD SUCCESS
[INFO] ------------------------------------------------------------------------
[INFO] Total time:  1.215 s
[INFO] Finished at: 2025-03-02T15:11:50+08:00
[INFO] ------------------------------------------------------------------------
"""
    res = Restore("~/ray/RQ3_Dataset/clone2/eo", "eo-parser", "",{},[]) 
    ret = res.parse_tree_for_deps(tree, res.path_to_cloned_folder, res.relative_path_to_module, "")
    print(ret)
    