"""use soot to get the CG/type_DG of a jar file"""
import os
import subprocess
import requests
from database.query import query_to_get_jar_location, query_call_graph,\
    store_call_graph, query_type_dependency_graph, store_type_dependency_graph
from constants import SOOTCG_PATH,SOOT_TYPE_DG_PATH
from preprocess.Restore import Restore

class Api:
    def __init__(self, groupId:str, artifactId:str, version:str):
        self.groupId = groupId
        self.artifactId = artifactId
        self.version = version

    def get_cg(self):
        """get the call graph of the jar file"""
        # query the call graph from sqlite
        cg = query_call_graph(self.groupId, self.artifactId, self.version)
        if cg:
            # call graph exists in the database
            return cg
        # call graph does not exist in the database, so use sootCG to get the call graph
        jar_path = self.get_jar()
        Restore.get_dep_jar(self.groupId, self.artifactId, self.version)
        # run sootCG
        command = f"java -jar {SOOTCG_PATH} {jar_path}"
        result = subprocess.run(command, shell=True, text=True, capture_output=True)
        cg = result.stdout
        store_call_graph(self.groupId, self.artifactId, self.version, cg)
        return cg
    
    def get_type_dg(self):
        """get the type dependency graph of the jar file"""
        jar_path = self.get_jar()
        Restore.get_dep_jar(self.groupId, self.artifactId, self.version)
        # query the type dependency graph from sqlite
        type_dg = query_type_dependency_graph(self.groupId, self.artifactId, self.version)
        if type_dg:
            # type dependency graph exists in the database
            return type_dg
        # run soot_Type_DG
        command = f"java -jar {SOOT_TYPE_DG_PATH} {jar_path}"
        result = subprocess.run(command, shell=True, text=True, capture_output=True)
        type_dg = result.stdout
        store_type_dependency_graph(self.groupId, self.artifactId, self.version, type_dg)
        return type_dg

    def get_jar(self):
        """get the jar file"""
        jar_path = query_to_get_jar_location(self.groupId, self.artifactId, self.version)
        return jar_path

if __name__ == '__main__':
    api = Api('joda-time', 'joda-time', '2.12.7')
    print("get cg")
    api.get_cg()
    print("get type dg")
    api.get_type_dg()