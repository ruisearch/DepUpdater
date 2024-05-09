## get client jar/Uber jar/dep jar
import os
import shutil
import re
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

## parse tree to get GAV of deps(exclude test and provided)
# return a list of dicts containing gav as well as transitive or direct
def parse_dep_gav(all_dep_gav:str):
    # dep_gav_pattern = r"- (.+?):(.+?):.+?:(.+?):(.+?)\s"
    # dep_matches = re.finditer(dep_gav_pattern, all_dep_gav)
    dep_gav_pattern = r"^\[INFO\] (.*?)- (.+?):(.+?):.+?:(.+?):(.+?)$"
    dep_matches = re.finditer(dep_gav_pattern, all_dep_gav, re.MULTILINE)
    dep_gav = []
    for dep_match in dep_matches:
        # # ignore test and provided dep
        # if dep_match.group(4) != 'test' and dep_match.group(4) != "provided":
        #     dep = {}
        #     dep.update({'group_id':f'{dep_match.group(1)}'})
        #     dep.update({'artifact_id':f'{dep_match.group(2)}'})
        #     dep.update({'version':f'{dep_match.group(3)}'})
        #     dep_gav.append(dep)
        if dep_match.group(5) != 'test' and dep_match.group(5) != "provided" and dep_match.group(5) != 'test (optional)' and dep_match.group(5) != 'provided (optional)':
            dep = {}
            dep.update({'group_id':f'{dep_match.group(2)}'})
            dep.update({'artifact_id':f'{dep_match.group(3)}'})
            dep.update({'version':f'{dep_match.group(4)}'})
            # vertical_count = dep_match.group(1).count('|')
            # get depth from the lenth of substring between "[INFO] " and "-"
            depth = (int)((len(dep_match.group(1))+2) / 3)
            # depth == 1 means direct which depth > 1 means transitive
            dep.update({'depth': depth})
            dep_gav.append(dep)
    # # test
    # print(dep_gav)
    return dep_gav    
    
## get dep jar using GAV from maven central repository
def get_dep_jar(dep_folder:str, group_id:str, artifact_id:str, version:str):
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
    
        
    jar_url = f"https://repo1.maven.org/maven2/{group_id.replace('.', '/')}/{artifact_id}/{version}/{artifact_id}-{version}.jar"
    
     # Call the function with retry logic
    try:
        response = handle_error_get(jar_url)
        # Proceed if the download was successful
        if response and response.status_code == 200:
            file_name = os.path.join(dep_folder, f"{artifact_id}-{version}.jar")
            with open(file_name, "wb") as jar_file:
                jar_file.write(response.content)
            print(f"{artifact_id}-{version}.jar downloaded successfully.")
    except Exception as e:
        print(f"Failed to download {artifact_id}-{version}.jar from central repository; Reason: {str(e)}")
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
        # print(block.group(6)) # dep
        
        # only handle the specific module
        # if relative_path_to_module is ., then handling all modules
        if relative_path_to_module == '.':
            flag = True
        else:
            flag = (block.group(1) == relative_path_to_module)
        if block.group(2) == 'jar' and flag:
            # create folder in data/Jar
            print(f"**** process {block.group(3)}:{block.group(4)}:{block.group(5)} ****")
            module = block.group(1)
            if module == '':
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
            dep = os.path.join(folder, "dep")
            create_folder(dep)
            # parse tree to get GAV of deps(exclude test and provided)
            deps_gav = parse_dep_gav(block.group(6))
            # get dep jar and update the list of dicts which will be displayed in json
            # jarname ----> gav
            mappings = []
            for dep_gav in deps_gav:
                get_dep_jar(dep, dep_gav['group_id'], dep_gav['artifact_id'], dep_gav['version'])
                mapping = {
                    "JarFileName": f"{dep_gav['artifact_id']}-{dep_gav['version']}.jar",
                    "GroupId": f"{dep_gav['group_id']}",
                    "ArtifactId": f"{dep_gav['artifact_id']}",
                    "Version": f"{dep_gav['version']}",
                    "Depth": dep_gav['depth']
                }
                mappings.append(mapping)
            # create json
            json_path = os.path.join(dep, 'match.json')
            with open(json_path, 'a') as json_file:
                json.dump(mappings, json_file, indent=4)
                
        # ignore war
        if block.group(2) == 'war':
            with open(ignore_client, 'a') as f:
                f.write(f'{block.group(3)}:{block.group(4)}:{block.group(5)}\n')
            
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
    dep = '''[INFO] +- org.springframework.boot:spring-boot-starter:jar:3.2.4:compile
[INFO] |  +- org.springframework.boot:spring-boot:jar:3.2.4:compile
[INFO] |  |  \- org.springframework:spring-context:jar:6.1.5:compile
[INFO] |  |     +- org.springframework:spring-expression:jar:6.1.5:compile
[INFO] |  |     \- io.micrometer:micrometer-observation:jar:1.12.4:compile
[INFO] |  |        \- io.micrometer:micrometer-commons:jar:1.12.4:compile
[INFO] |  +- org.springframework.boot:spring-boot-autoconfigure:jar:3.2.4:compile
[INFO] |  +- org.springframework.boot:spring-boot-starter-logging:jar:3.2.4:compile
[INFO] |  |  +- org.apache.logging.log4j:log4j-to-slf4j:jar:2.21.1:compile
[INFO] |  |  |  \- org.apache.logging.log4j:log4j-api:jar:2.21.1:compile
[INFO] |  |  \- org.slf4j:jul-to-slf4j:jar:2.0.12:compile
[INFO] |  +- jakarta.annotation:jakarta.annotation-api:jar:2.1.1:compile
[INFO] |  +- org.springframework:spring-core:jar:6.1.5:compile
[INFO] |  |  \- org.springframework:spring-jcl:jar:6.1.5:compile
[INFO] |  \- org.yaml:snakeyaml:jar:2.2:compile
[INFO] +- org.springframework.boot:spring-boot-starter-data-jpa:jar:3.2.4:compile
[INFO] |  +- org.springframework.boot:spring-boot-starter-aop:jar:3.2.4:compile
[INFO] |  |  +- org.springframework:spring-aop:jar:6.1.5:compile
[INFO] |  |  \- org.aspectj:aspectjweaver:jar:1.9.21:compile
[INFO] |  +- org.springframework.boot:spring-boot-starter-jdbc:jar:3.2.4:compile
[INFO] |  |  +- com.zaxxer:HikariCP:jar:5.0.1:compile
[INFO] |  |  \- org.springframework:spring-jdbc:jar:6.1.5:compile
[INFO] |  +- org.hibernate.orm:hibernate-core:jar:6.4.4.Final:compile
[INFO] |  |  +- jakarta.persistence:jakarta.persistence-api:jar:3.1.0:compile
[INFO] |  |  +- jakarta.transaction:jakarta.transaction-api:jar:2.0.1:compile
[INFO] |  |  +- org.jboss.logging:jboss-logging:jar:3.5.3.Final:runtime
[INFO] |  |  +- org.hibernate.common:hibernate-commons-annotations:jar:6.0.6.Final:runtime
[INFO] |  |  +- io.smallrye:jandex:jar:3.1.2:runtime
[INFO] |  |  +- com.fasterxml:classmate:jar:1.6.0:runtime
[INFO] |  |  +- net.bytebuddy:byte-buddy:jar:1.14.12:runtime
[INFO] |  |  +- org.glassfish.jaxb:jaxb-runtime:jar:4.0.5:runtime
[INFO] |  |  |  \- org.glassfish.jaxb:jaxb-core:jar:4.0.5:runtime
[INFO] |  |  |     +- org.eclipse.angus:angus-activation:jar:2.0.2:runtime
[INFO] |  |  |     +- org.glassfish.jaxb:txw2:jar:4.0.5:runtime
[INFO] |  |  |     \- com.sun.istack:istack-commons-runtime:jar:4.1.2:runtime
[INFO] |  |  +- jakarta.inject:jakarta.inject-api:jar:2.0.1:runtime
[INFO] |  |  \- org.antlr:antlr4-runtime:jar:4.13.0:compile
[INFO] |  +- org.springframework.data:spring-data-jpa:jar:3.2.4:compile
[INFO] |  |  +- org.springframework.data:spring-data-commons:jar:3.2.4:compile
[INFO] |  |  +- org.springframework:spring-orm:jar:6.1.5:compile
[INFO] |  |  +- org.springframework:spring-tx:jar:6.1.5:compile
[INFO] |  |  \- org.springframework:spring-beans:jar:6.1.5:compile
[INFO] |  \- org.springframework:spring-aspects:jar:6.1.5:compile
[INFO] +- com.h2database:h2:jar:2.2.224:runtime
[INFO] +- org.projectlombok:lombok:jar:1.18.30:compile
[INFO] +- org.springframework.boot:spring-boot-starter-test:jar:3.2.4:test
[INFO] |  +- org.springframework.boot:spring-boot-test:jar:3.2.4:test
[INFO] |  +- org.springframework.boot:spring-boot-test-autoconfigure:jar:3.2.4:test
[INFO] |  +- com.jayway.jsonpath:json-path:jar:2.9.0:test
[INFO] |  +- jakarta.xml.bind:jakarta.xml.bind-api:jar:4.0.2:runtime
[INFO] |  |  \- jakarta.activation:jakarta.activation-api:jar:2.1.3:runtime
[INFO] |  +- net.minidev:json-smart:jar:2.5.0:test
[INFO] |  |  \- net.minidev:accessors-smart:jar:2.5.0:test
[INFO] |  |     \- org.ow2.asm:asm:jar:9.3:test
[INFO] |  +- org.assertj:assertj-core:jar:3.24.2:test
[INFO] |  +- org.awaitility:awaitility:jar:4.2.0:test
[INFO] |  +- org.hamcrest:hamcrest:jar:2.2:test
[INFO] |  +- org.junit.jupiter:junit-jupiter:jar:5.10.2:test
[INFO] |  |  +- org.junit.jupiter:junit-jupiter-api:jar:5.10.2:test
[INFO] |  |  |  +- org.opentest4j:opentest4j:jar:1.3.0:test
[INFO] |  |  |  +- org.junit.platform:junit-platform-commons:jar:1.10.2:test
[INFO] |  |  |  \- org.apiguardian:apiguardian-api:jar:1.1.2:test
[INFO] |  |  +- org.junit.jupiter:junit-jupiter-params:jar:5.10.2:test
[INFO] |  |  \- org.junit.jupiter:junit-jupiter-engine:jar:5.10.2:test
[INFO] |  |     \- org.junit.platform:junit-platform-engine:jar:1.10.2:test
[INFO] |  +- org.mockito:mockito-core:jar:5.7.0:test
[INFO] |  |  +- net.bytebuddy:byte-buddy-agent:jar:1.14.12:test
[INFO] |  |  \- org.objenesis:objenesis:jar:3.3:test
[INFO] |  +- org.mockito:mockito-junit-jupiter:jar:5.7.0:test
[INFO] |  +- org.skyscreamer:jsonassert:jar:1.5.1:test
[INFO] |  |  \- com.vaadin.external.google:android-json:jar:0.0.20131108.vaadin1:test
[INFO] |  +- org.springframework:spring-test:jar:6.1.5:test
[INFO] |  \- org.xmlunit:xmlunit-core:jar:2.9.1:test
[INFO] +- org.slf4j:slf4j-api:jar:2.0.12:compile
[INFO] +- ch.qos.logback:logback-classic:jar:1.5.3:compile
[INFO] \- ch.qos.logback:logback-core:jar:1.5.3:compile'''
    parse_dep_gav(dep)