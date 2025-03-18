"""main file for traversing in the dependency graph"""
import os
import json
from collections import deque
import subprocess

from computation.rq3_computation import Computation
from logger.logger import log_debug
from constants import VALIDATION_LOG_DIR
class Traverse:
    def __init__(self, json_path:str, path_to_project_folder:str, relative_path_to_module:str):
        """
        Args:
            json_path (str): path to json
            path_to_project_folder (str): path to root dir
            relative_path_to_module (str): relative path to module
        """
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
        """put all direct dependencies of client jar into queue
        note: only the dependencies have only one dependent(client) are put into queue
        """
        for dep in self.graph:
            if dep['Depth'] == 1 and len(dep['Dependents']) == 1:
                log_debug(f"{dep['GroupId']}:{dep['ArtifactId']} enqueue.")
                self.queue.append(dep)

    def compute_api_of_client(self):
        """get the methods and types of client jar first"""
        for dep in self.graph:
            if dep['Depth'] == 0:
                client_com = Computation(dep, self.graph, self.repo_name, self.relative_path_to_module, None)
                client_com.get_and_record_reachable_api()
                dep['Best_Version'] = dep['Original_Version']
                break

    def traverse(self, local_dep_jar:list):
        """traverse the graph to compute the newest compatible version of each dependency in order
        Args:
            local_dep_jar (list): a list of gav of local deps
        """
        while self.queue:
            cur_dep = self.queue.popleft()
            
            # no need to compute client anymore
            if cur_dep['Depth'] == 0:
                continue

            log_debug(f"Computing {cur_dep['GroupId']}:{cur_dep['ArtifactId']}")

            if cur_dep['Count'] >= 3:
                # print(f"Dependency {cur_dep['GroupId']}:{cur_dep['ArtifactId']} has been computed for 3 times. Something may goes wrong.")
                log_debug(f'=== Dependency {cur_dep["GroupId"]}:{cur_dep["ArtifactId"]} has been computed for {cur_dep["Count"]} times ===')
                # exit(1)


            # find the newest compatible version of cur_dep,
            # and return its new dependencies and old dependencies to update the graph,
            # record the graph in version.json in real time
            # --> new_deps = compute_newest_version(cur_dep, self.graph, self.json_path)
            old_deps, local_dep_flag = self.compute_and_validate(cur_dep, local_dep_jar)
            cur_dep['Count'] += 1
            
            # 不要更新依赖图，但是要更新队列，以满足拓扑排序的顺序，所以目前完全不执行update不可以，这样只会计算刚开始就入队的节点
            # todo: 更新queue,让目前dependent都已计算的节点可以入队列（参考update/updateDG/update的方法）
            for n in self.get_update_graph():
                if self.need_computed(n) and n not in self.queue:
                    self.queue.append(n)

            log_debug(f"{cur_dep['GroupId']}:{cur_dep['ArtifactId']} has been computed, best version is {cur_dep['Best_Version']}.")

    def get_update_graph(self):
        key = lambda x, y: f"{x}:{y}"
        export_list=list()
        node_info = dict()
        for node in self.graph:
            node_info[key(node["GroupId"], node["ArtifactId"])] = node.get("Best_Version", "")

        for node in self.graph:
            all_reachable = True
            for dep in node.get("Dependents", []):
                if node_info[key(dep["GroupId"], dep["ArtifactId"])] == "":
                    all_reachable = False
                    break
            if all_reachable:
                export_list.append(node)
        return export_list

    def need_computed(self, node:dict):
        """check whether the node need to be computed"""
        if node.get("Best_Version", "") != "":
            # the node has been computed
            return False
        if node.get("Depth", 0) == 0:
            # client
            return False
        if node.get("Dependents", []) == []:
            # no dependent means not in graph actually
            return False
        return True

    def compute_and_validate(self, cur_dep:dict, local_dep_jar:list):
        """compute the newest compatible version of the dependency and validate it
        Args:
            cur_dep (dict): the dependency to be computed and validated
            local_dep_jar (list): a list of gav of local deps
        Returns:
            old_deps (list): the old dependencies of cur dep
            local_dep_flag (bool) : whether cur_dep is a local dep
        """
        com = Computation(cur_dep, self.graph, self.repo_name, self.relative_path_to_module, local_dep_jar)
        old_deps = com.get_old_deps()
        local_dep_flag = False
        # compute the newest compatible version of cur_dep
        best_version, local_dep_flag = com.compute_best_version()
        # method_entry_points, type_entry_points = com.return_entry_points()
        # # validate. If the actually best version is different from the best version got by tool, exit
        # self.validate(cur_dep, best_version, method_entry_points, type_entry_points)

        com.get_and_record_reachable_api(best_version)
        cur_dep['Best_Version'] = best_version
        # #debug
        # print(self.graph)
        self.record_graph(self.graph, self.json_path)
        return old_deps, local_dep_flag

    def get_old_best_version(self, cur_dep):
        """get the old best version of the dependency"""
        if cur_dep['Count'] == 0:
            # the first time to compute the dependency
            return cur_dep['Original_Version']
        if cur_dep['Best_Version']:
            # the dependency has been computed before
            return cur_dep['Best_Version']
        # the dependency has been computed before, but the best version is cleared in update phase
        return None

    @staticmethod
    def record_graph(graph, json_path):
        """record the graph in version.json"""
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(graph, f, ensure_ascii=False, indent=4)