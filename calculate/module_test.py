# testing script
import os
import json
import subprocess
import shutil
from lxml import etree
# set transitive dependency in pom
def add_or_update_transitive_dependency(file_path, group_id, artifact_id, version):
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

    tree.write(file_path, pretty_print=True, xml_declaration=True, encoding='UTF-8')

# set direct dependency in pom
def add_or_update_direct_dependency(file_path, group_id, artifact_id, version):
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
    # copy the pom.xml to a temp pom to prevent multiple process conflict
    temp_pom_path = os.path.join(module_path, f'_temp_{group_id}_{artifact_id}_{new_version}_pom.xml')
    shutil.copy(pom_path, temp_pom_path)
    # direct dep
    if dep['Depth'] == 1:
        # set <dependencies>
        add_or_update_direct_dependency(temp_pom_path, group_id, artifact_id, new_version)
    else :
        # transitive dep, set <dependencyManagement>
        add_or_update_transitive_dependency(temp_pom_path,group_id, artifact_id, new_version)
    return temp_pom_path
    
# main method to check(one module)
# res_dict: a dict containing all inform of a dep after calculating
# dep_path: path to dep/ folder in data/Jar, meaning all dep of a module
# path_to_cloned_folder: path to the root of cloned project
# module_error_folder: path to the folder containing the errors of the module
def check_version_module(lock, res_dict:dict, dep_path:str, path_to_cloned_folder:str, module_error_folder: str):
    # path to inform.json in module data folder
    inform_json_path = os.path.join(dep_path, '../inform.json')
    # get relative_path_to_module_folder
    with open(inform_json_path, 'r') as f:
        inform = json.load(f)
    relative_path_to_module_folder = inform['Module']
    # get the pom location
    module_path = os.path.join(path_to_cloned_folder, relative_path_to_module_folder)
    pom_path = os.path.join(module_path, "pom.xml")
    # first, check whether best version is compatible
    print(f"-- start checking {res_dict['GroupId']}:{res_dict['ArtifactId']}:{res_dict['Version']} ---> {res_dict['BestVersion']}")
    if res_dict['BestVersion'] == res_dict['Version']:
        print(f" BestVersion of {res_dict['GroupId']}:{res_dict['ArtifactId']} is same as original version, skip")
    else:
        # create a new xml setting the dep to best version
        new_pom_path = set_one_dep(res_dict, module_path, pom_path)
        # recompile to test
        flag, result = recompile(path_to_cloned_folder, new_pom_path)
        if flag == False:
            # recompilation error, store the log, it's a fn, should be added into module_error_folder/fn
            dep_list = []
            dep_list.append(res_dict)
            print(f" find a fn: {res_dict['GroupId']}:{res_dict['ArtifactId']}:{res_dict['Version']} ---> {res_dict['BestVersion']}")
            # module_data_folder: path to a module data folder in data/Jar,like abstract-factory_
            module_data_folder = os.path.join(dep_path, '..')
            store_error(lock, module_data_folder, dep_list, result, os.path.join(module_error_folder, 'fn'))
    # second, check whether best version is the newest
    # get the idx of best version in order to find the following version
    AllVersion = res_dict["AllVersion"]
    idx = 0
    for i in range(0, len(AllVersion)):
        if AllVersion[i]["version"] == res_dict["BestVersion"]:
            idx = i
            break
    # len(AllVersion) == 0 means that the dep can not be  dwonloaded from Maven central repository
    if len(AllVersion) == 0 or idx == len(AllVersion)-1:
            # best version is newest
            print(f" Bestversion of {res_dict['GroupId']}:{res_dict['ArtifactId']} is the newest version, skip")
    else :
        temp_dict = res_dict
        temp_dict["BestVersion"]  = AllVersion[idx+1]["version"]
        print(f"{res_dict['GroupId']}:{res_dict['ArtifactId']}:{res_dict['Version']} ---> {temp_dict['BestVersion']}")
        new_pom_path = set_one_dep(temp_dict, module_path, pom_path)
        # recompile to test
        flag, result = recompile(path_to_cloned_folder, new_pom_path)
        if flag:
            # next version is compatible, fp
            dep_list = []
            dep_list.append(temp_dict)
            print(f" find a fp: {res_dict['GroupId']}:{res_dict['ArtifactId']}:{res_dict['Version']} ---> {temp_dict['BestVersion']}")
            # module_data_folder: path to a module data folder in data/Jar,like abstract-factory_
            module_data_folder = os.path.join(dep_path, '..')
            store_error(lock, module_data_folder, dep_list, result, os.path.join(module_error_folder, 'fp'))

# recompile to test
# path_to_cloned_folder: path to root dir
# new_pom_path: path to the new pom file
def recompile(path_to_cloned_folder: str, new_pom_path: str):
    # command = f"cd {path_to_cloned_folder} && mvn clean && mvn compile -Dmaven.test.skip=true -Dcheckstyle.skip=true -pl {relative_path_to_module_folder} -am"
    command = f"cd {path_to_cloned_folder} && mvn -Dmaven.test.skip=true -Dcheckstyle.skip=true -f {new_pom_path} clean compile"
    try:
        result = subprocess.run(command, shell=True, text=True, capture_output=True)
        # check if the command was successful
        if result.returncode != 0:
            # Command failed, means a false negative
            return False, result
        else:
            return True, result
    except subprocess.SubprocessError as e:
        print(f"An error occurred while executing the command: {e}")
        return False, result

# add an error in a subfolder of module_error_folder(fp or fn), named folder(already exist)
# result: return value of subprocessor.run
# should store: relative module path/module name(in module_data_folder/inform.json)+dep ga + dep original verion\
# + dep new version + dep depth + recompilation log
# note: if there are multiply dep data, means all dep are set to the version that tool outputs
# use lock to achieve process mutually exclusive
def store_error(lock, module_data_folder:str, dep_list:list, result, folder:str):
    with lock:
        # get the name of the txt;all name is a number
        if os.listdir(folder):
            # not empty means already has same situation before
            max_num = 0
            for item in os.listdir(folder):
                if max_num < int(item):
                    max_num = int(item)
                txt_name = str(max_num+1)
        else :
            # empty, so txt_name is '1'
            txt_name = '1'
        path_to_inform = os.path.join(module_data_folder, 'inform.json')
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
                log_txt.write(f'depth: {dep["Depth"]}\n')
                log_txt.write(f'reachable api of old version:\n')
                for reachable_api in dep['ReachableAPIs']:
                    log_txt.write(f'    {reachable_api}\n')
                log_txt.write(f'/ / / / / / / / /\nrevapi log of new version:\n')
                revapi_log_path = os.path.join(module_data_folder, f'dep/new_dep/{dep["ArtifactId"]}-{dep["BestVersion"]}.jar.ret.txt')
                with open(revapi_log_path, 'r') as revapi_log:
                    log_txt.write(f'{revapi_log.read()}')
                log_txt.write(f'\n* * * * * * * *\n')
            log_txt.write(f"log:\n{result.stdout}")
            log_txt.write(f'\n* * * * * * * *\n')

# back to original pom
def reset(original_tree, pom_path):
    original_tree.write(pom_path, pretty_print=True, xml_declaration=True, encoding='UTF-8')