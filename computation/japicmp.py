"""use japicmp to check the binary compatibility of one version"""
import subprocess
from constants import JAPICMP_PATH
from database.query import query_japicmp_bc_api, query_japicmp_report,\
    store_japicmp_report, store_japicmp_bc_api

class Japicmp:
    """japicmp tool class"""
    
    def __init__(self, old_jar:str, new_jar:str):
        """
        Args:
            old_jar (str): the path to the old jar file
            new_jar (str): the path to the new jar file
        """
        self.old_jar = old_jar
        self.new_jar = new_jar
        # the list following are the bin BC records in Japicmp report
        # the content are got from extract_bc_records method
        self.binary_bc_records = []
        # four dict following are bc_api -> bc_record
        # the content are got from extract_bc_api method
        self.binary_bc_method = {}
        self.binary_bc_type = {}

    def client_impacting_bin_bc_api(self, groupId: str, artifactId: str, oldVersion: str, newVersion: str, method_entry_points:list, type_entry_points:list):
        """main method: get the client impacting binary bc api in the format of dict"""
        # like version_compatibility_checker in computation.py, interact bc_method/bc_type with method_entry_points/type_entry_points
        # to be implemented
        pass

    def bc_api(self, groupId: str, artifactId: str, oldVersion: str, newVersion: str):
        """get the bin bc api in the format of dict"""
        # command to check the binary compatibility between two jars
        binary_bc_method, binary_bc_type = query_japicmp_bc_api(groupId, artifactId, oldVersion, newVersion)
        if binary_bc_method is not None \
            and binary_bc_type is not None:
            # bin bc api exists in the database
            return binary_bc_method, binary_bc_type
        # bin bc api not exists in the database
        report = self.compare(groupId, artifactId, oldVersion, newVersion)
        self.extract_bc_records(report)
        for record in self.binary_bc_records:
            # extract the bc api from the bc records
            self.extract_bc_api(record)
        store_japicmp_bc_api(groupId, artifactId, oldVersion, newVersion, self.binary_bc_method, self.binary_bc_type)
        return self.binary_bc_method, self.binary_bc_type

    def compare(self, groupId:str, artifactId:str, old_version:str, new_version:str):
        """get the binary compatibility report of two jar files
        query sqlite first, if not exists, use japicmp to get and store the report in sqlite
        """
        # print(f'Comparing {groupId}:{artifactId}:{old_version} -> {groupId}:{artifactId}:{new_version}')
        report = query_japicmp_report(groupId, artifactId, old_version, new_version)
        if report:
            # report exists in the database
            return report
        report = self.run()
        # store the report in the database
        store_japicmp_report(groupId, artifactId, old_version, new_version, report)
        return report

    def run(self):
        """run Japicmp to get the binary report"""
        command = f'java -jar {JAPICMP_PATH} --ignore-missing-classes --only-modified -b -n {self.new_jar} -o {self.old_jar}'
        result = subprocess.run(command, shell=True, text=True, capture_output=True)
        return result.stdout
    
    def extract_bc_records(self, report:str):
        """extract the binary bc records from the report
        and store then in self.binary_bc_records
        """
        # to be implemented
        pass
        
        
    def extract_bc_api(self, record:str):
        """extract the binary bc api from a record
        and store them in self.binary_bc_method and self.binary_bc_type
        
        Args:
            record (str): a bin bc record from japicmp report
        """
        # to be implemented
        pass