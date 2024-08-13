## restore tree to graph
import os
import shutil
import re
import concurrent.futures
import json
import time
import requests
from database.sqlite import Sqlite
from ..constants import TREE_DIR, JAR_DIR, RET_DIR
from database.sqlite import Sqlite
from database.constants import SQLITE_PATH

class Restore:
    def __init__(self, path_to_cloned_folder:str, relative_path_to_module:str,\
        tree_path:str):
        """
        Args :
            path_to_cloned_folder : path to cloned folder
            relative_path_to_module : relative path from project root
            tree_path : path to tree file
        """
        self.path_to_cloned_folder = path_to_cloned_folder
        self.relative_path_to_module = relative_path_to_module
        self.tree_path = tree_path
        self.client_groupId = None
        self.client_artifactId = None
        self.client_version = None
        self.create_folder(TREE_DIR)
        self.create_folder(JAR_DIR)
    
    def create_folder(self, folder_path:str):
        """create a folder"""
        # Check if the folder already exists
        if os.path.exists(folder_path):
            return
        # Create an empty folder
        os.makedirs(folder_path)
        
    def restore(self)->None:
        """main method in this file,restore"""
        # create TREE folder
        self.create_folder(TREE_DIR)
        # parse
        with open(self.tree_path, 'r', encoding='utf-8') as tree:
            dependency_tree = tree.read()
        # parse tree
        all_deps = self.parse_tree_for_deps(dependency_tree, self.path_to_cloned_folder, self.relative_path_to_module)
        # filter the deps into valid_deps and omitted_deps
        valid_deps, omitted_deps = self.filter_dep(all_deps)
        # parse the dep in valid_deps and omitted_deps to get jar and match.json
        self.parse_for_jar_and_json(valid_deps, omitted_deps)

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

    def get_dep_jar(self, dep_folder:str, group_id:str, artifact_id:str, version:str, classifier:str)->bool:
        """get dep jar using GAV from maven central repository
        
        Args:
            dep_folder : path to data/Jar/{module-name}/dep folder
            
        Returns:
            True means downloading success while False means downloading fail
        """
        # debug
        # print(f'dep {group_id}:{artifact_id}:{version}')
        
        def handle_error_get(jar_url,  retries=5, backoff_factor=0.3):
        # This inner function attempts to get the content from the jar_url with retries
            for attempt in range(retries):
                try:
                    response = requests.get(jar_url, timeout=10)  # Set timeout to prevent hanging
                    response.raise_for_status()  # Will raise an HTTPError for bad responses
                    return response
                except requests.RequestException as e:
                    print(f"Attempt {attempt + 1} failed for {artifact_id}-{version}.jar: {str(e)}")
                    time.sleep(backoff_factor * (2 ** attempt))  # Exponential backoff
                    if attempt == retries - 1:
                        raise  # Re-raise the last exception if all retries fail
        
        
        jar_url = f"https://repo1.maven.org/maven2/{group_id.replace('.', '/')}/{artifact_id}/{version}/{artifact_id}-{version}.jar"
        
        # Call the function with retry logic
        try:
            file_name = os.path.join(dep_folder, f"{artifact_id}-{version}.jar")
            # prevent download repeatly
            if os.path.exists(file_name):
                return True
            response = handle_error_get(jar_url)
            # Proceed if the download was successful
            if response and response.status_code == 200:
                with open(file_name, "wb") as jar_file:
                    jar_file.write(response.content)
                if classifier == '':
                    print(f"{group_id}-{artifact_id}-{version}.jar downloaded successfully.")
                    return True
                else :
                    print(f"{group_id}-{artifact_id}-{version}-{classifier}.jar downloaded successfully.")
                    return True
        except Exception as e:
                print(f"Failed to download {artifact_id}-{version}.jar from central repository; Reason: {str(e)}")
                return False

    def parse_tree_for_deps(self, dependency_tree:str, path_to_cloned_folder:str, relative_path_to_module:str):
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
                # copy client jar
                target = os.path.join(path_to_cloned_folder, f"{block.group(1)}target")
                # normal name follows this format: artifactId-version.jar
                client_jar = f"{self.client_artifactId}-{self.client_version}.jar"
                path_to_client_jar_in_repo = os.path.join(target, client_jar)
                path_to_client_jar_storage = self.query_to_get_jar_location(self.client_groupId,\
                    self.client_artifactId, self.client_version)
                try:
                    shutil.copy(path_to_client_jar_in_repo, path_to_client_jar_storage)
                except FileNotFoundError as e:
                    # the jar name is not as expect
                    print(e)
                    print("name of client jar doesn't follow the form : artifactId-version.jar!")
                    exit()
                # client jar has been stored in data/jar/
                
                # parse tree to get all deps
                deps = self.parse_all_dep(block.group(6))
                return deps

    def query_to_get_jar_location(self, groupId, artifactId, version):
        """query artifacts table to find the absolute path to jar\n
        and create folder if not exist"""
        db = Sqlite(SQLITE_PATH)
        db.connect()
        condition = [('groupId','=',groupId),'AND',('artifactId','=',artifactId),'AND',('version','=',version)]
        relative_path = db.query_data('artifacts', 'relative_path',condition)
        if not relative_path:
            # not in artifacts yet, so insert the record
            path_to_record = f'{groupId}/{artifactId}/{version}/{artifactId}-{version}.jar'
            db.insert_data('artifacts', {'groupId':groupId, 'artifactId':artifactId, 'version':version, \
                'relative_path': path_to_record})
            relative_path = [path_to_record]
        db.close()
        jar_path = os.path.join(JAR_DIR, relative_path[0])
        dir_path = os.path.dirname(jar_path)
        self.create_folder(dir_path)
        return jar_path

    # return a list containing all deps as well as the dependent and depth
    # the list contains valid deps as well as omitted deps denoted by dict{dep, Depth, Dependents}
    def parse_all_dep(self,tree:str):
        dep_pattern = r"^\[INFO\] (.*?)- (.+?)$"
        dep_matches = re.finditer(dep_pattern, tree, re.MULTILINE)
        # group(1): lag
        # group(2): dep

        deps = []
        for dep_match in dep_matches:
            is_test = ":test" in dep_match.group(2)
            is_provided = ":provided" in dep_match.group(2)
            # exclude the dependency for test or provided
            if is_test is False and is_provided is False:
                dep = {}
                # {'dep': the record in tree list 'org.junit-pioneer:junit-pioneer:jar:1.9.1:compile'}
                dep.update({'dep':dep_match.group(2)})
                # get depth from the length of substring between "[INFO] " and "-"
                depth = (int)((len(dep_match.group(1))+2) / 3)
                # depth == 1 means direct while depth > 1 means transitive
                dep.update({'Depth':depth})
                deps.append(dep)

        # get dependent(parent actually)
        for idx, one_dep in enumerate(deps):
            dependent_depth = one_dep['Depth'] - 1
            for i in range(idx, -1, -1):
                if depth == 0:
                    break
                if deps[i]['Depth'] == depth:
                    # note: "Dependents" above are dependents like "org.mockito:mockito-core:jar:4.11.0:compile"
                    # and Dependents are always valid deps
                    # so, I change the record into the dict in order to relate the dependent with the dep when clearing the local module
                    # dict is {'GroupId', 'ArtifactId', 'Classifier'}
                    # we don't need 'Version' as the version will be updated afterwards

                    dependent_dict = self.record_to_dict(deps[i]['dep'])
                    dependent_dict.pop('Version')
                    Dependents.append(dependent_dict)
                    depth = depth - 1
            one_dep.update({"Dependents":Dependents})
        return deps

    # dep key:{dep, Depth, Dependents}
    def parse_for_jar_and_json(self, valid_deps:list, omitted_deps:list, module_folder:str):
        """parse the dep in valid_deps and omitted_deps to get jar and match.json
        
        Args:
            module_folder : path to data/Jar/{module_name}
        """
        # change the valid_deps
        self.change_valid_deps(valid_deps)
        # change the omitted_deps
        self.change_omitted_deps(omitted_deps)
        # path to Jar/{module}/dep
        path_to_dep = os.path.join(module_folder, "dep")
        self.create_folder(path_to_dep)
        # clearing the local modules which couldn't be downloaded from maven central repository
        self.clear_local_module(valid_deps, omitted_deps, path_to_dep)
        # get dep jar and update the list of dicts which will be displayed in json
        # jarname ----> gav
        mappings = []
        # traverse the valid_deps using processPool
        num_workers = os.cpu_count()
        with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
            futures = []
            for valid_dep in valid_deps:
                futures.append(executor.submit(self.process_a_valid_dep, valid_dep, omitted_deps))
        for future in futures:
            mappings.append(future.result())

        # sort deps by their depths so that the sequential traversal is BFS
        mappings.sort(key=lambda dep:dep['Depth'])

        # create json
        json_path = os.path.join(module_folder, 'match.json')
        with open(json_path, 'w', encoding='utf-8') as json_file:
            json.dump(mappings, json_file, indent=4)

    def clear_local_module(self,valid_deps:list, omitted_deps:list, path_to_dep:str) -> None:
        """clear local module which couldn't be downloaded from maven central \
            repository(usually local module) and their dependencies as well

        Args: 
            path_to_dep : path to Jar/{module}/dep
            valid_deps : {GroupId, ArtifactId, Classifier, Version, Type, Depth, Dependents}\
                (from change_valid_deps)
        """
        valid_flag_list = [True for _ in valid_deps] # False means the element should be deleted
        omitted_flag_list = [True for _ in omitted_deps]
        for i, valid_dep in enumerate(valid_deps):
            if valid_flag_list[i] is True:
                flag = self.get_dep_jar(path_to_dep, valid_dep['GroupId'], valid_dep['ArtifactId'], valid_dep['Version'], valid_dep['Classifier'])
                if flag is False:
                    # a local module
                    valid_flag_list[i] = False
                    # mark valid dep of the local module
                    self.mark_dep_of_local_module(valid_dep, valid_deps, valid_flag_list)
                    # mark omitted dep of local module
                    self.mark_dep_of_local_module(valid_dep, omitted_deps, omitted_flag_list)
        self.remove_dep_of_local_module(valid_deps, valid_flag_list)
        self.remove_dep_of_local_module(omitted_deps, omitted_flag_list)

    def mark_dep_of_local_module(self, local_module:dict, dep_list:list, flag_list:list)->None:
        """mark the dependency(valid or omitted) of local module from tree
        
        Args:
            local_module : a dict presents a local module (from clear_local_module)
            dep_list : valid list or omitted list (from clear_local_module)
            flag_list : mark the elements in dep_list that should be deleted (from clear_local_module)
        """
        for i, dep in enumerate(dep_list):
            for dependent in dep['Dependents']:
                if dependent['GroupId'] == local_module['GroupId'] and \
                    dependent['ArtifactId'] == local_module['ArtifactId']:
                    # the dep is a dependency of the local_module
                    flag_list[i] = False
                    break

    def remove_dep_of_local_module(self, dep_list:list, flag_list:list)->None:
        """remove dep of local from dep_list from flags in flag_list
        
        Args:
            dep_list : valid list or omitted list (from clear_local_module)
            flag_list : mark the elements in dep_list that should be deleted (from clear_local_module)
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
                --> related{Version, Dependents}
        
        Returns:
            the computed valid_dep which will be displayed in match.json\n
            {GroupId, ArtifactId, Classifier, Version, Type, Depth, Dependents, JarFileName, Omitted}
        """
        JarFileName = self.dict_to_JarFileName(valid_dep)
        valid_dep.update({"JarFileName": JarFileName})
        
        Omitted = []
        # find the related omitted_deps with the valid_dep and restore the omitted edges of the tree
        for omitted_dep in omitted_deps:
            related = {}
            if omitted_dep['GroupId'] == valid_dep['GroupId'] and omitted_dep['ArtifactId'] == valid_dep['ArtifactId'] \
                and omitted_dep['Classifier'] == valid_dep['Classifier']:
                # omitted_dep is the omitted dep of valid_dep
                Version = omitted_dep['Version']
                Dependents = []
                for dependent in omitted_dep['Dependents']:
                    Dependents.append(dependent)
                related.update({'Version':Version})
                related.update({'Dependents':Dependents})
                Omitted.append(related)
                # add the omitted dependency edges
                self.add_omitted_edges_of_a_dep(valid_dep['Dependents'], related['Dependents'])
        # record the omitted deps of the valid dep
        valid_dep.update({"Omitted":Omitted})
        return valid_dep

    def add_omitted_edges_of_a_dep(self, existing_dependents:list, omitted_dependents:list)->None:
        """add the omitted_dependents to existing_dependents"""
        for omitted_depentent in omitted_dependents:
            # prevent add edges repeatly
            if omitted_depentent not in existing_dependents:
                existing_dependents.append(omitted_depentent)
                
    def record_to_dict(self, record:str):
        """transform a record(valid) into tree to dep{GroupId, ArtifactId, Classifier, Version}"""
        pattern = r"(.+?):(.+?):jar(.*):(.+?):.+?\b"
        match = re.search(pattern, record)
        return {'GroupId':match.group(1), 'ArtifactId':match.group(2), 'Classifier':match.group(3), 'Version':match.group(4)}

    def dict_to_JarFileName(self, dep:dict):
        """transform dep{GroupId, ArtifactId, Version} into JarFileName"""
        return f'{dep["ArtifactId"]}-{dep["Version"]}.jar'

    def change_valid_deps(self, valid_deps:list):
        """change the valid_deps \n
        dep key:{dep, Depth, Dependents} --> dep key:{GroupId, ArtifactId, Classifier, Version, Type, Depth, Dependents}
        
        Args:
            valid_deps : from parse_all_dep
        """
        gav_pattern = r"(.+?):(.+?):jar(.*):(.+?):(.+?)\b"
        for i, valid_dep in enumerate(valid_deps):
            dep = {}
            match = re.search(gav_pattern, valid_dep['dep'])
            dep.update({'GroupId':match.group(1)})
            dep.update({'ArtifactId':match.group(2)})
            dep.update({'Classifier':match.group(3).replace(":","")})
            dep.update({'Version':match.group(4)})
            dep.update({'Type':match.group(5)})
            dep.update({'Depth':valid_dep['Depth']})
            dep.update({'Dependents':valid_dep['Dependents']})
            # test
            # print(dep)
            valid_deps[i] = dep


    def change_omitted_deps(self, omitted_deps:list):
        """change the omitted_deps \n
            dep key:{dep, Depth, Dependents} --> dep key:{GroupId, ArtifactId, Classifier, Version, Type, Depth, Dependents}
            
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
        for i, omitted_dep in enumerate(omitted_deps):
            dep = {}
            match = re.search(gav_pattern_1, omitted_dep['dep'])
            if match is not None:
                # duplicate and covered by pom
                dep.update({'GroupId':match.group(1)})
                dep.update({'ArtifactId':match.group(2)})
                dep.update({'Classifier':match.group(3).replace(":","")})
                dep.update({'Version':match.group(6)})
                dep.update({'Type':match.group(4)})
                dep.update({'Depth':omitted_deps[i]['Depth']})
                dep.update({'Dependents':omitted_deps[i]['Dependents']})
                omitted_deps[i] = dep
                continue
            match = re.search(gav_pattern_2, omitted_dep['dep'])
            if match is not None:
                # duplicate but not covered by pom
                dep.update({'GroupId':match.group(1)})
                dep.update({'ArtifactId':match.group(2)})
                dep.update({'Classifier':match.group(3).replace(":","")})
                dep.update({'Version':match.group(4)})
                dep.update({'Type':match.group(5)})
                dep.update({'Depth':omitted_deps[i]['Depth']})
                dep.update({'Dependents':omitted_deps[i]['Dependents']})
                omitted_deps[i] = dep
                continue
            match = re.search(gav_pattern_3, omitted_dep['dep'])
            if match is not None:
                # conflict
                dep.update({'GroupId':match.group(1)})
                dep.update({'ArtifactId':match.group(2)})
                dep.update({'Classifier':match.group(3).replace(":","")})
                dep.update({'Version':match.group(4)})
                dep.update({'Type':match.group(5)})
                dep.update({'Depth':omitted_deps[i]['Depth']})
                dep.update({'Dependents':omitted_deps[i]['Dependents']})
                omitted_deps[i] = dep
                continue
# test
if __name__ == "__main__":
    # # test remove_dep_of_local_module
    # test_list = [1, 2, 3, 4, 5]
    # test_flag_list = [True, False, True, False, True]
    # ex = Restore(None, None, None)
    # ex.remove_dep_of_local_module(test_list, test_flag_list)
    # print(test_list)

    # test