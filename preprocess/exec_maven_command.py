## exectute the mvn command like "mvn package"
# path_to_folder : the path where pom.xml locates
import os
import shutil
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
    if relative_path_to_module != '.':
        path_to_folder = os.path.join(path_to_folder, relative_path_to_module)
    command = f"cd {path_to_folder} && mvn clean && mvn package -DskipTests"
    print("mvn clean and mvn package...")
    os.system(command)
    print("client jar are generated successfully")

# execute "mvn dependency:tree"
def mvn_dependency_tree(path_to_folder:str):
    # MainProcess_pwd = os.getcwd()
    # log_path = os.path.join(MainProcess_pwd, "data/dependency_tree.txt")
    # create ./DATA
    create_folder(DATA)
    command = f"cd {path_to_folder} && mvn dependency:tree > {DEPENDENCY_TREE_FILE}"
    print("generating dependency tree...")
    os.system(command)
    print("dependency tree is generated in ./data/dependency_tree.txt successfully")
    
    