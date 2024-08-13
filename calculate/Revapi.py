## get the newest compatible version according to revapi
import copy
import os
import re
import shutil
import subprocess
import time

import requests
from tqdm import tqdm

from calculate.constants import ADDEDTOINTERFACE_PATH, REVAPI_FOLDER


# from constants import REVAPI_FOLDER
# from constants import ADDEDTOINTERFACE_PATH
class Revapi:
    def __init__(self, gavc:dict, ReachableAPIs:list, AllVersion:list, Pwd:str, JarName:str, DependedBy:list, Omitted:list):
        self.gavc = gavc
        self.api = ReachableAPIs
        self.allVersion = AllVersion
        self.Pwd = Pwd # dep/ folder path
        self.jar_name = JarName
        self.jar = os.path.join(Pwd, JarName) # jar path
        self.new_dep = os.path.join(Pwd, f'new_dep/')
        self.DependedBy = DependedBy
        self.Omitted = Omitted
    # # create dep/new_dep to contain new jar
    # def new_dep_folder(self):
    #     # Check if the folder already exists
    #     if os.path.exists(self.new_dep):
    #         return
    #     # Create the new folder
    #     os.makedirs(self.new_dep)
    
    # return the best version as well as the breaking reason
    # tqdm_log_module_folder: path to tqdm_log/{module_name}/ containing files denoting the progress of each process
    def get_best_version(self, tqdm_log_module_folder: str):
        # self.new_dep_folder()
        idx = self.find_current_version_idx()
        # something wrong,return current version
        # sometimes,a dep is a jar of another module, which cann't be downloaded from maven repo
        # as the result, the AllVersion is empty,so cann't find current version. idx is None
        if idx is None:
            return self.gavc['v'], ''
        length = len(self.allVersion)
        # current_version is the lastest version
        if idx == length - 1:
            dest = os.path.join(self.new_dep, self.jar_name)
            shutil.copy(self.jar, dest)
            return self.gavc['v'], ''
        # current_version is not the lastest version, calculation continue
        best_version = self.gavc['v']
        
        # file to contain tqdm log
        if self.gavc['c'] == '':
            dep_tqdm_log_file = os.path.join(tqdm_log_module_folder, f"{self.gavc['g']}_{self.gavc['a']}_tqdm_log.txt")
        else:
            dep_tqdm_log_file = os.path.join(tqdm_log_module_folder, f"{self.gavc['g']}_{self.gavc['a']}_{self.gavc['c']}_tqdm_log.txt")
        with open(dep_tqdm_log_file, 'a') as f:
            with tqdm(total=length-idx, desc=f'Calculate version', file=f) as pbar:
                # containing the breaking version which is detected by tool as well as the breaking reason
                # contains all breaking version and its breaking reason
                Breaking_Reason_List = []
                # pass all newer version to find the newest and compatible version
                for i in range(idx+1, length):
                    # new_dep_jar is path to the downloaded new jar
                    # ret_txt is new_dep_jar with the suffix '.jar' removed
                    new_dep_jar, ret_txt = self.download_new_dep(self.gavc['g'],self.gavc['a'],self.allVersion[i]['version'], self.gavc['c'])
                    # if new_dep_jar is None, it means that the download of a particular version of the jar failed
                    if new_dep_jar is None:
                        if self.gavc['c'] == '':
                            print(f"=={self.gavc['g']}:{self.gavc['a']}:{self.allVersion[i]['version']} download fails, so skip")
                        else:
                            print(f"=={self.gavc['g']}:{self.gavc['a']}:{self.allVersion[i]['version']}:{self.gavc['c']} download fails, so skip")
                        pbar.update(1)
                        continue
                    # the most important method : determine whether new version is compatible
                    # revapi_ret_txt == {ret_txt}#{current_version}
                    revapi_ret_txt = ret_txt+f"#{self.gavc['v']}"
                    flag, breaking_reason = self.compare(self.jar, new_dep_jar, revapi_ret_txt)
                    # compare current jar with new jar
                    if flag :
                        # no BC for effective_dep
                        # now consider omitted_deps for dependency conflict
                        # pass the omitted dep
                        flag_1 = True
                        for omitted_dep in self.Omitted:
                            flag_1, breaking_reason = self.conflict_resolution(omitted_dep, new_dep_jar, ret_txt)
                            if flag_1 is False:
                                # conflict occured
                                break
                        if flag_1 == False:
                            dependedby = ""
                            for dependant in omitted_dep["DependedBy"]:
                                dependedby = dependedby + f' {dependant}'
                            breaking_reason = f'conflict with {omitted_dep["JarFileName"]} dependedby {dependedby} ### ' + breaking_reason
                            Breaking_Reason = {}
                            # new dep is incompatible, recording the breaking reason
                            Breaking_Reason.update({'breaking_version': self.allVersion[i]['version']})
                            Breaking_Reason.update({'breaking_reason': breaking_reason})
                            Breaking_Reason_List.append(Breaking_Reason)
                        else :
                            best_version = self.allVersion[i]['version']
                    else :
                        Breaking_Reason = {}
                        # new dep is incompatible, recording the breaking reason
                        Breaking_Reason.update({'breaking_version': self.allVersion[i]['version']})
                        Breaking_Reason.update({'breaking_reason': breaking_reason})
                        Breaking_Reason_List.append(Breaking_Reason)
                    pbar.update(1)
                    # test:
                    # self.compare(self.jar, new_dep_jar, ret_txt)
                    # break
        return best_version, Breaking_Reason_List
            
    # conflict-resolution
    # omitted_dep : a dict contain information about an omitted_dep{JarFileName, Version, DependedBy, ReachableAPIs}
    # new_dep_jar : path to new version of jar
    # ret_txt : "#{version_of_omitted_dep}" to be added
    def conflict_resolution(self, omitted_dep:dict, new_dep_jar:str, ret_txt:str):
        # compare new jar with omitted_dep jar, so need to change some member variable to use compare method
        # self.api should be changed into reachable api of this omitted_dep
        # self.DependedBy should be changed into DependedBy of this omitted_dep
        # record the variable in advance to reduce afterwards
        reachable_api = copy.deepcopy(self.api)
        DependedBy = copy.deepcopy(self.DependedBy)
        revapi_ret_txt =ret_txt+f'#{omitted_dep["Version"]}'
        
        self.api = omitted_dep["ReachableAPIs"]
        omitted_dep_jar_path = os.path.join(self.Pwd, omitted_dep["JarFileName"])
        self.DependedBy = omitted_dep["DependedBy"]
        
        flag, breaking_reason = self.compare(omitted_dep_jar_path, new_dep_jar, revapi_ret_txt)
        
        # reduction
        self.api = reachable_api
        self.DependedBy = DependedBy
        return flag, breaking_reason
        
    # return the idx of current version in allversion
    def find_current_version_idx(self):
        for idx in range(0, len(self.allVersion)):
            if self.allVersion[idx]['version'] == self.gavc['v']:
                return idx
        
    # download a jar according to its gav in dep/new_dep
    def download_new_dep(self, group_id, artifact_id, version, classifier):
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
        # response = requests.get(jar_url)
        try:
            response = handle_error_get(jar_url)
            # Proceed if the download was successful
            if response.status_code == 200:
                if classifier == '':
                    file_name = f"{group_id}-{artifact_id}-{version}.jar"
                else:
                    file_name = f"{group_id}-{artifact_id}-{version}-{classifier}.jar"
                with open(os.path.join(self.new_dep,file_name), "wb") as jar_file:
                    jar_file.write(response.content)
                if classifier == '':
                    print(f"start analysising dependency {group_id}-{artifact_id}-{version}.jar ")
                else :
                    print(f"start analysising dependency {group_id}-{artifact_id}-{version}-{classifier}.jar ")
                # the second return value is part of the name of file containing revapi result
                # it's just file_name without '.jar'
                return os.path.join(self.new_dep,file_name), os.path.join(self.new_dep,f"{file_name.removesuffix('.jar')}")
        except Exception as e:
            if classifier == '':
                print(f"Failed to download {group_id}-{artifact_id}-{version}.jar from central repository; Reason: {str(e)}")
            else:
                print(f"Failed to download {group_id}-{artifact_id}-{version}-{classifier}.jar from central repository; Reason: {str(e)}")
            # return None, None , means that jar cannot not be downloaded
            return None, None
    # compare old jar and new jar
    # return value: True : no BC ; False : has BC
    # return value: breaking reason
    def compare(self, old_jar, new_jar, ret_txt_path):
        sh_path = os.path.join(REVAPI_FOLDER, "revapi.sh")
        command = f'''{sh_path} --extensions=org.revapi:revapi-java:0.28.1,org.revapi:revapi-reporter-text:0.15.0 --old={old_jar} --new={new_jar} -D revapi.reporter.text.minSeverity=BREAKING > {ret_txt_path}'''
        if os.path.exists(ret_txt_path) is False:
            os.system(command)
        # parse ret_txt and handle some corner case
        flag, records = self.parse_ret(ret_txt_path)
        if flag is False:
            # this records is broken because corner case like java.method.addedToInterface / reference BC
            # now, the records is the breaking reason rather than the records in revapi result
            return False, records
        # test
        # print("test\n",records)
        
        # match records with ReachableAPIs
        # # test
        # print("records",records)
        
        # for record in records:
        for record in records:
            # # old: is followed by <none>, has BC
            # if record is None:
            #     return False
        
            # skip None, as None is the reture value of some corner cases(not breaking), which is not handled by reachable API
            # like java.method.addedToInterface / reference BC
            if record is None:
                continue
            for API in self.api:
                new_api = API.replace('$','.')
                # new_api : replace '$' with '.' in ReachAPIs
                if new_api.startswith(record):
                    # new_api is breaking
                    return False, f"breaking api: {API} <<<<< transformed old api of breaking record: {record}"
        # True means compatible, so breaking_reason is ''
        return True, ''
        
    # parse the ret.txt
    # return the flag, filtered_records
    # if flag == True, use filtered_records containing breaking api to match the reachable api
    # if flag == False, then the version is breaking, filtered_records is breaking_reason
    # flag == False denotes the corner case breaks which cann't be handled by reachableAPI, like java.method.addedToInterface
    def parse_ret(self, ret_path):
        with open(ret_path, 'r') as f:
            content = f.read()
        new_jar_pattern = r"New API: (.*?)\n"
        new_jar = (re.search(new_jar_pattern, content)).group(1)
        # filtered_records = self.filter_record(content)
        filtered_records = self.filter_record(content)
        for i in range(len(filtered_records)):
            # get the content after "old: "
            # # test
            # print("before: ", filtered_records[i])
            
            # handle java.method.addedToInterface
            if "java.method.addedToInterface" in filtered_records[i] :
                print(f"== java.method.addedToInterface in {new_jar} ==")
                flag, breaking_reason = self.java_method_addedToInterface(filtered_records[i], new_jar)
                if flag == False:
                    # breaking_reason: which api implements a breaking interface
                    return False, breaking_reason
                # java.method.addedToInterface doesn't break
                # set filter_records[i] as None, compare will skip None
                filtered_records[i] = None
                continue
            
            # # handle reference BC, which means class BC
            if "old: class" in filtered_records[i]:
                print(f"== class BC in {new_jar} ==")
                flag, breaking_reason = self.reference_bc(filtered_records[i], new_jar)
                if flag == False:
                    # breaking_reason: which type breaks the reference used by a jar
                    return False, breaking_reason
                filtered_records[i] = None
                continue
            
            
            # using reachable API
            pattern = r'old: (.+?)\n'
            match = re.search(pattern, filtered_records[i])
            filtered_records[i] = self.transform(match.group(1))
            
            # # test
            # print("after: ",filtered_records[i])
            
        # return filtered_records
        return True, filtered_records

    
    # get the records whose SORUCE is BREAKING
    def filter_record(self, content):
        pattern = r"old: .+?^$"
        # pattern = r"old: .+?$"
        all_records = re.findall(pattern, content, flags=re.DOTALL | re.MULTILINE)
        
        # # test
        # print("all records:\n", all_records)
        
        filtered_records = []
        for record in all_records:
            if "SOURCE: BREAKING" in record:
                filtered_records.append(record)
        # # test
        # print("select source breaking:\n", filtered_records)
        return filtered_records
    
    # transform a record into the format which is comparable with BCEL api writing(return value)
    def transform(self, revapi_format_api:str):
        # remove <.*> excluding <init> or <clinit>
        pattern1 = r'<.*?>'
        
        def remove_tags(match):
            # If the matched string is '<init>' or '<clinit>', return it as is.
            if match.group(0) == '<init>' or match.group(0) == '<clinit>':
                return match.group(0)
            # Otherwise, return an empty string to "delete" the <>.
            return ''
        
        text = re.sub(pattern1, remove_tags, revapi_format_api)
        # text = revapi_format_api
        # method
        if text.startswith("method"):
            pattern2 = r'method (.+?) (.*?)::(.*?)\((.*?)\)'
            match = re.search(pattern2, text)
            return_type = match.group(1)
            # process generics for return value
            if return_type == ' T':
                return_type = 'java.lang.Object'
            elif return_type == ' T[]':
                return_type == 'java.lang.Object[]'
            elif return_type == 'E':
                return_type = 'java.lang.Object'
            
            class_name = match.group(2)
            method_name = match.group(3)
            parameters = match.group(4).replace(' ','')
            # # test
            # print("text\n", text)
        
            api = f"{class_name}: {return_type} {method_name}({parameters})"
            return api

        # parameter
        if text.startswith("parameter"):
            pattern3 = r'parameter (.+?) (.*?)::(.*?)\((.*?)\)'
            match = re.search(pattern3, text)
            return_type = match.group(1)
            # process generics for return value
            if return_type == ' T':
                return_type = 'java.lang.Object'
            elif return_type == ' T[]':
                return_type == 'java.lang.Object[]'
            elif return_type == 'E':
                return_type = 'java.lang.Object'
            
            class_name = match.group(2)
            method_name = match.group(3)
            parameters = match.group(4).replace(' ','').replace('===','')
            api = f"{class_name}: {return_type} {method_name}({parameters})"
            return api
        
        # class/interface/enum
        if text.startswith("class") or text.startswith("interface") or text.startswith("enum"):
            pattern4 = r' (.+?)$'
            match = re.search(pattern4, text)
            name = match.group(1)
            api = f"{name}:"
            return api
        
        # field
        if text.startswith("field"):
            pattern5 = r'field (.*)\..*?$'
            match = re.search(pattern5, text)
            class_name = match.group(1)
            api = f"{class_name}:"
            return api
    
    # handle java.method.addedToInterface
    # record contains "java.method.addedToInterface"
    # new_jar: the name of the new version dep jar
    # check whether any class implements the interface
    # exist : return False; non-exist : return True
    def java_method_addedToInterface(self, record:str, new_jar:str):
        # remove all substring containing '<' and '>'
        # eg: 
        # new: method void com.google.common.collect.RangeMap<K extends java.lang.Comparable, V>::putCoalescing(com.google.common.collect.Range<K>, V)
        # -> new: method void com.google.common.collect.RangeMap::putCoalescing(com.google.common.collect.Range, V)
        # surplus_substring_pattern = r'<.*?>'
        def remove_surplus_substring(input_string:str):
            result = []
            bracket_depth = 0
            for char in input_string:
                if char == '<':
                    bracket_depth += 1
                elif char == '>':
                    if bracket_depth > 0:
                        bracket_depth -= 1
                    continue 
                elif bracket_depth == 0:
                    result.append(char)
            return ''.join(result)
        # record = re.sub(surplus_substring_pattern, remove_surplus_substring, record)
        record = remove_surplus_substring(record)
        # get the interface, in new:
        # note : ignore inner interface($) now
        # pattern = r"new: method .*? (.*?)::.*?\n"
        pattern = r"new: method .* (.*?)::.*?\n"
        match = re.search(pattern, record)
        interface = match.group(1)
        print(f"  changed interface in {new_jar}: {interface}")
        # # test
        # print(f"{interface}")
        # use common BCEL to check whether any class implements interface
        # file to store the ret
        log_ret = os.path.join(self.Pwd, f'new_dep/{new_jar}.java_method_addedToInterface.txt')
        # travel class in client jar 
        client_folder = os.path.join(self.Pwd, '../client/')
        contents = os.listdir(client_folder)
        for item in contents:
            if item != self.jar_name and item.endswith(".jar"):
                jar_path = os.path.join(client_folder, item)
                # command = f"java -jar {ADDEDTOINTERFACE_PATH} {jar_path} {interface} >{log_ret}"
                # os.system(command)
                # use run rather than os.system to redirect the output, as the redirection works well when executing the python using 'script -q -c' rather than exeucting directly
                with open(log_ret, 'w') as f:
                    subprocess.run(['java', '-jar', f'{ADDEDTOINTERFACE_PATH}', f'{jar_path}', f'{interface}'], stdout=f)
                # # test
                # print(f"{item} analysised")
                with open(log_ret, 'r') as f:
                    log = f.read()
                    if "implements" in log:
                        # client jar has the class
                        print(f"java.method.addedToInterface: {interface} breaks {item}")
                        return False, f"java.method.addedToInterface: {interface} breaks {item}"
        # travel the dep jars which dependend on self.jar_name
        contents = os.listdir(self.Pwd)
        for item in self.DependedBy:
            # if item != self.jar_name and item.endswith(".jar"):
            # just consider the dependencies which depend on this dep
            jar_path = os.path.join(self.Pwd, item)
            # command = f"java -jar {ADDEDTOINTERFACE_PATH} {jar_path} {interface} >{log_ret}"
            # os.system(command)
            with open(log_ret, 'w') as f:
                subprocess.run(['java', '-jar', f'{ADDEDTOINTERFACE_PATH}', f'{jar_path}', f'{interface}'], stdout=f)
            # # test
            # print(f"{item} analysised")
            with open(log_ret, 'r') as f:
                log = f.read()
                if "implements" in log:
                    # client jar has the class
                    print(f"java.method.addedToInterface: {interface} breaks {item}")
                    return False, f"java.method.addedToInterface: {interface} breaks {item}"
        # no non-abstract class implements the interface
        # remove the log_ret, as it is empty
        os.remove(log_ret)
        return True, ''
    
    # handle reference BC
    # record containing class BC
    # record: a BC detected by revapi containing class BC("old: class")
    # compare the class of record with the references in the jar related to new_jar
    def reference_bc(self, record:str, new_jar:str):
        # extract class/reference_type
        pattern = r"old: class (.*)\n"
        match = re.search(pattern, record)
        reference_type = match.group(1)
        
        # compare reference_type with reference used by client jar
        client_folder = os.path.join(self.Pwd, '../client/')
        contents = os.listdir(client_folder)
        for item in contents:
            if item.endswith('.jar'):
                jar_path = os.path.join(client_folder, item)
                reference_file_path = jar_path+'_ref.txt'
                with open(reference_file_path, 'r') as f:
                    # references = f.read()
                    for line in f:
                        method, class_type = line.split(' ==> ')
                        if reference_type+'/' in class_type:
                            # the type of reference used by client breaks in new version
                            return False, f"reference broken: {reference_type} breaks {item}/{method}"
        
        # compare reference_type with reference used by dep jars which dependend on self.jar_name
        contents = os.listdir(self.Pwd)
        for item in self.DependedBy:    
            jar_path = os.path.join(self.Pwd, item)
            reference_file_path = jar_path+'_ref.txt'
            with open(reference_file_path, 'r') as f:
                    # references = f.read()
                    for line in f:
                        method, class_type = line.split(' ==> ')
                        if reference_type+'/' in class_type:
                            # the type of reference used by a dep breaks in new version
                            return False, f"reference broken: {reference_type} breaks {item}/{method}"
        
        return True, ''
    
        
    
if __name__ == "__main__":
    REVAPI_FOLDER = "/home/ray/Work/Tool/Tool/utils/revapi-0.12.0"
    ADDEDTOINTERFACE_PATH = "/home/ray/Work/Tool/Tool/utils/BCEL_method_addedToInterface-1.0-SNAPSHOT-jar-with-dependencies.jar"
    test_dep = Revapi({},[],[],'/home/ray/Work/Tool/Tool/data/Jar/server_/dep','config-1.2.1.jar')
#     record = '''old: <none>
# new: method <T extends java.lang.Enum<T>> T com.typesafe.config.Config::getEnum(java.lang.Class<T>, java.lang.String)
# java.method.addedToInterface: Method was added to an interface.
# SEMANTIC: POTENTIALLY_BREAKING, BINARY: NON_BREAKING, SOURCE: BREAKING'''
    record = '''old: <none>
new: method java.util.List<java.time.Duration> com.typesafe.config.Config::getDurationList(java.lang.String)
java.method.addedToInterface: Method was added to an interface.
BINARY: NON_BREAKING, SOURCE: BREAKING, SEMANTIC: POTENTIALLY_BREAKING'''
    test_dep.java_method_addedToInterface(record)