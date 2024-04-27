## get the newest compatible version according to revapi
import os
import shutil
import re
import requests
from calculate.constants import REVAPI_FOLDER
from calculate.constants import ADDEDTOINTERFACE_PATH
class Revapi:
    def __init__(self, gav:dict, ReachableAPIs:list, AllVersion:list, Pwd:str, JarName:str):
        self.gav = gav
        self.api = ReachableAPIs
        self.allVersion = AllVersion
        self.Pwd = Pwd # dep/ folder path
        self.jar_name = JarName
        self.jar = os.path.join(Pwd, JarName) # jar path
        self.new_dep = os.path.join(Pwd, f'new_dep/')
    # create dep/new_dep to contain new jar
    def new_dep_folder(self):
        # Check if the folder already exists
        if os.path.exists(self.new_dep):
            return
        # Create the new folder
        os.makedirs(self.new_dep)
    
    # return the best version
    def get_best_version(self):
        self.new_dep_folder()
        idx = self.find_current_version_idx()
        length = len(self.allVersion)
        # current_version is the lastest version
        if idx == length - 1:
            dest = os.path.join(self.new_dep, self.jar_name)
            shutil.copy(self.jar, dest)
            return self.gav['v']
        best_version = self.gav['v']
        for i in range(idx+1, length):
            new_dep_jar, ret_txt = self.download_new_dep(self.gav['g'],self.gav['a'],self.allVersion[i]['version'])
            # compare current jar with new jar
            if self.compare(self.jar, new_dep_jar, ret_txt):
                # no BC
                best_version = self.allVersion[i]['version']
            else :
            # new dep is incompatible, break
                break
            # test:
            # self.compare(self.jar, new_dep_jar, ret_txt)
            # break
        return best_version
            
    # return the idx of current version in allversion
    def find_current_version_idx(self):
        for idx in range(0, len(self.allVersion)):
            if self.allVersion[idx]['version'] == self.gav['v']:
                return idx
        
    # download a jar according to its gav in dep/new_dep
    def download_new_dep(self, group_id, artifact_id, version):
        jar_url = f"https://repo1.maven.org/maven2/{group_id.replace('.', '/')}/{artifact_id}/{version}/{artifact_id}-{version}.jar"
        response = requests.get(jar_url)
        if response.status_code == 200:
            file_name = f"{artifact_id}-{version}.jar"
            with open(os.path.join(self.new_dep,file_name), "wb") as jar_file:
                jar_file.write(response.content)
            print(f"Analysis dependency {artifact_id}-{version}.jar ...")
            return os.path.join(self.new_dep,file_name), os.path.join(self.new_dep,f"{file_name}.ret.txt")
        else:
            print(f"Failed to download dependency {artifact_id}-{version}.jar. Reason: {response.reason}")
    # compare old jar and new jar
    # True : no BC ; False : has BC
    def compare(self, old_jar, new_jar, ret_txt_path):
        sh_path = os.path.join(REVAPI_FOLDER, "revapi.sh")
        command = f'''{sh_path} --extensions=org.revapi:revapi-java:0.28.1,org.revapi:revapi-reporter-text:0.15.0 --old={old_jar} --new={new_jar} -D revapi.reporter.text.minSeverity=BREAKING > {ret_txt_path}'''
        os.system(command)
        flag, records = self.parse_ret(ret_txt_path)
        if flag is False:
            return False
        # test
        # print("test\n",records)
        
        # match records with ReachableAPIs
        # # test
        # print("records",records)
        
        for record in records:
            # # old: is followed by <none>, has BC
            # if record is None:
            #     return False
            for API in self.api:
                new_api = API.replace('$','.')
                # new_api : replace '$' with '.' in ReachAPIs
                if new_api.startswith(record):
                    # new_api is breaking
                    return False
        return True
        
    # parse the ret.txt
    # return the flag, filtered_records
    # if flag == True, use filtered_records containing breaing api to match the reachable api
    # if flag == False, then the version is breaking, so filtered_records is useless
    # flag == False is used to handle the corner case which cann't be handled by reachableAPI, like java.method.addedToInterface
    def parse_ret(self, ret_path):
        with open(ret_path, 'r') as f:
            content = f.read()
        # filtered_records = self.filter_record(content)
        filtered_records = self.filter_record(content)
        for i in range(len(filtered_records)):
            # get the content after "old: "
            # # test
            # print("before: ", filtered_records[i])
            
            # handle java.method.addedToInterface
            if "java.method.addedToInterface" in filtered_records[i] :
                print("java.method.addedToInterface")
                flag = self.java_method_addedToInterface(filtered_records[i])
                if flag == False:
                    return False, []
                # java.method.addedToInterface doesn't break
                # '.' couldn't be the prefix of the api
                filtered_records[i] = "."
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
    # check whether any class implements the interface
    # exist : return False; non-exist : return True
    def java_method_addedToInterface(self, record:str):
        # get the interface, in new:
        # note : ignore inner interface($) now
        pattern = r"new: method .*? (.*?)::.*?\n"
        match = re.search(pattern, record)
        interface = match.group(1)
        # use common BCEL to check whether any class implements interface
        # file to store the ret
        log_ret = os.path.join(self.Pwd, 'java_method_addedToInterface.txt')
        # travel class in client jar 
        client_folder = os.path.join(self.Pwd, '../client/')
        contents = os.listdir(client_folder)
        for item in contents:
            if item != self.jar_name and item.endswith(".jar"):
                jar_path = os.path.join(client_folder, item)
                command = f"java -jar {ADDEDTOINTERFACE_PATH} {jar_path} {interface} >{log_ret}"
                os.system(command)
                # # test
                # print(f"{item} analysised")
                with open(log_ret, 'r') as f:
                    log = f.read()
                    if "implements" in log:
                        # client jar has the class
                        print(f"java.method.addedToInterface breaks {item}")
                        return False
        # travel all dep jar(excluding self.jar_name)
        contents = os.listdir(self.Pwd)
        for item in contents:
            if item != self.jar_name and item.endswith(".jar"):
                jar_path = os.path.join(self.Pwd, item)
                command = f"java -jar {ADDEDTOINTERFACE_PATH} {jar_path} {interface} >{log_ret}"
                os.system(command)
                # # test
                # print(f"{item} analysised")
                with open(log_ret, 'r') as f:
                    log = f.read()
                    if "implements" in log:
                        # dep jar has the class
                        print(f"java.method.addedToInterface breaks {item}")
                        return False
        return True