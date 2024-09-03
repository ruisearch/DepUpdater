"""main file for traversing in the dependency graph"""
import os
import json
from collections import deque

from computation.computation import Computation
from computation.validation import Validation

class Traverse:
    def __init__(self, json_path, path_to_folder, relative_path_to_module):
        with open(json_path, 'r', encoding='utf-8') as f:
            self.graph = json.load(f)
        self.json_path = json_path
        self.queue = deque()
        self.repo_name = os.basename(path_to_folder)
        self.path_to_project_folder = path_to_folder
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
                client_com = Computation(dep, self.graph, self.json_path, self.repo_name, self.relative_path_to_module)
                client_com.get_and_record_reachable_api()
                break

    def traverse(self):
        """traverse the graph to compute the newest compatible version of each dependency"""
        while self.queue:
            cur_dep = self.queue.popleft()
            # find the newest compatible version of cur_dep,
            # and return its new dependencies and old dependencies to update the graph,
            # record the graph in version.json in real time
            # --> new_deps = compute_newest_version(cur_dep, self.graph, self.json_path)
            com = Computation(cur_dep, self.graph, self.json_path, self.repo_name, self.relative_path_to_module)
            old_deps = com.get_old_deps()
            best_version = com.compute_best_version()
            method_entry_points, type_entry_points = com.return_entry_points()
            # validate. If the actually best version is different from the best version got by tool, exit
            self.validate(cur_dep, best_version, method_entry_points, type_entry_points)
            com.get_and_record_reachable_api(best_version)
            # update the graph and queue,
            # record the graph in version.json in real time
            # --> update_graph(cur_dep, old_deps, new_deps, self.graph, self.queue, self.json_path)

    def validate(self, cur_dep, best_version, method_entry_points, type_entry_points):
        """get the actually best version and compare it with the best version got by tool
        Args:
            cur_dep (dict): the dependency to be validated
            best_version (str): the best version got by tool
            method_entry_points (list): the entry points of methods
            type_entry_points (list): the entry points of types
        """
        val = Validation(self.path_to_project_folder, self.relative_path_to_module)
        group_id = cur_dep['GroupId']
        artifact_id = cur_dep['ArtifactId']
        versions = [version['version'] for version in cur_dep['Versions']]
        if cur_dep['Depth'] == 1:
            direct_or_transitive = 'direct'
        else:
            direct_or_transitive = 'transitive'
        actual_best_version = val.validate(group_id, artifact_id, versions, method_entry_points, type_entry_points, direct_or_transitive)
        if best_version != actual_best_version:
            print(f"Error: the best version of {group_id}:{artifact_id} got by tool is {best_version}, but the actual best version is {actual_best_version}")
            exit(1)