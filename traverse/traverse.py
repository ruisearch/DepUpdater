"""main file for traversing in the dependency graph"""
import os
import json
from collections import deque

from computation.computation import Computation
from computation.validation import Validation

class Traverse:
    def __init__(self, json_path, path_to_project_folder, relative_path_to_module):
        with open(json_path, 'r', encoding='utf-8') as f:
            self.graph = json.load(f)
        self.json_path = json_path
        self.queue = deque()
        self.repo_name = os.path.basename(path_to_project_folder)
        self.path_to_project_folder = path_to_project_folder
        self.relative_path_to_module = relative_path_to_module
        self.init_queue()
        self.compute_api_of_client()
    
    def init_queue(self):
        """put all direct dependencies of client jar into queue"""
        for dep in self.graph:
            if dep['Depth'] == 1:
                self.queue.append(dep)

    def compute_api_of_client(self):
        """get the methods and types of client jar first"""
        for dep in self.graph:
            if dep['Depth'] == 0:
                client_com = Computation(dep, self.graph, self.repo_name, self.relative_path_to_module)
                client_com.get_and_record_reachable_api()
                break

    def traverse(self):
        """traverse the graph to compute the newest compatible version of each dependency in order"""
        # back up the original pom.xml
        pom_path = os.path.join(self.path_to_project_folder, self.relative_path_to_module, 'pom.xml')
        original_pom_path = os.path.join(self.path_to_project_folder, self.relative_path_to_module, '_original_pom.xml')
        Validation.backup_pom(original_pom_path, pom_path)
        
        while self.queue:
            cur_dep = self.queue.popleft()
            # find the newest compatible version of cur_dep,
            # and return its new dependencies and old dependencies to update the graph,
            # record the graph in version.json in real time
            # --> new_deps = compute_newest_version(cur_dep, self.graph, self.json_path)
            old_deps = self.compute_and_validate(cur_dep)
            # update the graph and queue,
            # record the graph in version.json in real time
            # --> update_graph(cur_dep, old_deps, new_deps, self.graph, self.queue, self.json_path)
        
        # restore the pom.xml and back up the pom.xml after validating
        backed_up_pom_path = os.path.join(self.path_to_project_folder, self.relative_path_to_module, '_backed_up_pom.xml')
        Validation.restore_pom(original_pom_path, pom_path, backed_up_pom_path)


    def compute_and_validate(self, cur_dep:dict):
        """compute the newest compatible version of the dependency and validate it
        Args:
            cur_dep (dict): the dependency to be computed and validated
        Returns:
            old_deps (list): the old dependencies of cur dep
        """
        com = Computation(cur_dep, self.graph, self.repo_name, self.relative_path_to_module)
        old_deps = com.get_old_deps()
        # compute the newest compatible version of cur_dep
        best_version = com.compute_best_version()
        method_entry_points, type_entry_points = com.return_entry_points()
        # validate. If the actually best version is different from the best version got by tool, exit
        self.validate(cur_dep, best_version, method_entry_points, type_entry_points)
        com.get_and_record_reachable_api(best_version)
        cur_dep['Best_Version'] = best_version
        # #debug
        # print(self.graph)
        self.record_graph(self.graph, self.json_path)
        return old_deps

    def validate(self, cur_dep, best_version, method_entry_points, type_entry_points):
        """get the actually best version and compare it with the best version got by tool. If they are different, exit
        Args:
            cur_dep (dict): the dependency to be validated
            best_version (str): the best version got by tool
            method_entry_points (list): the entry points of methods(from computation phase)
            type_entry_points (list): the entry points of types(from computation phase)
        """
        val = Validation(self.path_to_project_folder, self.relative_path_to_module)
        group_id = cur_dep['GroupId']
        artifact_id = cur_dep['ArtifactId']
        versions = [version['version'] for version in cur_dep['Versions']]
        if cur_dep['Depth'] == 1:
            direct_or_transitive = 'direct'
        else:
            direct_or_transitive = 'transitive'
        val.validate(group_id, artifact_id, versions, best_version, method_entry_points, type_entry_points, direct_or_transitive)
        
    @staticmethod
    def record_graph(graph, json_path):
        """record the graph in version.json"""
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(graph, f, ensure_ascii=False, indent=4)