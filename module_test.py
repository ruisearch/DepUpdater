# testing script
import os
import sys
import json
import subprocess
import shutil
from lxml import etree

# folder to store false cases(already exists)
False_case_path = os.path.join(os.getcwd(), 'false_cases/')
def create_new_folder(folder:str):
    # Check if folder already exists
    if os.path.exists(folder):
        # Remove the existing folder
        shutil.rmtree(folder)
    # Create the new folder
    os.makedirs(folder)
# recompile to test
def recompile(module_path:str):
    command = f"cd {module_path} && mvn clean && mvn compile -DskipTests"
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
def store_error(module_data_folder:str, dep_list:list, result, folder:str):
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
            log_txt.write(f'\n* * * * * * * *\n')
        log_txt.write(f"log:\n{result.stdout}")
   
## expand the path to absolute path
def expand_resolve_abspath(path):
    expanded_path = os.path.expanduser(path)
    resolved_path = os.path.normpath(expanded_path)
    absolute_path = os.path.abspath(resolved_path)
    return absolute_path
# main method to check(one module)
# module_data_folder: path to a module data folder in data/Jar,like abstract-factory_
# path_to_cloned_folder: path to the root of cloned project
# module_error_folder: path to the folder containing the errors of the module
def check_version_module(module_data_folder:str, path_to_cloned_folder:str, module_error_folder:str):
    # path to match.json in module data folder
    match_json_path = os.path.join(module_data_folder, 'dep/match.json')
    # get the content of match.json
    with open(match_json_path, 'r') as f:
        deps = json.load(f)
    # path to inform.json in module data folder
    inform_json_path = os.path.join(module_data_folder, 'inform.json')
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
    # first, test each dep in turn
    print("\n search fn : \n")
    for dep in deps:
        print(f"{dep['GroupId']}:{dep['ArtifactId']}:{dep['Version']} ---> {dep['BestVersion']}")
        set_one_dep(dep, pom_path)
        # recompile to test
        flag, result = recompile(module_path)
        if flag == False:
            # recompilation error, store the log, it's a fn, should be added into module_error_folder/fn
            dep_list = []
            dep_list.append(dep)
            store_error(module_data_folder, dep_list, result, os.path.join(module_error_folder, 'fn'))
        # back to original pom
        reset(original_tree, pom_path)
    # second, all dep in best versions
    print("set all dep to best version \n")
    for dep in deps:
        set_one_dep(dep, pom_path)
    # recompile to test
    flag, result = recompile(module_path)
    if flag == False:
        # recompilation error, store the log, it's a fn, should be added into module_error_folder/fn
        store_error(module_data_folder, deps, result, os.path.join(module_error_folder, 'fn'))
    # back to original pom
    reset(original_tree, pom_path)
    # third, each dep update to the version following best vesion, if recompiling successfully, fp
    print("\n search fp : \n")
    for dep in deps:
        # get the idx of best version in order to find the following version
        AllVersion = dep["AllVersion"]
        idx = 0
        for i in range(0, len(AllVersion)):
            if AllVersion[i]["version"] == dep["BestVersion"]:
                idx = i
                break
        if idx == len(AllVersion)-1:
            # best version is newest
            continue
        calculated_version = dep["BestVersion"]
        dep["BestVersion"] = AllVersion[idx+1]["version"]
        print(f"{dep['GroupId']}:{dep['ArtifactId']}:{calculated_version} ---> {dep['BestVersion']}")
        # recompile to test
        flag, result = recompile(module_path)
        if flag:
            # next version is compatible, fp
            dep_list = []
            dep_list.append(dep)
            store_error(module_data_folder, dep_list, result, os.path.join(module_error_folder, 'fp'))
        # back to original pom
        reset(original_tree, pom_path)
        
# set one dep to the version calculated
# dep: the dict of the dep which is pared from match.json
# pom_path: path to the pom
def set_one_dep(dep:dict, pom_path:str):
    group_id = dep["GroupId"]
    artifact_id = dep["ArtifactId"]
    new_version = dep["BestVersion"]
    # direct dep
    if dep['Depth'] == 1:
        # set <dependencies>
        add_or_update_direst_dependency(pom_path, group_id, artifact_id, new_version)
    else :
        # transitive dep, set <dependencyManagement>
        add_or_update_transitive_dependency(pom_path, group_id, artifact_id, new_version)

def add_or_update_direst_dependency(file_path, group_id, artifact_id, version):
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

def add_or_update_transitive_dependency(file_path, group_id, artifact_id, version):
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(file_path, parser)
    root = tree.getroot()
    ns = {'m': 'http://maven.apache.org/POM/4.0.0'}  # Make sure this matches your pom.xml's namespace   
    
    dependencyManagement = root.find('.//m:dependencyManagement', namespaces=ns)
    if dependencyManagement is None:
        dependencyManagement = etree.SubElement(root, '{http://maven.apache.org/POM/4.0.0}dependencyManagement')
    
    dependencies = dependencyManagement.find('m:dependencies', namespace=ns)
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
# back to original pom
def reset(original_tree, pom_path):
    original_tree.write(pom_path, pretty_print=True, xml_declaration=True, encoding='UTF-8')

# exeucte MainProcess.py
path_to_cloned_folder = expand_resolve_abspath(sys.argv[1])
relative_path_to_module = sys.argv[2]
command = f"python MainProcess.py {path_to_cloned_folder} {relative_path_to_module}"
print("\n*** launch Tool ***\n")
os.system(command)
print("\n*** done ***\n")
print("**** test ****\n")
# project_error_folder represents a project. the folder won't be deleted by this script, can only be created
# if it is outdated, please remove project_error_folder firstly
project_name = path_to_cloned_folder.replace('/','_')
project_error_folder = os.path.join(False_case_path, project_name)
if os.path.isdir(project_error_folder) is False:
    os.makedirs(project_error_folder)
# analysis data from data/Jar
pwd = os.getcwd()
path_to_Jar_folder = os.path.join(pwd,'data/Jar')
items = os.listdir(path_to_Jar_folder)
for item in items:
    item_path = os.path.join(path_to_Jar_folder, item)
    # a module folder
    if os.path.isdir(item_path):
        # test a module
        # the false case will be stored in the following folder
        module_error_folder = os.path.join(project_error_folder, item)
        with open(os.path.join(item_path, 'inform.json')) as f:
            inform = json.load(f)
        module_name = inform["Module"]
        print(f"** test module : {module_name} **")
        create_new_folder(module_error_folder)
        create_new_folder(os.path.join(module_error_folder, 'fp'))
        create_new_folder(os.path.join(module_error_folder, 'fn'))
        check_version_module(item_path, path_to_cloned_folder, module_error_folder)
        print(f"** module : {module_name}  test done **")
print("**** test done !!!****")      
