## get client jar/Uber jar/dep jar
import os
import shutil
import re
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

## parse tree
# dependency_tree : content of dependency_tree file
# path_to_folder : path to the clone folder
def parse_for_jar(dependency_tree:str, path_to_cloned_folder:str):
    ## regular expression to get a block
    block_pattern = r"\[INFO\] -+?<.+?\n\[INFO\] .+?\[(\d+?)/\d+\]\n\[INFO\].+?from (.+?)/pom.xml\n\[INFO\] -+?\[ (.+?) \]-+?\n.+?\n.+?\n\[INFO\] (.+?):(.+?):.+?:(.+?)\n(.+?)\[INFO\] \n"
    blocks = re.finditer(block_pattern, dependency_tree, flags=re.DOTALL)
    for block in blocks:
        # print(block.group(0)) # block
        # print(block.group(1)) # number
        # print(block.group(2)) # module folder
        # print(block.group(3)) # type(like jar)
        # print(block.group(4)) # groupId
        # print(block.group(5)) # artifactId
        # print(block.group(6)) # version
        # print(block.group(7)) # dep
        if block.group(3) == 'jar':
            ## copy client jar and Uber jar into out/preprocess
            # jar: artifactId[block.group(5)]-version[block.group(6)].jar / Uber jar: original-jar
            # create folder in out/preprocess
            print("get client...")
            folder = os.path.join(JAR_FOLDER, block.group(1))
            create_folder(folder)
            # write GAV of client in client_name.txt
            with open(os.path.join(folder,'client_name.txt'), 'w') as f:
                f.write("{block.group(4)}:{block.group(5)}:{block.group(6)}")
            # copy client jar to folder/client
            target = os.path.join(path_to_cloned_folder, f"{block.group(2)}/target")
            client = os.path.join(folder, "client")
            create_folder(client)
            
            
    

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
    parse_for_jar(tree)