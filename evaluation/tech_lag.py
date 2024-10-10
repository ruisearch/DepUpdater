"""class to compute technical lag"""
import json

class TechLag:
    def __init__(self, json_path):
        """Args:
        json_path: str, path to the json file containing the versions of the deps in the module
        """
        self.json_path = json_path
        self.deps = self.extract_deps()
        self.original_lag = 0
        self.current_lag = 0
        self.compute_original_lag()
        self.compute_current_lag()
        self.reduced_lag = self.original_lag - self.current_lag

    def extract_deps(self):
        """extract dep from json"""
        with open(self.json_path, 'r') as f:
            deps = json.load(f)
        ret_deps = []
        for dep in deps:
            if dep['Best_Version'] and dep['Dependents']:
            # if dep['Dependents']:
                # consider the deps that are in graph actually
                ret_deps.append(dep)
        return ret_deps

    def compute_original_lag(self):
        """compute the original lag of the module"""
        for dep in self.deps:
            self.original_lag += len(dep['Dependents']) - 1

    def compute_current_lag(self):
        """compute the current lag of the module"""
        for dep in self.deps:
            all_versions = dep['Versions']
            best_version = dep['Best_Version']
            idx = self.find_idx(all_versions, best_version)
            self.current_lag += idx

    def find_idx(self, all_versions:list, version:str):
        """find the index of the version in all versions"""
        for idx, v in enumerate(all_versions):
            if v['version'] == version:
                return idx