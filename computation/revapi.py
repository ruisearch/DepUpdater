"""all operation on Revapi tool"""
import os
import re
import subprocess
from constants import REVAPI_SH_PATH
from database.query import query_revapi_report, store_revapi_report
class Revapi:
    """Revapi tool class"""

    def __init__(self, old_jar:str, new_jar:str):
        """
        Args:
            old_jar (str): the path to the old jar file
            new_jar (str): the path to the new jar file
        """
        self.old_jar = old_jar
        self.new_jar = new_jar
        # two list following are the BC records in Revapi report
        # the content are got from extract_bc_records method
        self.binary_bc_records = []
        self.source_bc_records = []
        # four dict following are bc_api -> bc_record
        # the content are got from extract_bc_api method
        self.binary_bc_method = {}
        self.binary_bc_type = {}
        self.source_bc_method = {}
        self.source_bc_type = {}

    def compare(self, groupId:str, artifactId:str, old_version:str, new_version:str):
        """get the compatibility report between two jar files\n
        query sqlite first. if not exist, run revapi to get and store the report in sqlite
        """
        print(f'Comparing {groupId}:{artifactId}:{old_version} -> {groupId}:{artifactId}:{new_version}')
        report = query_revapi_report(groupId, artifactId, old_version, new_version)
        if report:
            # report exists in the database
            # print('Report exists in the database')
            return report
        report = self.run()
        # store report in sqlite
        store_revapi_report(groupId, artifactId, old_version, new_version, report)
        return report

    def run(self):
        """run revapi to get the compatibility report"""
        command = command = f'''{REVAPI_SH_PATH} --extensions=org.revapi:revapi-java:0.28.1,org.revapi:revapi-reporter-text:0.15.0 --old={self.old_jar} --new={self.new_jar} -D revapi.reporter.text.minSeverity=BREAKING'''
        result = subprocess.run(command, shell=True, text=True, capture_output=True)
        return result.stdout

    def extract_bc_records(self, report:str):
        """extract the binary and source breaking change records from the report
        and store them in self.binary_bc_records and self.source_bc_records respectively
        """
        record_pattern = r"old: .*?(?=\n\n)"
        records = re.findall(record_pattern, report, re.DOTALL)
        for record in records:
            if 'BINARY: BREAKING' in record:
                self.binary_bc_records.append(record)
            if 'SOURCE: BREAKING' in record:
                self.source_bc_records.append(record)

    def extract_bc_api(self, record:str, binary_or_source:str):
        """extract the BC api from a Revapi record
        Args:
            record (str): a bc record from Revapi report
            binary_or_source (str): 'binary' or 'source' to distinguish the type of the bc record
        """
        if binary_or_source == 'binary':
            bc_method = self.binary_bc_method
            bc_type = self.binary_bc_type
        elif binary_or_source == 'source':
            bc_method = self.source_bc_method
            bc_type = self.source_bc_type
        else:
            raise ValueError('binary_or_source should be binary or source')
        if 'old: <none>' in record:
            # old api is None, so extract the type from new api
            api_pattern = r"new: .+? .+? (.+?)::.+?\n"
            match = re.search(api_pattern, record)
            api = match.group(1)
            api = self.transform_type(api)
            bc_type.setdefault(api, set()).add(record)
        else:
            api_pattern = r"old: (.+?) (.+?)\n"
            match = re.search(api_pattern, record)
            api_type = match.group(1)
            api = match.group(2)
            if api_type == 'class' or api_type == 'interface' \
                or api_type == 'enum':
                # api is the bc type
                api = self.transform_type(api)
                bc_type.setdefault(api, set()).add(record)
            elif api_type == 'field':
                # api is the filed of a the bc type
                # remove inherited class
                if ' @' in api:
                    api = api[:api.find(' @')]
                # restore it to the type, means ignore the last . and the field name
                api = api[:api.rfind('.')]
                api = self.transform_type(api)
                bc_type.setdefault(api, set()).add(record)
            elif api_type == 'method':
                # remove inherited class
                if ' @' in api:
                    api = api[:api.find(' @')]
                # remove throws
                if ' throws ' in api:
                    api = api[:api.find(' throws ')]
                api = self.transform_method(api)
                bc_method.setdefault(api, set()).add(record)
            elif api_type == 'parameter':
                # remove inherited class
                if ' @' in api:
                    api = api[:api.find(' @')]
                # remove === === in the ParameterType
                api = api.replace('===', '')
                api = self.transform_method(api)
                bc_method.setdefault(api, set()).add(record)

    def transform_type(self, _type:str):
        """transform the type to the format in the type dependency graph"""
        return _type
    
    def transform_method(self, method:str):
        """transform the method to the format in the call graph"""
        return method
    
    def extract_source_breaking_methods(self, report:str):
        """extract the source breaking methods from the report"""
        source_breaking_methods = []
        lines = report.split('\n')
        for i, line in enumerate(lines):
            if re.match(r'^\s+source\s+breaking\s+changes\s*$', line):
                # print('source breaking changes')
                j = i + 2
                while not re.match(r'^\s+binary\s+breaking\s+changes\s*$', lines[j]):
                    if re.match(r'^\s+.*$', lines[j]):
                        source_breaking_methods.append(lines[j].strip())
                    j += 1
                break
        return source_breaking_methods
    
if __name__ == '__main__':
    from constants import MainProcess_pwd
    old_jar = os.path.join(MainProcess_pwd, 'test', 'byte-buddy-1.12.19.jar')
    new_jar = os.path.join(MainProcess_pwd, 'test', 'byte-buddy-1.14.13.jar')
    revapi = Revapi(old_jar, new_jar)
    report = revapi.compare('net.bytebuddy', 'byte-buddy', '1.12.19', '1.14.13')
    
    # test extract_bc_api
    revapi.extract_bc_records(report)
    for record in revapi.source_bc_records:
        revapi.extract_bc_api(record, 'source')
    for record in revapi.binary_bc_records:
        revapi.extract_bc_api(record, 'binary')
    print(revapi.source_bc_type)
    print(revapi.source_bc_method)
    print(revapi.binary_bc_method)
    print(revapi.binary_bc_type)