"""main file for traversing in the dependency graph"""
import json
from collections import deque

from computation.computation import Computation

class Traverse:
    def __init__(self, json_path, repo_name, relative_path_to_module):
        with open(json_path, 'r', encoding='utf-8') as f:
            self.graph = json.load(f)
        self.json_path = json_path
        self.queue = deque()
        self.repo_name = repo_name
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
                client_com.get_reachable_api()
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
            com.get_and_record_reachable_api(best_version)
            # update the graph and queue,
            # record the graph in version.json in real time
            # --> update_graph(cur_dep, old_deps, new_deps, self.graph, self.queue, self.json_path)


