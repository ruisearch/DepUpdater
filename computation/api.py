"""use soot to get the CG/type_DG of a jar file"""
import os
import subprocess
import requests
from database.query import query_to_get_jar_location, query_call_graph,\
    store_call_graph, query_type_dependency_graph, store_type_dependency_graph
from constants import SOOTCG_PATH,SOOT_TYPE_DG_PATH,REACHABLE_API_DIR
from preprocess.Restore import Restore

class Api:
    def __init__(self, groupId:str, artifactId:str, version:str, ):
        self.groupId = groupId
        self.artifactId = artifactId
        self.version = version

    def get_cg(self):
        """get the call graph of the jar file
        Returns:
            cg (str): call graph in string format
        """
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
    
    def extract_methods_from_cg(self, cg:str):
        """extract methods from call graph"""
        methods = set()
        for line in cg.split('\n'):
            # caller -> callee in one line, extract caller and callee
            if '->' in line:
                caller, callee = line.split(' -> ')
                methods.add(caller.strip())
                methods.add(callee.strip())
        return methods
    
    def extract_types_from_dg(self, dg:str):
        """extract types from dependency graph"""
        types = set()
        for line in dg.split('\n'):
            # caller -> callee in one line, extract caller and callee
            if '->' in line:
                caller, callee = line.split(' -> ')
                types.add(caller.strip())
                types.add(callee.strip())
        return types

    @staticmethod
    def parse_call_relations(call_relations_str:str):
        """Parse a string of caller -> callee relations
        Args:
            call_relations_str (str): A string of caller -> callee relations\n
            can be cg ,type_dg or reachable_api_pair from file
        Returns:
            call_relations (dict): A dictionary of caller -> callees relations\n
            key: caller, value: a set of the corresponding callees\n
        """
        call_relations = {}
        callers = set()
        callees = set()
        
        # Split the string by lines
        lines = call_relations_str.strip().split('\n')
        
        # Process each line
        for line in lines:
            caller, callee = line.strip().split(' -> ')
            callers.add(caller)
            callees.add(callee)
            if caller in call_relations:
                call_relations[caller].add(callee)
            else:
                call_relations[caller] = {callee}
        return call_relations
    
    @staticmethod
    def find_matching_relations(call_relations: dict, target_callers:set):
        """Filter caller -> callee relations in call_relations that callee in target_callers
        Args:
            call_relations (dict): A dictionary of caller -> callees relations\n
            key: caller, value: a set of the corresponding callees\n
            target_callers (set): A set of target callers\n
        Returns:
            matching_relations (set): A set of matching caller -> callee relations tuple\n
            [0] is caller while [1] is callee
        """
        matching_relations = set()
        
        for caller, callees in call_relations.items():
            for callee in callees:
                if callee in target_callers:
                    matching_relations.add((caller, callee))
        return matching_relations
    
    @staticmethod
    def find_reachable_calls(entry_points:set, call_relations:dict):
        """Recursively find all reachable call relations starting from entry points"""
        reachable = set()
        
        def dfs(caller):
            if caller in call_relations:
                for callee in call_relations[caller]:
                    relation = (caller, callee)
                    if relation not in reachable:
                        reachable.add(relation)
                        dfs(callee)
        for entry in entry_points:
            dfs(entry)
        
        return reachable

if __name__ == '__main__':
    api = Api('joda-time', 'joda-time', '2.12.7')
    print("get cg")
    api.get_cg()
    print("get type dg")
    api.get_type_dg()