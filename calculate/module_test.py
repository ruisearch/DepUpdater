# testing script
import os
import json
import subprocess
import shutil
import copy
import time
from tqdm import tqdm
from lxml import etree
# set transitive dependency in pom
def add_or_update_transitive_dependency(file_path, group_id, artifact_id, version, classifier):
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(file_path, parser)
    root = tree.getroot()
    ns = {'m': 'http://maven.apache.org/POM/4.0.0'}  # Make sure this matches your pom.xml's namespace   
    
    dependencyManagement = root.find('.//m:dependencyManagement', namespaces=ns)
    if dependencyManagement is None:
        dependencyManagement = etree.SubElement(root, '{http://maven.apache.org/POM/4.0.0}dependencyManagement')
    
    dependencies = dependencyManagement.find('m:dependencies', namespaces=ns)
    if dependencies is None:
        dependencies = etree.SubElement(dependencyManagement, '{http://maven.apache.org/POM/4.0.0}dependencies')
    
    # Check if dependency exists and create/update as necessary
    dependency = None
    for dep in dependencies.findall('m:dependency', namespaces=ns):
        g_id = dep.find('m:groupId', namespaces=ns)
        a_id = dep.find('m:artifactId', namespaces=ns)
        if g_id is not None and a_id is not None and g_id.text == group_id and a_id.text == artifact_id:
            dependency = dep
            break

    if dependency is None:
        dependency = etree.SubElement(dependencies, '{http://maven.apache.org/POM/4.0.0}dependency')
        gid = etree.SubElement(dependency, '{http://maven.apache.org/POM/4.0.0}groupId')
        gid.text = group_id
        aid = etree.SubElement(dependency, '{http://maven.apache.org/POM/4.0.0}artifactId')
        aid.text = artifact_id

    ver = dependency.find('m:version', namespaces=ns)
    if ver is None:
        ver = etree.SubElement(dependency, '{http://maven.apache.org/POM/4.0.0}version')
    ver.text = version

    # add classifier if it exists
    cla = dependency.find('m:classifier', namespaces=ns)
    if classifier != '':
        if cla is None:
            cla = etree.SubElement(dependency, '{http://maven.apache.org/POM/4.0.0}classifier')
        cla.text = classifier
    
    tree.write(file_path, pretty_print=True, xml_declaration=True, encoding='UTF-8')

# set direct dependency in pom
def add_or_update_direct_dependency(file_path, group_id, artifact_id, version, classifier):
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(file_path, parser)
    root = tree.getroot()
    ns = {'m': 'http://maven.apache.org/POM/4.0.0'}  # Make sure this matches your pom.xml's namespace

    dependencies = root.find('.//m:dependencies', namespaces=ns)
    if dependencies is None:
        dependencies = etree.SubElement(root, '{http://maven.apache.org/POM/4.0.0}dependencies')

    # Check if dependency exists and create/update as necessary
    dependency = None
    for dep in dependencies.findall('m:dependency', namespaces=ns):
        g_id = dep.find('m:groupId', namespaces=ns)
        a_id = dep.find('m:artifactId', namespaces=ns)
        if g_id is not None and a_id is not None and g_id.text == group_id and a_id.text == artifact_id:
            dependency = dep
            break

    if dependency is None:
        dependency = etree.SubElement(dependencies, '{http://maven.apache.org/POM/4.0.0}dependency')
        gid = etree.SubElement(dependency, '{http://maven.apache.org/POM/4.0.0}groupId')
        gid.text = group_id
        aid = etree.SubElement(dependency, '{http://maven.apache.org/POM/4.0.0}artifactId')
        aid.text = artifact_id

    ver = dependency.find('m:version', namespaces=ns)
    if ver is None:
        ver = etree.SubElement(dependency, '{http://maven.apache.org/POM/4.0.0}version')
    ver.text = version
    
    # add classifier if it exists
    cla = dependency.find('m:classifier', namespaces=ns)
    if classifier != '':
        if cla is None:
            cla = etree.SubElement(dependency, '{http://maven.apache.org/POM/4.0.0}classifier')
        cla.text = classifier

    tree.write(file_path, pretty_print=True, xml_declaration=True, encoding='UTF-8')
# set one dep to the version calculated; create a new xml to achieve it 
# dep: the dict of the dep which contains all information of a dep
# module_path: path to module_path in cloned folder
# pom_path: path to the pom.xml
# temp_pom_path: path to the tempory pom
def set_one_dep(dep:dict, module_path:str, pom_path:str)->str:
    group_id = dep["GroupId"]
    artifact_id = dep["ArtifactId"]
    new_version = dep["BestVersion"]
    classifier = dep['Classifier']
    # copy the pom.xml to a temp pom to prevent multiple process conflict
    if classifier == '':
        temp_pom_path = os.path.join(module_path, f'_temp_{group_id}_{artifact_id}_{new_version}_.xml')
    else:
        temp_pom_path = os.path.join(module_path, f'_temp_{group_id}_{artifact_id}_{new_version}_{classifier}.xml')
    shutil.copy(pom_path, temp_pom_path)
    # direct dep
    if dep['Depth'] == 1:
        # set <dependencies>
        add_or_update_direct_dependency(temp_pom_path, group_id, artifact_id, new_version ,classifier)
    else :
        # transitive dep, set <dependencyManagement>
        add_or_update_transitive_dependency(temp_pom_path,group_id, artifact_id, new_version, classifier)
    return temp_pom_path
    
# main method to check(one module)
# res_dict: a dict containing all inform of a dep after calculating
# dep_path: path to dep/ folder in data/Jar, meaning all dep of a module
# path_to_cloned_folder: path to the root of cloned project
# module_error_folder: path to the folder containing the errors of the module
# tqdm_log_module_folder: path to tqdm_log/{module_name}/ containing files denoting the progress of each process
# flag: if this dep is true positive, flag is True, False otherwise
# lock is deprecated
def check_version_module(lock, res_dict:dict, dep_path:str, path_to_cloned_folder:str, module_error_folder: str, tqdm_log_module_folder:str)->bool:
    flag = True
    # path to inform.json in module data folder
    inform_json_path = os.path.join(dep_path, '../inform.json')
    # get relative_path_to_module_folder
    with open(inform_json_path, 'r') as f:
        inform = json.load(f)
    relative_path_to_module_folder = inform['Module']
    # get the pom location
    module_path = os.path.join(path_to_cloned_folder, relative_path_to_module_folder)
    pom_path = os.path.join(module_path, "pom.xml")
    # test: check the actual tags of the Version ~ the version after the BestVersion
    # get the idxs of the version after current version(first) and the newest version(last)
    AllVersion = res_dict["AllVersion"]
    first = 0
    last = len(AllVersion)-1
    best = 0 # idx of BestVersion
    for i in range(0, len(AllVersion)):
        if AllVersion[i]["version"] == res_dict["Version"]:
            if i == len(AllVersion)-1:
                # current version is the newest version, no need to check
                print(f"{res_dict['GroupId']}:{res_dict['ArtifactId']}:{res_dict['Version']} is the newest version, skip")
                return
            first = i+1
        if AllVersion[i]["version"] == res_dict["BestVersion"]:
            best = i
        
    # recompilation from first version to last version to find the fn and fp
    # fp: BestVersion is not the actual newest version which is compatible(record the recompliation of the BestVersion)
    # fn: the actual newest version which is compatible is not BestVersion(record the recompliation of newest version which is compatible)
    # key: find the actual newest version which is compatible(this version may not exist from first version to last version)
    # note: last may be the actual last version in AllVersion
    real_positive_version_idx = first-1 # current version is compatible
    positive_result = None
    real_positive_result = None
    # find actual newest version which is compatible(real_positive_version)
    # first ~ last
     
    # file to contain tqdm log
    # for fp, record two recompilation results: positive_result + subsequent_positive_result(the version after positive version);
    # for fn, record two recompilation results: real_positive_result + subsequent_real_positive_result(the version after real positive version);
    dep_tqdm_log_file = os.path.join(tqdm_log_module_folder, f"{res_dict['GroupId']}_{res_dict['ArtifactId']}_tqdm_log.txt")
    with open(dep_tqdm_log_file, 'a') as f:
        with tqdm(total=last-first+1, desc=f'Validate version of {res_dict["GroupId"]}:{res_dict["ArtifactId"]}  ', file=f) as pbar:
            subsequent_positive_result = None
            positive_result = None
            subsequent_real_positive_result = None
            real_positive_result = None
            former_flag = True
            for i in range(first, last+1):
                temp_dict = copy.deepcopy(res_dict)
                temp_dict["BestVersion"]  = AllVersion[i]["version"]
                if res_dict['Classifier'] == '':
                    print(f"{res_dict['GroupId']}:{res_dict['ArtifactId']}:{res_dict['Version']} ---> {temp_dict['BestVersion']}")
                else:
                    print(f"{res_dict['GroupId']}:{res_dict['ArtifactId']}:{res_dict['Version']}:{res_dict['Classifier']} ---> {temp_dict['BestVersion']}")
                new_pom_path = set_one_dep(temp_dict, module_path, pom_path)
                # recompile to test
                flag, result = recompile(path_to_cloned_folder, new_pom_path)
                if i == best:
                    # get the recompilation result of the Bestverion, cause it may be the record of fp
                    positive_result = result
                if i-1 == best:
                    # get the recompilation result of the version after the positive version
                    subsequent_positive_result = result
                if flag:
                    real_positive_version_idx = i
                    # get the recompilation result of the real positive version, cause it may be the record of fn
                    real_positive_result = result
                if flag is False and former_flag is True:
                    # get the recompilation result of the version after the real positive version
                    # the last subsequent_real_positive_result records the result
                    subsequent_real_positive_result = result
                former_flag = flag
                pbar.update(1)
            if real_positive_version_idx == last:
                # real positive is the last version, means that 
                subsequent_real_positive_result = None
    if res_dict['Classifier'] == '':
        print(f"Actually best version of {res_dict['GroupId']}:{res_dict['ArtifactId']} is {AllVersion[real_positive_version_idx]['version']}")
    else:
        print(f"Actually best version of {res_dict['GroupId']}:{res_dict['ArtifactId']}:{res_dict['Classifier']} is {AllVersion[real_positive_version_idx]['version']}")
    # record fp and fn
    if real_positive_version_idx != best:
        flag = False
        # fp: BestVersion is not the actual newest version which is compatible(record the recompliation of the BestVersion)
        dep_list = []
        dep_list.append(res_dict)
        print(f" find a fp: {res_dict['GroupId']}:{res_dict['ArtifactId']}:{res_dict['Version']} ---> {res_dict['BestVersion']}")
        # module_data_folder: path to a module data folder in data/Jar,like abstract-factory_
        module_data_folder = os.path.join(dep_path, '..')
        store_error(lock, module_data_folder, dep_list, positive_result, subsequent_positive_result, os.path.join(module_error_folder, 'fp'))
        # fn: the actual newest version which is compatible is not BestVersion(record the recompliation of newest version which is compatible)
        # if real_positive_version_idx != last or real_positive_version_idx == last and last == len(AllVersion)-1:
        temp_dict = copy.deepcopy(res_dict)
        temp_dict['BestVersion'] = AllVersion[real_positive_version_idx]['version']
        dep_list = []
        dep_list.append(temp_dict)
        print(f" find a fn: {res_dict['GroupId']}:{res_dict['ArtifactId']}:{res_dict['Version']} ---> {temp_dict['BestVersion']}")
        store_error(lock, module_data_folder, dep_list, real_positive_result, subsequent_real_positive_result, os.path.join(module_error_folder, 'fn'))
    else:
        flag = True
    return flag

# recompile to test
# path_to_cloned_folder: path to root dir
# new_pom_path: absolute path to the new pom file
def recompile(path_to_cloned_folder: str, new_pom_path: str):
    # command = f"cd {path_to_cloned_folder} && mvn clean && mvn compile -Dmaven.test.skip=true -Dcheckstyle.skip=true -pl {relative_path_to_module_folder} -am"
    # command = f"cd {path_to_cloned_folder} && mvn -Dmaven.test.skip=true -Dcheckstyle.skip=true -f {new_pom_path} clean compile"
    # note: skip maven-enforcer-plugin
    command = f"cd {path_to_cloned_folder} && mvn -Dmaven.test.skip=true -Dcheckstyle.skip=true -Denforcer.skip=true -f {new_pom_path} clean compile"
    try:
        result = subprocess.run(command, shell=True, text=True, capture_output=True)
        # check if the command was successful
        if result.returncode != 0:
            # recompiling failure
            # remove the temporary pom.xml
            if new_pom_path.endswith('pom.xml') is False:
                os.remove(new_pom_path)
            return False, result
        else:
            if new_pom_path.endswith('pom.xml') is False:
                os.remove(new_pom_path)
            return True, result
    except subprocess.SubprocessError as e:
        print(f"An error occurred while executing the command: {e}")
        # in this situration, don't remove temporary xml file
        return False, result

# add an error in a subfolder of module_error_folder(fp or fn), named folder(already exist)
# result: return value of subprocessor.run
# should store: relative module path/module name(in module_data_folder/inform.json)+dep ga + dep original verion\
# + dep new version + dep depth + recompilation log
def store_error(lock, module_data_folder:str, dep_list:list, result, subsuquent_result, folder:str):
    # with lock:
    # get the name of the txt;all name is a number
    # if os.listdir(folder):
    #     # not empty means already has same situation before
    #     max_num = 0
    #     for item in os.listdir(folder):
    #         if max_num < int(item):
    #             max_num = int(item)
    #         txt_name = str(max_num+1)
    # else :
    #     # empty, so txt_name is '1'
    #     txt_name = '1'
    pid = os.getpid()
    txt_name = f'{int(time.time())}_{pid}.txt'
    
    path_to_inform = os.path.join(module_data_folder, 'inform.json')
    # folder to contain related jar
    jar_folder = os.path.join(folder, '../jar/')
    with open(path_to_inform, 'r') as f:
        inform = json.load(f)
        module_name = inform['Module']
    with open(os.path.join(folder, txt_name), 'a') as log_txt:
        # records module name
        log_txt.write(f'module name: {module_name}\n')
        log_txt.write(f'\n* * * * * * * *\n')
        for dep in dep_list:
            log_txt.write(f'groudId: {dep["GroupId"]}\n')
            log_txt.write(f'artifactId: {dep["ArtifactId"]}\n')
            log_txt.write(f'old version: {dep["Version"]}\n')
            log_txt.write(f'new version: {dep["BestVersion"]}\n')
            log_txt.write(f'classifier: {dep["Classifier"]}\n')
            # record breaking reason if dep['Breaking_Reason'] is not empty
            # empty means the best version Tool detected is the newest version
            if not dep:
                log_txt.write(f'breaking reason by Tool:\n  breaking version:{dep["Breaking_Reason"]["breaking_version"]}\n breaking reason:{dep["Breaking_Reason"]["breaking_reason"]}\n')
            log_txt.write(f'depth: {dep["Depth"]}\n')
            log_txt.write(f'reachable api of old version:\n')
            for reachable_api in dep['ReachableAPIs']:
                log_txt.write(f'    {reachable_api}\n')
            new_dep_path = os.path.join(module_data_folder, 'dep/new_dep')
            files = os.listdir(new_dep_path)
            # current version revapi log
            if dep['Version'] != dep['BestVersion']:
                log_txt.write(f'/ / / / / / / / /\nrevapi log of former version -- {dep["BestVersion"]}:\n')
                former_revapi_log_paths = []
                if dep['Classifier'] == '':
                    for file in files:
                        if file.startswith(f'{dep["GroupId"]}-{dep["ArtifactId"]}-{dep["BestVersion"]}#'):
                            former_revapi_log_paths.append(os.path.join(new_dep_path, file))
                    # former_revapi_log_path = os.path.join(module_data_folder, f'dep/new_dep/{dep["GroupId"]}-{dep["ArtifactId"]}-{dep["BestVersion"]}.jar.ret.txt')
                    former_jar_path = os.path.join(module_data_folder, f'dep/new_dep/{dep["GroupId"]}-{dep["ArtifactId"]}-{dep["BestVersion"]}.jar')
                else:
                    for file in files:
                        if file.startswith(f'{dep["GroupId"]}-{dep["ArtifactId"]}-{dep["BestVersion"]}-{dep["Classifier"]}#'):
                           former_revapi_log_paths.append(os.path.join(new_dep_path, file)) 
                    # former_revapi_log_path = os.path.join(module_data_folder, f'dep/new_dep/{dep["GroupId"]}-{dep["ArtifactId"]}-{dep["BestVersion"]}-{dep["Classifier"]}.jar.ret.txt')
                    former_jar_path = os.path.join(module_data_folder, f'dep/new_dep/{dep["GroupId"]}-{dep["ArtifactId"]}-{dep["BestVersion"]}-{dep["Classifier"]}.jar')
                for former_revapi_log_path in former_revapi_log_paths:
                    with open(former_revapi_log_path, 'r') as revapi_log:
                        log_txt.write(f'{revapi_log.read()}\n')
                        log_txt.write(f'<< << << << << << << << <<\n')
                shutil.copy(former_jar_path, jar_folder)
            # subsequent version(breaking version) revapi log
            idx = 0
            for i in range(len(dep['AllVersion'])):
                if dep['AllVersion'][i]['version'] == dep['BestVersion']:
                    idx = i
                    break
            if idx != len(dep['AllVersion'])-1:
                subsequent_idx = idx+1
                subsequent_version = dep['AllVersion'][subsequent_idx]['version']
                sub_revapi_log_paths = []
                if dep['Classifier'] == '':
                    for file in files:
                        if file.startswith(f'{dep["GroupId"]}-{dep["ArtifactId"]}-{subsequent_version}#'):
                            sub_revapi_log_paths.append(os.path.join(new_dep_path, file))
                    # sub_revapi_log_path = os.path.join(module_data_folder, f'dep/new_dep/{dep["GroupId"]}-{dep["ArtifactId"]}-{subsequent_version}.jar.ret.txt')
                    sub_jar_path = os.path.join(module_data_folder, f'dep/new_dep/{dep["GroupId"]}-{dep["ArtifactId"]}-{subsequent_version}.jar')
                else:
                    for file in files:
                        if file.startswith(f'{dep["GroupId"]}-{dep["ArtifactId"]}-{subsequent_version}-{dep["Classifier"]}#'):
                            sub_revapi_log_paths.append(os.path.join(new_dep_path, file))
                    # sub_revapi_log_path = os.path.join(module_data_folder, f'dep/new_dep/{dep["GroupId"]}-{dep["ArtifactId"]}-{subsequent_version}-{dep["Classifier"]}.jar.ret.txt')
                    sub_jar_path = os.path.join(module_data_folder, f'dep/new_dep/{dep["GroupId"]}-{dep["ArtifactId"]}-{subsequent_version}-{dep["Classifier"]}.jar')
                log_txt.write(f'/ / / / / / / / /\nrevapi log of the subsequent version -- {subsequent_version}:\n')
                for sub_revapi_log_path in sub_revapi_log_paths:
                    with open(sub_revapi_log_path, 'r') as revapi_log:
                        log_txt.write(f'{revapi_log.read()}\n')
                        log_txt.write(f'<< << << << << << << << <<\n')
                shutil.copy(sub_jar_path, jar_folder)
            log_txt.write(f'\n* * * * * * * *\n')
        print(f">>>>>> compilation log for former version")
        if result is not None:
            log_txt.write(f">>>>>>\ncompilation log of {dep['BestVersion']}:\n{result.stdout}\n")
        print(f">>>>>> compilation log for later version")
        if subsuquent_result is not None:
            log_txt.write(f">>>>>>\nsubsequent compilation log of {subsequent_version}:\n{subsuquent_result.stdout}\n")
        log_txt.write(f'\n* * * * * * * *\n') 

# back to original pom
def reset(original_tree, pom_path):
    original_tree.write(pom_path, pretty_print=True, xml_declaration=True, encoding='UTF-8')