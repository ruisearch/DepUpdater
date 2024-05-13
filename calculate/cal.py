## calculate best version and then calcute lag(after testing)
import os
import json
import concurrent.futures
import multiprocessing
import shutil
from lxml import etree
from calculate.constants import JAR_FOLDER
from calculate.Dep import Dep
from calculate.module_test import check_version_module, recompile, store_error, reset, add_or_update_direct_dependency,add_or_update_transitive_dependency

def create_new_folder(folder:str):
    # Check if folder already exists
    if os.path.exists(folder):
        # Remove the existing folder
        shutil.rmtree(folder)
    # Create the new folder
    os.makedirs(folder)
## calculate best version then testing for all modules in data/Jar
# path_to_cloned_folder: path to the root dir of cloned project
# project_error_folder: path to folder containing false_cases of the project
def select_best_version(path_to_cloned_folder:str, project_error_folder:str):
    ## create a lock so that the store_error will be process mutual excluison
    manager = multiprocessing.Manager()
    lock = manager.Lock()
    # handle the folders in data/Jar represent the modules
    Jar_contents = os.listdir(JAR_FOLDER)
    for item in Jar_contents:
        item_path = os.path.join(JAR_FOLDER, item)
        ## item is a subfolder in Jar folder, representing a module
        if os.path.isdir(item_path):
            # test a module after calculating 
            # the false cases will be stored in the following folder
            module_error_folder = os.path.join(project_error_folder, item)
            create_new_folder(module_error_folder)
            create_new_folder(os.path.join(module_error_folder, 'fp'))
            create_new_folder(os.path.join(module_error_folder, 'fn'))
            # travel the match.json and pass one dep for Dep
            json_path = os.path.join(item_path, f"dep/match.json")
            dep_path = os.path.join(item_path, f"dep/")
            with open(json_path, 'r') as f:
                dict_list = json.load(f)
            # for one_dict in dict_list:
            num_workers = os.cpu_count()
            with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
                futures = [executor.submit(cal_test_a_dep, lock, one_dict, dep_path, path_to_cloned_folder, module_error_folder) for one_dict in dict_list]
            result_deps = [future.result() for future in futures]
            
            # write the result_deps into match.json    
            with open(json_path, 'w') as f:
                # json.dump(dict_list, f, indent=4)
                json.dump(result_deps, f, indent=4)
            
            ## set all dep to best version then validate whether it is compatible
            inform_json_path = os.path.join(item_path, 'inform.json')
            # get relative_path_to_module_folder
            with open(inform_json_path, 'r') as f:
                inform = json.load(f)
            relative_path_to_module_folder = inform['Module']
            # get the pom location
            module_path = os.path.join(path_to_cloned_folder, relative_path_to_module_folder)
            pom_path = os.path.join(module_path, "pom.xml")
            # get the original tree in convenience of resetting 
            parser = etree.XMLParser(remove_blank_text=True)
            original_tree = etree.parse(pom_path, parser)
            # set all dep to best versoins
            print("set all dep to best version \n")
            for dep in result_deps:
                change_dep_in_pom(dep, pom_path)
            # recompile to test
            flag, result = recompile(path_to_cloned_folder, relative_path_to_module_folder)
            if flag == False:
                # recompilation error, store the log, it's a fp, should be added into module_error_folder/fn
                print(" find a fn")
                store_error(lock, item_path, result_deps, result, os.path.join(module_error_folder, 'fp'))
            # back to original pom
            reset(original_tree, pom_path)
            
    ## handle a specific module
    ## test : just deal with one module folder in data/Jar
    # item_path = os.path.join(JAR_FOLDER, '148')
    # item_path = os.path.join(JAR_FOLDER, '3')
    # item_path = os.path.join(JAR_FOLDER, '169')
    # item_path = os.path.join(JAR_FOLDER, '165')
    # item_path = os.path.join(JAR_FOLDER, '2')
    # travel the match.json and pass one dep for Dep
    # else:
    #     items = os.listdir(JAR_FOLDER)
    #     for item in items:
    #         if os.path.isdir(os.path.join(JAR_FOLDER, item)):
    #             item_path = os.path.join(JAR_FOLDER, item)
    #             # test a module
    #             # the false case will be stored in the following folder
    #             module_error_folder = os.path.join(project_error_folder, item)
    #             module_name = relative_path_to_module
    #             create_new_folder(module_error_folder)
    #             create_new_folder(os.path.join(module_error_folder, 'fp'))
    #             create_new_folder(os.path.join(module_error_folder, 'fn'))
    #             break
    #     json_path = os.path.join(item_path, f"dep/match.json")
    #     dep_path = os.path.join(item_path, f"dep/")
    #     with open(json_path, 'r') as f:
    #         dict_list = json.load(f)
    #     # for one_dict in dict_list:
    #     num_workers = os.cpu_count()
    #     with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
    #         futures = [executor.submit(cal_test_a_dep, lock, one_dict, dep_path, path_to_cloned_folder, module_error_folder) for one_dict in dict_list]
    #     result = [future.result() for future in futures]
    #     with open(json_path, 'w') as f:
    #         # json.dump(dict_list, f, indent=4)
    #         json.dump(result, f, indent=4)
# main method of a subprocess
# lock: lock to guarantee process mutual exclusion
# one_dict: a dict containing the information of a dep after matching
# dep_path: path to dep/ folder(a parameter of Dep constractor; get inform.json to get module relative path)
# path_to_cloned_folder: path to the root of cloned project
# module_error_folder: path to module folder in false_cases 
# res_dict: the resulting dict containing all versions as well as best version
def cal_test_a_dep(lock, one_dict:dict, dep_path:str, path_to_cloned_folder:str, module_error_folder: str):
    dep = Dep(one_dict, dep_path)
    res_dict = one_dict
    # get the module name
    inform_json_path = os.path.join(dep_path, '../inform.json')
    with open(inform_json_path, 'r') as f:
        inform = json.load(f)
    module_name = inform['Module']
    if module_name == '':
        module_name = '/'
    # get all version of each dep
    print(f"-- start sorting versions of {one_dict['GroupId']}:{one_dict['ArtifactId']} -- ")
    res_dict.update({'AllVersion':dep.fetch_versions_sorted()})
    print(f"-- get all versions of {one_dict['GroupId']}:{one_dict['ArtifactId']} -- ")
    # get the newest compatible versoin
    print(f"-- start calculating  best version of {one_dict['GroupId']}:{one_dict['ArtifactId']} in {module_name} -- ")
    res_dict.update({'BestVersion':dep.get_best_version()})
    print(f"-- best version of {one_dict['GroupId']}:{one_dict['ArtifactId']} is {res_dict['BestVersion']} -- ")
    print(f"-- start validating the best version of {one_dict['GroupId']}:{one_dict['ArtifactId']} in {module_name} --")
    check_version_module(lock, res_dict, dep_path, path_to_cloned_folder, module_error_folder)
    print(f"-- validation to the best version of {one_dict['GroupId']}:{one_dict['ArtifactId']} in {module_name}  done --")
    return res_dict
# set one dep to the version calculated
# dep: the dict of the dep which is pared from match.json
# pom_path: path to the pom.xml rather than temporary xml
def change_dep_in_pom(dep:dict, pom_path:str):
    group_id = dep["GroupId"]
    artifact_id = dep["ArtifactId"]
    new_version = dep["BestVersion"]
    # direct dep
    if dep['Depth'] == 1:
        # set <dependencies>
        add_or_update_direct_dependency(pom_path, group_id, artifact_id, new_version)
    else :
        # transitive dep, set <dependencyManagement>
        add_or_update_transitive_dependency(pom_path, group_id, artifact_id, new_version)
## calculate lag
def calculate_lag():
    print("cal")