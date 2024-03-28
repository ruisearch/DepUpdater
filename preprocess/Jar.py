## get client jar/Uber jar/dep jar
import os
import shutil
import re
import requests
from constants import JAR_FOLDER, DEPENDENCY_TREE_FILE

## create a folder
## folder_path : path to folder
def create_folder(folder_path:str):
    # Check if the folder already exists
    if os.path.exists(folder_path):
        # Remove the existing folder
        shutil.rmtree(folder_path)
    # Create the new folder
    os.makedirs(folder_path)

## parse tree to get GAV of deps(exclude test and provided)
# return a list of dicts containing gav
def parse_dep_gav(all_dep_gav:str):
    dep_gav_pattern = r"- (.+?):(.+?):.+?:(.+?):(.+?)\n"
    dep_matches = re.finditer(dep_gav_pattern, all_dep_gav)
    dep_gav = []
    for dep_match in dep_matches:
        # ignore test and provided dep
        if dep_match.group(4) != 'test' and dep_match.group(4) != "provided":
            dep = {}
            dep.update({'group_id':f'{dep_match.group(1)}'})
            dep.update({'artifact_id':f'{dep_match.group(2)}'})
            dep.update({'version':f'{dep_match.group(3)}'})
            dep_gav.append(dep)
    return dep_gav    
    # ---------- to be continued--------#
    
## get dep jar using GAV from maven central repository
def get_dep_jar(dep_folder:str, group_id:str, artifact_id:str, version:str):
    jar_url = f"https://repo1.maven.org/maven2/{group_id.replace('.', '/')}/{artifact_id}/{version}/{artifact_id}-{version}.jar"
    response = requests.get(jar_url)
    print(f"url:{jar_url}")
    
    if response.status_code == 200:
        file_name = os.path.join(dep_folder,f"{artifact_id}-{version}.jar")
        with open(file_name, "wb") as jar_file:
            jar_file.write(response.content)
        print(f"Dependency {artifact_id}-{version}.jar downloaded successfully.")
    else:
        print(f"Failed to download dependency {artifact_id}-{version}.jar. Reason : {response.reason}")

## parse tree
# dependency_tree : content of dependency_tree file
# path_to_folder : path to the clone folder
def parse_for_jar(dependency_tree:str, path_to_cloned_folder:str):
    ## regular expression to get a block
    block_pattern = r"\[INFO\] -+?<.+?\n\[INFO\] .+?\[(\d+?)/\d+\]\n\[INFO\].+?from (.+?)/pom.xml\n\[INFO\] -+?\[ (.+?) \]-+?\n.+?\n.+?\n\[INFO\] (.+?):(.+?):.+?:(.+?)\n(.+?)\[INFO\] \n"
    blocks = re.finditer(block_pattern, dependency_tree, flags=re.DOTALL)
    print("get client jar / Uber jar/ dep jar...")
    for block in blocks:
        # print(block.group(0)) # block
        # print(block.group(1)) # number
        # print(block.group(2)) # module folder
        # print(block.group(3)) # type(like jar)
        # print(block.group(4)) # client groupId
        # print(block.group(5)) # client artifactId
        # print(block.group(6)) # client version
        # print(block.group(7)) # dep
        if block.group(3) == 'jar':
            ## copy client jar and Uber jar into out/preprocess
            # jar: artifactId[block.group(5)]-version[block.group(6)].jar / Uber jar: original-jar
            # create folder in out/preprocess
            folder = os.path.join(JAR_FOLDER, block.group(1))
            create_folder(folder)
            # write GAV of client in client_name.txt
            with open(os.path.join(folder,'client_gav.txt'), 'w') as f:
                f.write(f"{block.group(4)}:{block.group(5)}:{block.group(6)}")
                
            # copy client jar to folder/client
            target = os.path.join(path_to_cloned_folder, f"{block.group(2)}/target")
            client = os.path.join(folder, "client")
            create_folder(client)
            client_jar = f"{block.group(5)}-{block.group(6)}.jar"
            path_to_client_jar = os.path.join(target, client_jar)
            shutil.copy(path_to_client_jar, client)
            
            # copy Uber jar to folder/Uber
            Uber = os.path.join(folder, "Uber")
            create_folder(Uber)
            Uber_jar = f"original-{client_jar}"
            path_to_Uber_jar = os.path.join(target, Uber_jar)
            shutil.copy(path_to_Uber_jar, Uber)
            
            ## get dep jar using GAV from maven central repository
            # create dep folder
            dep = os.path.join(folder, "dep")
            create_folder(dep)
            # parse tree to get GAV of deps(exclude test and provided)
            deps_gav = parse_dep_gav(block.group(7))
            for dep_gav in deps_gav:
                get_dep_jar(dep, dep_gav['group_id'], dep_gav['artifact_id'], dep_gav['version'])
            
            
    

## main method in this file
# path_to_folder:path to cloned folder
def Get(path_to_cloned_folder:str):
    ## create Jar folder
    create_folder(JAR_FOLDER)
    ## parse
    with open(DEPENDENCY_TREE_FILE, 'r') as tree:
        dependency_tree = tree.read()
        # parse tree
        parse_for_jar(dependency_tree, path_to_cloned_folder)
        
        
# test   
if __name__ == "__main__":
    # def expand_resolve_abspath(path):
    #     expanded_path = os.path.expanduser(path)
    #     resolved_path = os.path.normpath(expanded_path)
    #     absolute_path = os.path.abspath(resolved_path)
    #     return absolute_path
    # path = expand_resolve_abspath(f"~/Work/Tool/Tool/out/preprocess/dependency_tree.txt")
    # with open(path, 'r') as f:
    #     dependency_tree = f.read()
    #     parse_for_jar(dependency_tree)
    tree = '''[INFO] -----------------------< com.iluwatar:strangler >-----------------------
[INFO] Building strangler 1.26.0-SNAPSHOT                             [131/168]
[INFO]   from strangler/pom.xml
[INFO] --------------------------------[ jar ]---------------------------------
[INFO] 
[INFO] --- dependency:3.6.0:tree (default-cli) @ strangler ---
[INFO] com.iluwatar:strangler:jar:1.26.0-SNAPSHOT
[INFO] +- org.junit.jupiter:junit-jupiter-engine:jar:5.8.2:test
[INFO] |  +- org.junit.platform:junit-platform-engine:jar:1.8.2:test
[INFO] |  |  +- org.opentest4j:opentest4j:jar:1.2.0:test
[INFO] |  |  \- org.junit.platform:junit-platform-commons:jar:1.8.2:test
[INFO] |  +- org.junit.jupiter:junit-jupiter-api:jar:5.8.2:test
[INFO] |  \- org.apiguardian:apiguardian-api:jar:1.1.2:test
[INFO] +- org.slf4j:slf4j-api:jar:1.7.36:compile
[INFO] +- ch.qos.logback:logback-classic:jar:1.2.11:compile
[INFO] +- ch.qos.logback:logback-core:jar:1.2.11:compile
[INFO] \- org.projectlombok:lombok:jar:1.18.24:provided
[INFO] 
'''
    # download in /preprocess/out/preprocess/Jar rather than /out/preprocess/Jar in test
    parse_for_jar(tree, f"/home/ray/Work/Tool/Data/fudan_paper_client/584/java-design-patterns")