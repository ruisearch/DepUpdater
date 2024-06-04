## exectute the mvn command like "mvn package"
# path_to_folder : the path where pom.xml locates
import os
import shutil
import subprocess
from preprocess.constants import DEPENDENCY_TREE_FILE, DATA

# create a folder
def create_folder(folder_path:str):
    # Check if the folder already exists
    if os.path.exists(folder_path):
        # Remove the existing folder
        shutil.rmtree(folder_path)
    # Create the new folder
    os.makedirs(folder_path)
    
# execute "mvn package"
def mvn_package(path_to_folder:str, relative_path_to_module:str):
    # if relative_path_to_module != '.':
    #     path_to_folder = os.path.join(path_to_folder, relative_path_to_module)
    if relative_path_to_module == '.':
        command = f"cd {path_to_folder} && mvn -Dmaven.test.skip=true -Dcheckstyle.skip=true clean package"
    else :
        command = f"cd {os.path.join(path_to_folder, relative_path_to_module)} && mvn -Dmaven.test.skip=true -Dcheckstyle.skip=true clean package"
    print("mvn clean and mvn package...")
    exit_status = os.system(command)
    return exit_status

# execute "mvn dependency:tree"
def mvn_dependency_tree(path_to_folder:str):
    # MainProcess_pwd = os.getcwd()
    # log_path = os.path.join(MainProcess_pwd, "data/dependency_tree.txt")
    # create ./DATA
    create_folder(DATA)
    command = f"cd {path_to_folder} && mvn dependency:tree -fae"
    print("generating dependency tree...")
    result = subprocess.run(command, shell=True, text=True, capture_output=True)
    with open(DEPENDENCY_TREE_FILE, 'w') as f:
        f.write(f'{result.stdout}')
    # os.system(command)
    print("dependency tree is generated in ./data/dependency_tree.txt successfully")
    
    