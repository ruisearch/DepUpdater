"""all operation on Revapi tool"""
import os
import re
import subprocess
from constants import REVAPI_SH_PATH
from database.query import query_revapi_report, store_revapi_report,\
    query_bc_api, store_binary_bc_api, store_source_bc_api
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
        
    def bc_api(self, groupId:str, artifactId:str, old_version:str, new_version:str, binary_or_source:str):
        """main method of this file, get the bc api in the format of dict
        Args:
            binary_or_source (str): 'binary' or 'source' to distinguish the type of the bc api
        """
        if binary_or_source == 'binary':
            binary_bc_method, binary_bc_type, _, _ = query_bc_api(groupId, artifactId, old_version, new_version)
            if binary_bc_method and binary_bc_type:
                # bc api exists in the database
                return binary_bc_method, binary_bc_type
            # bc api not exists in the database
            report = self.compare(groupId, artifactId, old_version, new_version)
            self.extract_bc_records(report)
            for record in self.binary_bc_records:
                self.extract_bc_api(record, 'binary')
            store_binary_bc_api(groupId, artifactId, old_version, new_version, self.binary_bc_method, self.binary_bc_type)
            return self.binary_bc_method, self.binary_bc_type
        elif binary_or_source == 'source':
            _, _, source_bc_method, source_bc_type = query_bc_api(groupId, artifactId, old_version, new_version)
            if source_bc_method and source_bc_type:
                # bc api exists in the database
                return source_bc_method, source_bc_type
            # bc api not exists in the database
            report = self.compare(groupId, artifactId, old_version, new_version)
            self.extract_bc_records(report)
            for record in self.source_bc_records:
                self.extract_bc_api(record, 'source')
            store_source_bc_api(groupId, artifactId, old_version, new_version, self.source_bc_method, self.source_bc_type)
            return self.source_bc_method, self.source_bc_type
        else:
            raise ValueError('binary_or_source should be binary or source')

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
            bc_type.setdefault(api, []).append(record)
        else:
            api_pattern = r"old: (.+?) (.+?)\n"
            match = re.search(api_pattern, record)
            api_type = match.group(1)
            api = match.group(2)
            if api_type == 'class' or api_type == 'interface' \
                or api_type == 'enum' or api_type == '@interface':
                # api is the bc type
                api = self.transform_type(api)
                bc_type.setdefault(api, []).append(record)
            elif api_type == 'field':
                # api is the filed of a the bc type
                # remove inherited class
                if ' @' in api:
                    api = api[:api.find(' @')]
                # restore it to the type, means ignore the last . and the field name
                api = api[:api.rfind('.')]
                api = self.transform_type(api)
                bc_type.setdefault(api, []).append(record)
            elif api_type == 'method':
                # remove inherited class
                if ' @' in api:
                    api = api[:api.find(' @')]
                # remove throws
                if ' throws ' in api:
                    api = api[:api.find(' throws ')]
                api = self.transform_method(api)
                bc_method.setdefault(api, []).append(record)
            elif api_type == 'parameter':
                # remove inherited class
                if ' @' in api:
                    api = api[:api.find(' @')]
                # remove === === in the ParameterType
                api = api.replace('===', '')
                api = self.transform_method(api)
                bc_method.setdefault(api, []).append(record)

    @staticmethod
    def transform_type(_type:str):
        """transform the type to the format in the type dependency graph
        remove <> to disregard generic
        """
        _type = Revapi.remove_angle_brackets(_type)
        return _type

    @staticmethod
    def transform_method(method:str):
        """transform the method to the format in the call graph
        1. change a generic type to its upper bound
        2. remove <> to disregard generic
        """
        # handle generic type defined in the class
        class_generic_type_pattern = r'(<[^<>]*>)::'
        class_generic_match = re.search(class_generic_type_pattern, method)
        if class_generic_match:
            # generic type exists in the class
            class_generic_declaration = class_generic_match.group(1)
            letter, upper_bound = Revapi.handle_generic_declaration(class_generic_declaration)
            method = Revapi.replace_letter_with_upper_bound(method, letter, upper_bound)
        # # handle generic type defined in the method
        method_generic_type_pattern = r'^(<.*?>)'
        method_generic_match = re.search(method_generic_type_pattern, method)
        if method_generic_match:
            # generic type exists in the method
            method_generic_declaration = method_generic_match.group(1)
            letter, upper_bound = Revapi.handle_generic_declaration(method_generic_declaration)
            method = Revapi.replace_letter_with_upper_bound(method, letter, upper_bound)
        # remove <> to disregard generic
        method = Revapi.remove_angle_brackets(method).strip()
        return method

    @staticmethod
    def handle_generic_declaration(generic_declaration:str):
        """handle the generic type
        Args:
            generic_declaration (str): the generic declaration, like <S extends java.lang.annotation.Annotation>
        Returns:
            generic_letter (str): the letter representing generic type, like S
            generic_type (str): the upper bound of the generic type, like java.lang.annotation.Annotation
        """
        if ' extends ' in generic_declaration:
            # upper bound is defined after 'extends'
            generic_letter = generic_declaration[generic_declaration.find('<')+1:generic_declaration.find(' extends ')]
            generic_type = generic_declaration[generic_declaration.find(' extends ')+9: generic_declaration.rfind('>')]
            return generic_letter, generic_type
        # upper bound is java.lang.Object
        generic_letter = generic_declaration[generic_declaration.find('<')+1:generic_declaration.rfind('>')]
        return generic_letter, 'java.lang.Object'

    @staticmethod
    def replace_letter_with_upper_bound(method:str, generic_letter:str, upper_bound:str):
        """replace the generic letter with its upper bound
        in parameter, return type"""
        letter_pattern = r'\b' + generic_letter + r'\b'
        return re.sub(letter_pattern, upper_bound, method)

    @staticmethod
    def remove_angle_brackets(text:str):
        """remove <> in the text"""
        while re.search(r'<[^<>]*>', text):
            text = re.sub(r'<[^<>]*>', '', text)
        return text

if __name__ == '__main__':
    from constants import MainProcess_pwd
    old_jar = os.path.join(MainProcess_pwd, 'test', 'byte-buddy-1.12.19.jar')
    new_jar = os.path.join(MainProcess_pwd, 'test', 'byte-buddy-1.14.13.jar')
    revapi = Revapi(old_jar, new_jar)
    # report = revapi.compare('net.bytebuddy', 'byte-buddy', '1.12.19', '1.14.13')
    
    # # test extract_bc_api
    # revapi.extract_bc_records(report)
    # for record in revapi.source_bc_records:
    #     revapi.extract_bc_api(record, 'source')
    # for record in revapi.binary_bc_records:
    #     revapi.extract_bc_api(record, 'binary')
    # print(revapi.source_bc_type)
    # print(revapi.source_bc_method)
    # print(revapi.binary_bc_method)
    # print(revapi.binary_bc_type)
    
    # # # test transform_method
    # # test_method = '<S extends java.lang.annotation.Annotation> net.bytebuddy.asm.Advice.OffsetMapping.Factory<S> net.bytebuddy.asm.Advice.OffsetMapping.ForSerializedValue.Factory<T extends java.lang.annotation.Annotation>::of(java.lang.Class<S>, java.io.Serializable, java.lang.Class<?>)'
    # # test_method = '<T> T test.soot.CG.Cg_Main::test_generic(T)'
    # test_method = '<T extends org.test> T org.test.A<T extends org.class.test>::test(T, lang.String)'
    # print(Revapi.transform_method(test_method))
    
    # test bc_api
    binary_bc_method, binary_bc_type = revapi.bc_api('net.bytebuddy', 'byte-buddy', '1.12.19', '1.14.13', 'binary')
    source_bc_method, source_bc_type = revapi.bc_api('net.bytebuddy', 'byte-buddy', '1.12.19', '1.14.13', 'source')
    print(source_bc_method)