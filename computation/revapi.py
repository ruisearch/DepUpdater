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
    
if __name__ == '__main__':
    from constants import MainProcess_pwd
    old_jar = os.path.join(MainProcess_pwd, 'test', 'byte-buddy-1.12.19.jar')
    new_jar = os.path.join(MainProcess_pwd, 'test', 'byte-buddy-1.14.13.jar')
    revapi = Revapi(old_jar, new_jar)
    revapi.compare('net.bytebuddy', 'byte-buddy', '1.12.19', '1.14.13')