## calculate best version and then calcute lag(after testing)
import os
import json
import concurrent.futures
import multiprocessing
import shutil
import copy
from lxml import etree
from tqdm import tqdm
from calculate.constants import JAR_FOLDER, TQDM_LOG_PATH
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
    false_folder_lock = manager.Lock() # deprecated
    json_lock = manager.Lock()
    # create tqdm_log/ containing the progress of each process denoting a dep
    create_new_folder(TQDM_LOG_PATH)
    
    # handle the folder in data/Jar representing  the module
    Jar_contents = os.listdir(JAR_FOLDER)
    for item in Jar_contents:
        item_path = os.path.join(JAR_FOLDER, item)
        ## item is a subfolder in Jar folder, representing a module
        if os.path.isdir(item_path):
            # test a module after calculating 
            # the false cases will be stored in the following folder
            module_error_folder = os.path.join(project_error_folder, item)
            # existing module_error_folder is outdate, so delete it and create a new one
            create_new_folder(module_error_folder)
            create_new_folder(os.path.join(module_error_folder, 'fp'))
            create_new_folder(os.path.join(module_error_folder, 'fn'))
            create_new_folder(os.path.join(module_error_folder, 'jar'))
            # travel the match.json and pass one dep for Dep
            json_path = os.path.join(item_path, f"match.json")
            dep_path = os.path.join(item_path, f"dep/")
            
            with open(json_path, 'r') as f:
                dict_list = json.load(f)
                
            # create dep/new_dep/
            new_dep_path = os.path.join(dep_path, 'new_dep/')
             # Check if the folder already exists
            if os.path.exists(new_dep_path) is False:
                # Create the new folder
                os.makedirs(new_dep_path)
            
            # create tqdm_log/{module_name}/
            tqdm_log_module_folder = os.path.join(TQDM_LOG_PATH, f'{item}')
            create_new_folder(tqdm_log_module_folder)
            
            num_workers = os.cpu_count()
            with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
                # initializing the progress bar
                pbar = tqdm(total=len(dict_list), desc=f"Dep in {item}")
                # submit tasks
                futures = [executor.submit(cal_test_a_dep, false_folder_lock, json_lock, one_dict, dep_path, path_to_cloned_folder, module_error_folder, tqdm_log_module_folder) for one_dict in dict_list]
                
                result_deps = []
                error_dep_count = 0
                dep_count = 0
                # for future in futures:
                #     result_dep, flag = future.result()
                #     result_deps.append(result_dep)
                #     if flag is False:
                #         error_dep_count = error_dep_count + 1
                #     dep_count = dep_count + 1
                
                for future in concurrent.futures.as_completed(futures):
                    result_dep, flag = future.result()
                    # add 1 in progress bar, meaning a dep is handled
                    pbar.update(1)
                    result_deps.append(result_dep)
                    if flag is False:
                        error_dep_count = error_dep_count + 1
                    dep_count = dep_count + 1
                pbar.close()    
            
            # copy match.json, Uber/call_graph.json, client/client_api.txt into the module_error_folder
            shutil.copy(json_path, module_error_folder)
            client_folder = os.path.join(item_path, 'client')
            for file in os.listdir(client_folder):
                if file.endswith('api.txt'):
                    api_file_path = os.path.join(client_folder, file)
                    shutil.copy(api_file_path, module_error_folder)
                    break
            Uber_folder = os.path.join(item_path, 'Uber')
            for file in os.listdir(Uber_folder):
                if file.endswith('json'):
                    cg_json_path = os.path.join(Uber_folder, file)
                    shutil.copy(cg_json_path, module_error_folder)
                    break
                     
            # # write the result_deps into match.json    
            # with open(json_path, 'w') as f:
            #     # json.dump(dict_list, f, indent=4)
            #     json.dump(result_deps, f, indent=4)
            # write the weight of error_dep in dep
            error_dep_count_txt_path = os.path.join(module_error_folder, 'error_dep_count.txt')
            with open(error_dep_count_txt_path, 'w') as f:
                f.write(f'total dep: {dep_count}\n')
                f.write(f'error dep: {error_dep_count}\n')
                if dep_count != 0:
                    f.write(f'weight: {error_dep_count / dep_count}\n')
                else:
                    f.write("this module has no dep")
            
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
            absolute_module_path = os.path.join(path_to_cloned_folder, relative_path_to_module_folder)
            flag, result = recompile(path_to_cloned_folder, os.path.join(absolute_module_path, 'pom.xml'))
            if flag == False:
                # recompilation error, store the log, it's a fp, should be added into module_error_folder/fn
                print(" find a fp")
                store_error(false_folder_lock, item_path, result_deps, result, None, os.path.join(module_error_folder, 'fp'))
                with open(error_dep_count_txt_path, 'a') as f:
                    f.write('note: setting all dep to best version causes compilation error!\n')
            # back to original pom
            reset(original_tree, pom_path)
            
# main method of a subprocess
# false_folder_lock: lock to guarantee process mutual exclusion when writing fp or fn to false_cases/'(deprecated)
# json_lock: lock to write to match.json
# one_dict: a dict containing the information of a dep after matching
# dep_path: path to data/Jar/{module/dep/ folder(a parameter of Dep constractor; get inform.json to get module relative path)
# path_to_cloned_folder: path to the root of cloned project
# module_error_folder: path to module folder in false_cases 
# tqdm_log_module_folder: path to tqdm_log/{module_name}/ containing files denoting the progress of each process
# res_dict: the resulting dict containing all versions as well as best version
# flag: if this dep is true positive, flag is True, False otherwise
def cal_test_a_dep(false_folder_lock, json_lock, one_dict:dict, dep_path:str, path_to_cloned_folder:str, module_error_folder: str, tqdm_log_module_folder:str):
    dep = Dep(one_dict, dep_path)
    res_dict = copy.deepcopy(one_dict)
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
    write_a_dep(json_lock, os.path.join(dep_path, '../match.json'), res_dict)
    # get the newest compatible versoin
    print(f"-- start calculating  best version of {one_dict['GroupId']}:{one_dict['ArtifactId']} in {module_name} -- ")
    bestversion, breaking_reason = dep.get_best_version(tqdm_log_module_folder)
    # res_dict.update({'BestVersion':dep.get_best_version(tqdm_log_module_folder)})
    res_dict.update({'BestVersion': bestversion})
    res_dict.update({'Breaking_Reason': breaking_reason})
    print(f"-- best version of {one_dict['GroupId']}:{one_dict['ArtifactId']} is {res_dict['BestVersion']} -- ")
    write_a_dep(json_lock, os.path.join(dep_path, '../match.json'), res_dict)
    print(f"-- start validating the best version of {one_dict['GroupId']}:{one_dict['ArtifactId']} in {module_name} --")
    flag = check_version_module(false_folder_lock, res_dict, dep_path, path_to_cloned_folder, module_error_folder, tqdm_log_module_folder)
    print(f"-- validation to the best version of {one_dict['GroupId']}:{one_dict['ArtifactId']} in {module_name}  done --")
    return res_dict,flag

# write the dep into match.json after calculating its BestVersion
# json_lock: lock to write to match.json
# path_to_match_json: path to match.json
# res_dict: dep which got its BestVersion recently
def write_a_dep(json_lock, path_to_match_json:str, res_dict:dict):
    with json_lock:
        with open(path_to_match_json, 'r') as f_json:
            deps = json.load(f_json)
            # find the dep
            for i in range(len(deps)):
                if deps[i]['JarFileName'] == res_dict['JarFileName']:
                    deps[i] = res_dict
                    break
        with open(path_to_match_json, 'w') as f_json:
            # write back
            json.dump(deps, f_json, indent=4)
                  
# set one dep to the version calculated
# dep: the dict of the dep which is pared from match.json
# pom_path: path to the pom.xml rather than temporary xml
def change_dep_in_pom(dep:dict, pom_path:str):
    group_id = dep["GroupId"]
    artifact_id = dep["ArtifactId"]
    new_version = dep["BestVersion"]
    classifier = dep["Classifier"]
    # direct dep
    if dep['Depth'] == 1:
        # set <dependencies>
        add_or_update_direct_dependency(pom_path, group_id, artifact_id, new_version, classifier)
    else :
        # transitive dep, set <dependencyManagement>
        add_or_update_transitive_dependency(pom_path, group_id, artifact_id, new_version, classifier)
## calculate lag
def calculate_lag():
    print("cal")