## get client jar/Uber jar/dep jar
import os
import shutil
import re
import concurrent.futures
import requests
import time
import json
from preprocess.constants import JAR_FOLDER, DEPENDENCY_TREE_FILE
# from constants import JAR_FOLDER, DEPENDENCY_TREE_FILE

## create a folder
## folder_path : path to folder
def create_folder(folder_path:str):
    # Check if the folder already exists
    if os.path.exists(folder_path):
        # Remove the existing folder
        shutil.rmtree(folder_path)
    # Create the new folder
    os.makedirs(folder_path)

## parse tree to get information of deps(exclude test and provided)
# return a list of dicts containing gav and depth as well as transitive or direct
def parse_dep(all_dep_gav:str):
    # dep_gav_pattern = r"^\[INFO\] (.*?)- (.+?):(.+?):.+:(.+?):(.+?)$"
    dep_gav_pattern = r"^\[INFO\] (.*?)- (.+?):(.+?):jar(.*):(.+?):(.+?)$"
    dep_matches = re.finditer(dep_gav_pattern, all_dep_gav, re.MULTILINE)
    # group(1): lag
    # group(2): groupId
    # group(3): artifactId
    # group(4): ':'+classifier
    # group(5): version
    # group(6): type, like compile
    dep_gav = []
    for dep_match in dep_matches:
        # if dep_match.group(5).endswith('test') is False and dep_match.group(5).endswith("provided") is False:
        #     dep = {}
        #     dep.update({'group_id':f'{dep_match.group(2)}'})
        #     dep.update({'artifact_id':f'{dep_match.group(3)}'})
        #     dep.update({'version':f'{dep_match.group(4)}'})
        #     # get depth from the lenth of substring between "[INFO] " and "-"
        #     depth = (int)((len(dep_match.group(1))+2) / 3)
        #     # depth == 1 means direct which depth > 1 means transitive
        #     dep.update({'depth': depth})
        #     dep_gav.append(dep)
        if dep_match.group(6).endswith('test') is False and dep_match.group(6).endswith("provided") is False:
            dep = {}
            dep.update({'group_id':f'{dep_match.group(2)}'})
            dep.update({'artifact_id':f'{dep_match.group(3)}'})
            dep.update({'classifier':f'{dep_match.group(4).replace(":","")}'})
            dep.update({'version':f'{dep_match.group(5)}'})
            dep.update({'type':f'{dep_match.group(6)}'})
            # get depth from the lenth of substring between "[INFO] " and "-"
            depth = (int)((len(dep_match.group(1))+2) / 3)
            # depth == 1 means direct which depth > 1 means transitive
            dep.update({'depth': depth})
            dep_gav.append(dep)
    return dep_gav
    
## get dep jar using GAV from maven central repository
def get_dep_jar(dep_folder:str, group_id:str, artifact_id:str, version:str, classifier:str):
    # debug
    # print(f'dep {group_id}:{artifact_id}:{version}')
    
    def handle_error_get(jar_url,  retries=5, backoff_factor=0.3):
      # This inner function attempts to get the content from the jar_url with retries
        for attempt in range(retries):
            try:
                response = requests.get(jar_url, timeout=10)  # Set timeout to prevent hanging
                response.raise_for_status()  # Will raise an HTTPError for bad responses
                return response
            except requests.RequestException as e:
                print(f"Attempt {attempt + 1} failed for {artifact_id}-{version}.jar: {str(e)}")
                time.sleep(backoff_factor * (2 ** attempt))  # Exponential backoff
                if attempt == retries - 1:
                    raise  # Re-raise the last exception if all retries fail
    
    if classifier == '':
        jar_url = f"https://repo1.maven.org/maven2/{group_id.replace('.', '/')}/{artifact_id}/{version}/{artifact_id}-{version}.jar"
    else :
        jar_url = f"https://repo1.maven.org/maven2/{group_id.replace('.', '/')}/{artifact_id}/{version}/{artifact_id}-{version}-{classifier}.jar"
    
     # Call the function with retry logic
    try:
        response = handle_error_get(jar_url)
        # Proceed if the download was successful
        if response and response.status_code == 200:
            if classifier == '':
                file_name = os.path.join(dep_folder, f"{group_id}-{artifact_id}-{version}.jar")
            else :
                file_name = os.path.join(dep_folder, f"{group_id}-{artifact_id}-{version}-{classifier}.jar")
            with open(file_name, "wb") as jar_file:
                jar_file.write(response.content)
            if classifier == '':
                print(f"{group_id}-{artifact_id}-{version}.jar downloaded successfully.")
            else :
                print(f"{group_id}-{artifact_id}-{version}-{classifier}.jar downloaded successfully.")
    except Exception as e:
        if classifier == '':
            print(f"Failed to download {artifact_id}-{version}.jar from central repository; Reason: {str(e)}")
        else:
            print(f"Failed to download {artifact_id}-{version}-{classifier}.jar from central repository; Reason: {str(e)}")
        # # sometimes, the dep is a local artifact, so try to get the jar from local repository
        # print("try to get it from local repository:")
        # command = f"mvn dependency:copy -Dartifact={group_id}:{artifact_id}:{version} -DoutputDirectory={dep_folder}"
        # os.system(command)
        

## parse tree
# dependency_tree : content of dependency_tree file
# path_to_folder : path to the clone folder
def parse_for_jar(dependency_tree:str, path_to_cloned_folder:str, relative_path_to_module:str):
    ## regular expression to get a block
    # block_pattern = r'\[INFO\] Building .+?\[(\d+?)/\d+\]\n\[INFO\].+?from (.*?)pom.xml\n\[INFO\] -+?\[ (.+?) \]-+?\n\[INFO\].+?\n\[INFO\].+?\n\[INFO\] (.+?):(.+?):.+?:(.+?)\n(.+?)\[INFO\] -'
    # block_pattern = r'\[INFO\] Building .+?\[(\d+?)/\d+\]\n\[INFO\].+?from (.*?)pom.xml\n\[INFO\] -+?\[ (.+?) \]-+?\n.*?\[INFO\] (\S+?):(\S+?):\S+?:(\S+?)\n(.+?)\[INFO\] -'
    block_pattern = r'\[INFO\] Building .+?\n\[INFO\].+?from (.*?)pom.xml\n\[INFO\] -+?\[ (.+?) \]-+?\n.*?\[INFO\] (\S+?):(\S+?):\S+?:(\S+?)\n(.+?)\[INFO\] -'
    blocks = re.finditer(block_pattern, dependency_tree, flags=re.DOTALL)
    print("\n****** get client jar / dep jar... ******\n")
    # sometimes, the jar name is not as expect;
    # sometimes, the client is war;
    # above clients are ignored
    ignore_client = os.path.join(JAR_FOLDER, f'ignore.txt')
    if os.path.exists(ignore_client):
        os.remove(ignore_client)
    for block in blocks:
        ## finditer
        # print(block.group(0)) # block
        # print(block.group(1)) # module folder
        # print(block.group(2)) # type(like jar)
        # print(block.group(3)) # client groupId
        # print(block.group(4)) # client artifactId
        # print(block.group(5)) # client version
        # print(block.group(6)) # deps
        
        # only handle the specific module
        # if relative_path_to_module is ., then handling all modules
        if relative_path_to_module == '.':
            flag = True
        else:
            # so, argv[2] should end with '/'
            flag = (block.group(1) == relative_path_to_module)
        if block.group(2) == 'jar' and flag:
            # create folder in data/Jar
            print(f"**** process {block.group(3)}:{block.group(4)}:{block.group(5)} ****")
            module = block.group(1)
            if module == '':
                # the module pom is at the root of project
                module = '_'
            folder = os.path.join(JAR_FOLDER, module.replace('/','_'))
            create_folder(folder)
            # record client_gav and Module_folder in inform.json
            with open(os.path.join(folder, 'inform.json'), 'w') as f:
                inform = {"GAV":f"{block.group(3)}:{block.group(4)}:{block.group(5)}",
                           "Module":f"{block.group(1)}"}
                json.dump(inform, f, indent=4)
                
            # copy client jar to folder/client
            client = os.path.join(folder, "client")
            create_folder(client)
            Uber = os.path.join(folder, "Uber")
            create_folder(Uber)
            target = os.path.join(path_to_cloned_folder, f"{block.group(1)}target")
            client_jar = f"{block.group(4)}-{block.group(5)}.jar"
            path_to_client_jar = os.path.join(target, client_jar)
            try:
                shutil.copy(path_to_client_jar, client)
            except FileNotFoundError as e:
                # the jar name is not as expect
                # record the jar 
                print(e)
                with open(ignore_client, 'a') as f:
                    f.write(f'{block.group(3)}:{block.group(4)}:{block.group(5)}\n')
                shutil.rmtree(folder)
                continue
            
            ## get dep jar using GAV from maven central repository
            # create dep folder
            path_to_dep = os.path.join(folder, "dep")
            create_folder(path_to_dep)
            # parse tree to get GAV of deps(exclude test and provided)
            deps = parse_dep(block.group(6))
            # get dep jar and update the list of dicts which will be displayed in json
            # jarname ----> gav
            mappings = []
            
            # for i in range(len(deps_gav)):
            #     get_dep_jar(dep, deps_gav[i]['group_id'], deps_gav[i]['artifact_id'], deps_gav[i]['version'])
            #     mapping = {
            #         "JarFileName": f"{deps_gav[i]['artifact_id']}-{deps_gav[i]['version']}.jar",
            #         "GroupId": f"{deps_gav[i]['group_id']}",
            #         "ArtifactId": f"{deps_gav[i]['artifact_id']}",
            #         "Version": f"{deps_gav[i]['version']}",
            #         "Depth": deps_gav[i]['depth'],
            #         "Index": i
            #     }
            #     mappings.append(mapping)
            num_workers = os.cpu_count()
            with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
                futures = []
                # for dep in deps:
                for i in range(len(deps)):
                    futures.append(executor.submit(download_a_dep_jar, path_to_dep, deps[i], i))
            for future in futures:
                mappings.append(future.result())
            
            # for each dep in mappings, get the deps which are depended by this dep
            for mapping in mappings:
                depended_by = []
                depth = mapping['Depth']-1
                idx = mapping['Index']
                for i in range(idx, -1, -1):
                    if depth == 0:
                        break
                    if mappings[i]['Depth'] == depth:
                        depended_by.append(mappings[i]['JarFileName'])
                        depth = depth-1
                mappings[idx].update({'DependedBy': depended_by})
            # create json
            json_path = os.path.join(path_to_dep, 'match.json')
            with open(json_path, 'w') as json_file:
                json.dump(mappings, json_file, indent=4)
                
        # ignore war
        if block.group(2) == 'war':
            with open(ignore_client, 'a') as f:
                f.write(f'{block.group(3)}:{block.group(4)}:{block.group(5)}\n')
       
# download dep jar concurrently
# path_to_dep: path to dep/
# dep: a dict in deps_gav, dep['group_id'] is groupId, dep['artifact_id'] is artifactId, dep['version'] is version
# mapping: mapping of a dep;
# idx: index of the dep in deps_gav
def download_a_dep_jar(path_to_dep:str, dep:dict, idx:int):
    get_dep_jar(path_to_dep, dep['group_id'], dep['artifact_id'], dep['version'], dep['classifier'])
    if dep['classifier'] == "":
        JarFileName = f'{dep["group_id"]}-{dep["artifact_id"]}-{dep["version"]}.jar'
    else:
        JarFileName = f'{dep["group_id"]}-{dep["artifact_id"]}-{dep["version"]}-{dep["classifier"]}.jar'
    mapping = {
        "JarFileName": JarFileName,
        "GroupId": f"{dep['group_id']}",
        "ArtifactId": f"{dep['artifact_id']}",
        "Classifier": f"{dep['classifier']}",
        "Version": f"{dep['version']}",
        "Type": f"{dep['type']}",
        "Depth": dep['depth'],
        "Index": idx
    }
    return mapping

## main method in this file
# path_to_folder:path to cloned folder
# relative_path_to_module: relative path from project root 
def Get(path_to_cloned_folder:str, relative_path_to_module:str):
    ## create Jar folder
    create_folder(JAR_FOLDER)
    ## parse
    with open(DEPENDENCY_TREE_FILE, 'r') as tree:
        dependency_tree = tree.read()
        # parse tree
        parse_for_jar(dependency_tree, path_to_cloned_folder, relative_path_to_module)
        
        
# test   
if __name__ == "__main__":
    # def expand_resolve_abspath(path):
    #     expanded_path = os.path.expanduser(path)
    #     resolved_path = os.path.normpath(expanded_path)
    #     absolute_path = os.path.abspath(resolved_path)
    #     return absolute_path
    # path = expand_resolve_abspath(f"~/Work/Tool/Tool/data/preprocess/dependency_tree.txt")
    # with open(path, 'r') as f:
    #     dependency_tree = f.read()
    #     parse_for_jar(dependency_tree)
#     tree = '''[INFO] -----------------------< com.iluwatar:strangler >-----------------------
# [INFO] Building strangler 1.26.0-SNAPSHOT                             [131/168]
# [INFO]   from strangler/pom.xml
# [INFO] --------------------------------[ jar ]---------------------------------
# [INFO] 
# [INFO] --- dependency:3.6.0:tree (default-cli) @ strangler ---
# [INFO] com.iluwatar:strangler:jar:1.26.0-SNAPSHOT
# [INFO] +- org.junit.jupiter:junit-jupiter-engine:jar:5.8.2:test
# [INFO] |  +- org.junit.platform:junit-platform-engine:jar:1.8.2:test
# [INFO] |  |  +- org.opentest4j:opentest4j:jar:1.2.0:test
# [INFO] |  |  \- org.junit.platform:junit-platform-commons:jar:1.8.2:test
# [INFO] |  +- org.junit.jupiter:junit-jupiter-api:jar:5.8.2:test
# [INFO] |  \- org.apiguardian:apiguardian-api:jar:1.1.2:test
# [INFO] +- org.slf4j:slf4j-api:jar:1.7.36:compile
# [INFO] +- ch.qos.logback:logback-classic:jar:1.2.11:compile
# [INFO] +- ch.qos.logback:logback-core:jar:1.2.11:compile
# [INFO] \- org.projectlombok:lombok:jar:1.18.24:provided
# [INFO] 
# '''
#     # download in /preprocess/data/preprocess/Jar rather than /data/preprocess/Jar in test
#     parse_for_jar(tree, f"/home/ray/Work/Tool/Data/fudan_paper_client/584/java-design-patterns")

#     dep = '''[INFO] +- org.junit.jupiter:junit-jupiter-engine:jar:5.8.2:test
# [INFO] |  +- org.junit.platform:junit-platform-engine:jar:1.8.2:test
# [INFO] |  |  +- org.opentest4j:opentest4j:jar:1.2.0:test
# [INFO] |  |  \- org.junit.platform:junit-platform-commons:jar:1.9.0:test
# [INFO] |  +- org.junit.jupiter:junit-jupiter-api:jar:5.8.2:test
# [INFO] |  \- org.apiguardian:apiguardian-api:jar:1.1.2:test
# [INFO] +- org.slf4j:slf4j-api:jar:2.0.12:compile
# [INFO] +- ch.qos.logback:logback-classic:jar:1.5.3:compile
# [INFO] +- ch.qos.logback:logback-core:jar:1.5.3:compile
# [INFO] \- org.projectlombok:lombok:jar:1.18.24:provided'''
    dep = '''[INFO] |  |  +- io.netty:netty-transport-native-unix-common:jar:4.1.100.Final:compile
[INFO] |  |  +- io.netty:netty-handler-proxy:jar:4.1.100.Final:compile
[INFO] |  |  +- io.netty:netty-handler-ssl-ocsp:jar:4.1.100.Final:compile
[INFO] |  |  +- io.netty:netty-resolver:jar:4.1.100.Final:compile
[INFO] |  |  +- io.netty:netty-resolver-dns:jar:4.1.100.Final:compile
[INFO] |  |  +- io.netty:netty-transport:jar:4.1.100.Final:compile
[INFO] |  |  +- io.netty:netty-transport-rxtx:jar:4.1.100.Final:compile
[INFO] |  |  +- io.netty:netty-transport-sctp:jar:4.1.100.Final:compile
[INFO] |  |  +- io.netty:netty-transport-udt:jar:4.1.100.Final:compile
[INFO] |  |  +- io.netty:netty-transport-classes-epoll:jar:4.1.100.Final:compile
[INFO] |  |  +- io.netty:netty-transport-classes-kqueue:jar:4.1.100.Final:compile
[INFO] |  |  +- io.netty:netty-resolver-dns-classes-macos:jar:4.1.100.Final:compile
[INFO] |  |  +- io.netty:netty-transport-native-epoll:jar:linux-x86_64:4.1.100.Final:runtime
[INFO] |  |  +- io.netty:netty-transport-native-epoll:jar:linux-aarch_64:4.1.100.Final:runtime
[INFO] |  |  +- io.netty:netty-transport-native-kqueue:jar:osx-x86_64:4.1.100.Final:runtime
[INFO] |  |  +- io.netty:netty-transport-native-kqueue:jar:osx-aarch_64:4.1.100.Final:runtime
[INFO] |  |  +- io.netty:netty-resolver-dns-native-macos:jar:osx-x86_64:4.1.100.Final:runtime
[INFO] |  |  \- io.netty:netty-resolver-dns-native-macos:jar:osx-aarch_64:4.1.100.Final:runtime'''
    print(parse_dep(dep))