## exectute the mvn command like "mvn package"
# path_to_folder : the path where pom.xml locates
import os
import shutil
import subprocess
from constants import TREE_DIR

# create a folder
def create_folder(folder_path:str):
    # Check if the folder already exists
    if os.path.exists(folder_path):
        return
    # Create the new folder
    os.makedirs(folder_path)
    
def mvn_package(path_to_folder:str, relative_path_to_module:str):
    """execute \"mvn package\""""
    # firstly, execute mvn package in module folder
    if relative_path_to_module == '.':
        command = f"cd {path_to_folder} && mvn -Dmaven.test.skip=true -Dcheckstyle.skip=true clean package"
    else :
        command = f"cd {os.path.join(path_to_folder, relative_path_to_module)} && mvn -Dmaven.test.skip=true -Dcheckstyle.skip=true clean package"
    print("mvn clean and mvn package...")
    exit_status = os.system(command)
    if exit_status != 0:
        # mvn package is unexecutable in module folder, so execute it in root with the help of -pl -am
        if relative_path_to_module == '.':
            command = f"cd {path_to_folder} && mvn -Dmaven.test.skip=true -Dcheckstyle.skip=true clean package"
        else :
            command = f"cd {path_to_folder} && mvn -Dmaven.test.skip=true -Dcheckstyle.skip=true -pl {relative_path_to_module} -am clean package "
    exit_status = os.system(command)
    return exit_status

# # execute "mvn dependency:tree"
# def mvn_dependency_tree(path_to_folder:str, relative_path_to_module:str):
#     # MainProcess_pwd = os.getcwd()
#     # log_path = os.path.join(MainProcess_pwd, "data/dependency_tree.txt")
#     # create ./DATA
#     create_folder(DATA)
#     command = f"cd {path_to_folder} && mvn dependency:tree -pl {relative_path_to_module} -am -fae"
#     print("generating dependency tree...")
#     result = subprocess.run(command, shell=True, text=True, capture_output=True)
#     with open(DEPENDENCY_TREE_FILE, 'w') as f:
#         f.write(f'{result.stdout}')
#     # os.system(command)
#     print("dependency tree is generated in ./data/dependency_tree.txt successfully")
    
def mvn_verbose_dependency_tree(path_to_folder:str, relative_path_to_module:str):
    """execute mvn dependency:tree -Dverbose"""
    command = f"cd {path_to_folder} && mvn dependency:tree -pl {relative_path_to_module} -am -Dverbose -fae"
    print("generating dependency tree...")
    result = subprocess.run(command, shell=True, text=True, capture_output=True)
    repo_name = os.path.basename(path_to_folder)
    tree_folder = os.path.join(TREE_DIR, f'{repo_name}/{relative_path_to_module}')
    create_folder(tree_folder)
    tree_file = os.path.join(tree_folder, 'verbose_tree.txt')
    with open(tree_file, 'w', encoding='utf-8') as f:
        f.write(f'{result.stdout}')
    # os.system(command)
    print("dependency tree is generated successfully")
    return tree_file
    