## get client jar/Uber jar/dep jar
import os
import shutil
import re
import concurrent.futures
import requests
import time
import json
from preprocess.constants import JAR_FOLDER, DEPENDENCY_TREE_FILE, DEPENDENCY_VERBOSE_TREE_FILE
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
        if classifier == '':
            file_name = os.path.join(dep_folder, f"{group_id}-{artifact_id}-{version}.jar")
        else :
            file_name = os.path.join(dep_folder, f"{group_id}-{artifact_id}-{version}-{classifier}.jar")
        # prevent download repeatly
        if os.path.exists(file_name):
            return
        response = handle_error_get(jar_url)
        # Proceed if the download was successful
        if response and response.status_code == 200:
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

## parse tree(verbose) to get a list of deps(without imformation like GAV, just the record as well as the dependents and depth)
# create the Jar folder and copy client jar as well 
def parse_tree_for_deps(dependency_tree:str, path_to_cloned_folder:str, relative_path_to_module:str):
    ## regular expression to get a block
    block_pattern = r'\[INFO\] Building .+?\n\[INFO\].+?from (.*?)pom.xml\n\[INFO\] -+?\[ (.+?) \]-+?\n.*?\[INFO\] (\S+?):(\S+?):\S+?:(\S+?)\n(.+?)\[INFO\] -'
    blocks = re.finditer(block_pattern, dependency_tree, flags=re.DOTALL)
    print("\n****** extract deps... ******\n")
    # sometimes, the jar name is not as expect;
    # sometimes, the client is war;
    # above clients are ignored
    ignore_client = os.path.join(JAR_FOLDER, f'ignore.txt')
    if os.path.exists(ignore_client):
        os.remove(ignore_client)
    for block in blocks:
        # print(block.group(0)) # block
        # print(block.group(1)) # module folder
        # print(block.group(2)) # type(like jar)
        # print(block.group(3)) # client groupId
        # print(block.group(4)) # client artifactId
        # print(block.group(5)) # client version
        # print(block.group(6)) # deps
        
        # only handle the specific module
        # if relative_path_to_module is ., the module's pom is at the root
        if relative_path_to_module == '.':
            flag = (block.group(1) == '')
        else:
            # so, argv[2] should end with '/' unless the module's pom is at the root dir 
            flag = (block.group(1) == relative_path_to_module)
        if block.group(2) == 'jar' and flag:
            # get the module name(replace '/' with '_' to appear in folder name)
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
            
            # parse tree to get all deps
            deps = parse_all_dep(block.group(6))
            # return path to Jar folder and deps list
            return folder, deps
    
            
# return a list containing all deps as well as the dependent and depth
def parse_all_dep(tree:str):
    dep_pattern = r"^\[INFO\] (.*?)- (.+?)$"
    dep_matches = re.finditer(dep_pattern, tree, re.MULTILINE)
    # group(1): lag
    # group(2): dep
    
    deps = []
    for dep_match in dep_matches:
        is_test = ":test" in dep_match.group(2)
        is_provided = ":provided" in dep_match.group(2)
        if is_test is False and is_provided is False:
            dep = {}
            dep.update({'dep':dep_match.group(2)})
            # get depth from the lenth of substring between "[INFO] " and "-"
            depth = (int)((len(dep_match.group(1))+2) / 3)
            # depth == 1 means direct which depth > 1 means transitive
            dep.update({'Depth':depth})
            deps.append(dep)
    
    # get dependent
    for idx in range(len(deps)):
        depth = deps[idx]['Depth'] - 1
        DependedBy = []
        for i in range(idx, -1, -1):
            if depth == 0:
                break
            if deps[i]['Depth'] == depth:
                DependedBy.append(deps[i]['dep'])
                depth = depth - 1
        deps[idx].update({"DependedBy":DependedBy})
    
    
    return deps


## main method in this file
# path_to_folder:path to cloned folder
# relative_path_to_module: relative path from project root 
def Get(path_to_cloned_folder:str, relative_path_to_module:str):
    ## create Jar folder
    create_folder(JAR_FOLDER)
    ## parse
    # with open(DEPENDENCY_TREE_FILE, 'r') as tree:
    with open(DEPENDENCY_VERBOSE_TREE_FILE, 'r') as tree:
        dependency_tree = tree.read()
    # parse tree
    # parse_for_jar(dependency_tree, path_to_cloned_folder, relative_path_to_module)
    folder, all_deps = parse_tree_for_deps(dependency_tree, path_to_cloned_folder, relative_path_to_module)
    # filter the deps into effective_deps and omitted_deps
    effective_deps, omitted_deps = filter_dep(all_deps)
    # parse the dep in effective_deps and omitted_deps to get jar and match.json
    parse_for_jar_and_json(effective_deps, omitted_deps, folder)

# filter the deps into effective_deps and omitted_deps
def filter_dep(all_deps:list):
    effective_deps = []
    omitted_deps = []
    for dep in all_deps:
        if dep['dep'].startswith('('):
            # omitted dep
            omitted_deps.append(dep)
        else:
            effective_deps.append(dep)
    return effective_deps, omitted_deps

# parse the dep in effective_deps and _deps to get jar and match.json
# module_folder : path to data/Jar/{module_name}
# dep key:{dep, Depth, DependedBy}
def parse_for_jar_and_json(effective_deps:list, omitted_deps:list, module_folder:str):
    # change the effective_deps
    change_effective_deps(effective_deps)
    # change the omitted_deps
    change_omitted_deps(omitted_deps)
    # path to Jar/{module}/dep
    path_to_dep = os.path.join(module_folder, "dep")
    create_folder(path_to_dep)
    # get dep jar and update the list of dicts which will be displayed in json
    # jarname ----> gav
    mappings = []
    # pass the effective_deps using processPool
    num_workers = os.cpu_count()
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = []
        for i in range(len(effective_deps)):
            futures.append(executor.submit(process_an_effective_dep, path_to_dep, effective_deps[i], omitted_deps))
    for future in futures:
        mappings.append(future.result()) 
        
    # create json
    json_path = os.path.join(module_folder, 'match.json')
    with open(json_path, 'w') as json_file:
        json.dump(mappings, json_file, indent=4)
        
# process an effective dep: get the jar, get the related omitted dep and download the related omitted jar
# effective_dep{group_id, artifact_id, classifier, version, type, depth, DependedBy}
# --> mapping{JarFileName, GroupId, ArtifactId, Classifier, Version, Type, Depth, DependedBy, Omitted}
# Omitted is a list of dict containing Omitted_dep
# omitted_dep{group_id, artifact_id, classifier, version, type, depth, DependedBy}
# --> related{JarFileName, Version, DependedBy}
# note: "DependedBy" above is dependants like "org.mockito:mockito-core:jar:4.11.0:compile"
# and DependedBy is always effective deps
# so, should change the record into the JarFileName
def process_an_effective_dep(path_to_dep:str, effective_dep:dict, omitted_deps:list):
    get_dep_jar(path_to_dep, effective_dep['group_id'], effective_dep['artifact_id'], effective_dep['version'], effective_dep['classifier'])
    JarFileName = dict_to_JarFileName(effective_dep)
    # change the DependedBy of effective_dep
    for i in range(len(effective_dep['DependedBy'])):
        effective_dep['DependedBy'][i] = dict_to_JarFileName(record_to_dict(effective_dep['DependedBy'][i]))
    
    Omitted = []
    # find the related omitted_deps
    for omitted_dep in omitted_deps:
        related = {}
        if omitted_dep['group_id'] == effective_dep['group_id'] and omitted_dep['artifact_id'] == effective_dep['artifact_id'] \
            and omitted_dep['classifier'] == effective_dep['classifier'] :
            # omitted_dep is the omitted dep of effective_dep
            # download the omitted_dep
            get_dep_jar(path_to_dep, omitted_dep['group_id'], omitted_dep['artifact_id'], omitted_dep['version'], omitted_dep['classifier'])
            # relate effective_dep with omitted_dep
            omitted_jarfilename = dict_to_JarFileName(omitted_dep)
            Version = omitted_dep['version']
            DependedBy = []
            for dependant in omitted_dep['DependedBy']:
                DependedBy.append(dict_to_JarFileName(record_to_dict(dependant)))
            related.update({'JarFileName':omitted_jarfilename})
            related.update({'Version':Version})
            related.update({'DependedBy':DependedBy})
            Omitted.append(related)
    
    # return the mapping(which will be dispalyed in match.json) of effective_dep
    mapping = {
        "JarFileName": JarFileName,
        "GroupId": effective_dep['group_id'],
        "ArtifactId": effective_dep['artifact_id'],
        "Classifier": effective_dep['classifier'],
        "Version": effective_dep['version'],
        "Type": effective_dep['type'],
        "Depth": effective_dep['depth'],
        "DependedBy":effective_dep['DependedBy'],
        "Omitted":Omitted
    }
    
    return mapping
    
            
  
# transform a record into tree to dep{group_id, artifact_id, classifier, version}
def record_to_dict(record:str):
    pattern = r"(.+?):(.+?):jar(.*):(.+?):.+?\b"
    match = re.search(pattern, record)
    return {'group_id':match.group(1), 'artifact_id':match.group(2), 'classifier':match.group(3), 'version':match.group(4)}
# transform dep{group_id, artifact_id, classifier, version} into JarFileName
def dict_to_JarFileName(dep:dict):
    if dep['classifier'] == "":
        return f'{dep["group_id"]}-{dep["artifact_id"]}-{dep["version"]}.jar'
    else:
        return f'{dep["group_id"]}-{dep["artifact_id"]}-{dep["version"]}-{dep["classifier"]}.jar'

# change the effective_deps
# dep key:{dep, Depth, DependedBy} --> dep key:{group_id, artifact_id, classifier, version, type, depth, DependedBy}
def change_effective_deps(effective_deps:list):
    gav_pattern = r"(.+?):(.+?):jar(.*):(.+?):(.+?)\b"
    for i in range(len(effective_deps)):
        dep = {}
        match = re.search(gav_pattern, effective_deps[i]['dep'])
        dep.update({'group_id':match.group(1)})
        dep.update({'artifact_id':match.group(2)})
        dep.update({'classifier':match.group(3).replace(":","")})
        dep.update({'version':match.group(4)})
        dep.update({'type':match.group(5)})
        dep.update({'depth':effective_deps[i]['Depth']})
        dep.update({'DependedBy':effective_deps[i]['DependedBy']})
        # test
        # print(dep)
        effective_deps[i] = dep

# change the omitted_deps
# dep key:{dep, Depth, DependedBy} --> dep key:{group_id, artifact_id, classifier, version, type, depth, DependedBy}
def change_omitted_deps(omitted_deps:list):
    # duplicate and covered by pom
    # eg:
    # (org.junit.platform:junit-platform-engine:jar:1.10.2:runtime - version managed from 1.10.2; omitted for duplicate)
    gav_pattern_1 = r"\((.+?):(.+?):jar(.*):(.+?):(.+?) - version managed from (.+?); omitted for duplicate\)"
    # duplicate but not covered by pom
    # eg:
    # (org.eclipse.sisu:org.eclipse.sisu.inject:jar:0.9.0.M2:compile - omitted for duplicate)
    gav_pattern_2 = r"\((.+?):(.+?):jar(.*):(.+?):(.+?) - omitted for duplicate\)"
    # conflict
    # eg:
    # (org.codehaus.plexus:plexus-classworlds:jar:2.6.0:compile - omitted for conflict with 2.7.0)
    gav_pattern_3 = r"\((.+?):(.+?):jar(.*):(.+?):(.+?) - omitted for conflict with (.+?)\)"
    for i in range(len(omitted_deps)):
        dep = {}
        match = re.search(gav_pattern_1, omitted_deps[i]['dep'])
        if match is not None:
            # duplicate and covered by pom
            dep.update({'group_id':match.group(1)})
            dep.update({'artifact_id':match.group(2)})
            dep.update({'classifier':match.group(3).replace(":","")})
            dep.update({'version':match.group(6)})
            dep.update({'type':match.group(5)})
            dep.update({'depth':omitted_deps[i]['Depth']})
            dep.update({'DependedBy':omitted_deps[i]['DependedBy']})
            omitted_deps[i] = dep
            continue
        match = re.search(gav_pattern_2, omitted_deps[i]['dep'])
        if match is not None:
            # duplicate but not covered by pom
            dep.update({'group_id':match.group(1)})
            dep.update({'artifact_id':match.group(2)})
            dep.update({'classifier':match.group(3).replace(":","")})
            dep.update({'version':match.group(4)})
            dep.update({'type':match.group(5)})
            dep.update({'depth':omitted_deps[i]['Depth']})
            dep.update({'DependedBy':omitted_deps[i]['DependedBy']})
            omitted_deps[i] = dep
            continue
        match = re.search(gav_pattern_3, omitted_deps[i]['dep'])
        if match is not None:
            # conflict
            dep.update({'group_id':match.group(1)})
            dep.update({'artifact_id':match.group(2)})
            dep.update({'classifier':match.group(3).replace(":","")})
            dep.update({'version':match.group(4)})
            dep.update({'type':match.group(5)})
            dep.update({'depth':omitted_deps[i]['Depth']})
            dep.update({'DependedBy':omitted_deps[i]['DependedBy']})
            omitted_deps[i] = dep
            continue
            
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
#     dep = '''[INFO] |  |  +- io.netty:netty-transport-native-unix-common:jar:4.1.100.Final:compile
# [INFO] |  |  +- io.netty:netty-handler-proxy:jar:4.1.100.Final:compile
# [INFO] |  |  +- io.netty:netty-handler-ssl-ocsp:jar:4.1.100.Final:compile
# [INFO] |  |  +- io.netty:netty-resolver:jar:4.1.100.Final:compile
# [INFO] |  |  +- io.netty:netty-resolver-dns:jar:4.1.100.Final:compile
# [INFO] |  |  +- io.netty:netty-transport:jar:4.1.100.Final:compile
# [INFO] |  |  +- io.netty:netty-transport-rxtx:jar:4.1.100.Final:compile
# [INFO] |  |  +- io.netty:netty-transport-sctp:jar:4.1.100.Final:compile
# [INFO] |  |  +- io.netty:netty-transport-udt:jar:4.1.100.Final:compile
# [INFO] |  |  +- io.netty:netty-transport-classes-epoll:jar:4.1.100.Final:compile
# [INFO] |  |  +- io.netty:netty-transport-classes-kqueue:jar:4.1.100.Final:compile
# [INFO] |  |  +- io.netty:netty-resolver-dns-classes-macos:jar:4.1.100.Final:compile
# [INFO] |  |  +- io.netty:netty-transport-native-epoll:jar:linux-x86_64:4.1.100.Final:runtime
# [INFO] |  |  +- io.netty:netty-transport-native-epoll:jar:linux-aarch_64:4.1.100.Final:runtime
# [INFO] |  |  +- io.netty:netty-transport-native-kqueue:jar:osx-x86_64:4.1.100.Final:runtime
# [INFO] |  |  +- io.netty:netty-transport-native-kqueue:jar:osx-aarch_64:4.1.100.Final:runtime
# [INFO] |  |  +- io.netty:netty-resolver-dns-native-macos:jar:osx-x86_64:4.1.100.Final:runtime
# [INFO] |  |  \- io.netty:netty-resolver-dns-native-macos:jar:osx-aarch_64:4.1.100.Final:runtime'''
#     print(parse_dep(dep))
    dep = 'com.fasterxml.jackson.core:jackson-annotations:jar:2.16.1:test (version managed from 2.16.1)'
    dep = 'org.mockito:mockito-core:jar:4.11.0:compile'
    gav_pattern = r"(.+?):(.+?):jar(.*):(.+?):(.+?)\b"
    match = re.search(gav_pattern, dep)
    print(match.group(1),match.group(2),match.group(3),match.group(4),match.group(5))