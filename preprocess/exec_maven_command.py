## exectute the mvn command like "mvn package"
# path_to_folder : the path where pom.xml locates
import os
# execute "mvn package"
def mvn_package(path_to_folder:str):
    command = f"cd {path_to_folder} && mvn clean && mvn package -DskipTests"
    print("mvn clean and mvn package...")
    os.system(command)
    print("Uber jar and jar are generated successfully")