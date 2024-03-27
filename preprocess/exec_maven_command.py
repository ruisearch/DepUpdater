## exectute the mvn command like "mvn package"
# path_to_folder : the path where pom.xml locates
import os
# execute "mvn package"
def mvn_package(path_to_folder:str):
    command = f"cd {path_to_folder} && mvn clean && mvn package -DskipTests"
    print("mvn clean and mvn package...")
    os.system(command)
    print("Uber jar and jar are generated successfully")

# execute "mvn dependency:tree"
def mvn_dependency_tree(path_to_folder:str):
    MainProcess_pwd = os.getcwd()
    log_path = os.path.join(MainProcess_pwd, "out/preprocess/dependency_tree.txt")
    command = f"cd {path_to_folder} && mvn dependency:tree > {log_path}"
    print("generating dependency tree")
    os.system(command)
    print("dependency tree is generated successfully")
    
    