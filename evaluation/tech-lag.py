"""class to compute technical lag"""
import json
import os
class TechLag:
    def __init__(self, ret_folder, json_path):
        """Args:
        ret_folder: str, path to the folder containing ret files of a module
        json_path: str, path to the json file containing the versions of the deps in the module
        """
        self.ret_folder = ret_folder
        self.json_path = json_path
        self.deps = self.extract_deps()

    def extract_deps(self):
        """extract dep from json"""
        with open(self.json_path, 'r') as f:
            deps = json.load(f)
        ret_deps = []
        for dep in deps:
            if dep['Best_Version'] and dep['Dependents']:
                # consider the deps that has the best version and has dependents
                ret_deps.append(dep)
        return ret_deps

    def compute_original_tag(self):
        """compute the original tag of the module"""
        for dep in self.deps:
            pass