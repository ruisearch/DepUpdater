import os
import requests
import json
import time
from functools import cmp_to_key
# from operator import itemgetter
from calculate.Revapi import Revapi
import semver
class Dep:
    # dep_path : path to dep/
    # dep_dict : the json object
    # Pwd : path to the dep folder
    def __init__(self, dep_dict:dict, dep_path:str):
        self.JarFileName = dep_dict["JarFileName"]
        self.GroupId = dep_dict["GroupId"]
        self.ArtifactId = dep_dict["ArtifactId"]
        self.Version = dep_dict["Version"]
        self.ReachableAPIs = dep_dict["ReachableAPIs"]
        self.Classifier = dep_dict['Classifier']
        self.DependedBy = dep_dict['DependedBy']
        self.Pwd = dep_path

    def fetch_versions_sorted(self):
        url = f"https://search.maven.org/solrsearch/select"
        query = f"g:\"{self.GroupId}\" AND a:\"{self.ArtifactId}\""
        params = {
            'q': query,
            'rows': '100',
            'core': 'gav',
            'wt': 'json'
        }
        @staticmethod
        def get_resource_with_retry(url, params, retries=5, backoff_factor=0.3, timeout=10):
            for attempt in range(retries):
                try:
                    response = requests.get(url, params=params,timeout=timeout)
                    response.raise_for_status()
                    return response
                except requests.RequestException as e:
                    print(f"Attempt {attempt + 1} failed: {str(e)}")
                    if attempt < retries - 1:
                        sleep_time = backoff_factor * (2 ** attempt)
                        print(f"Retrying in {sleep_time} seconds...")
                        time.sleep(sleep_time)
                    else:
                        raise
        try:
            # response = requests.get(url, params=params)
            response = get_resource_with_retry(url, params=params)
            if response:
                data = response.json()

                versions = []
                if 'docs' in data['response']:
                    for doc in data['response']['docs']:
                        if 'timestamp' in doc:
                            versions.append({
                                'version': doc['v'],
                                'date': doc['timestamp']
                            })
        except Exception as e:
            print(f"Fail to handle {self.GroupId}:{self.ArtifactId}, reason:{e}")
        
        # Sort versions by date
        # versions.sort(key=itemgetter('date'))
        # Sort versions using a custom comparison function
        versions.sort(key=cmp_to_key(self.version_comparator))
        self.AllVersion = versions
        return versions
    def version_comparator(self, a, b):
            # Try to parse versions as SemVer
            try:
                a_semver = semver.VersionInfo.parse(a['version'])
                a_is_semver = True
            except ValueError:
                a_semver = None
                a_is_semver = False

            try:
                b_semver = semver.VersionInfo.parse(b['version'])
                b_is_semver = True
            except ValueError:
                b_semver = None
                b_is_semver = False

            # If both are SemVer compliant, sort by SemVer
            if a_is_semver and b_is_semver:
                if a_semver < b_semver:
                    return -1
                elif a_semver > b_semver:
                    return 1
                else:
                    return 0

            # If either is not SemVer compliant, sort by date
            if a['date'] < b['date']:
                return -1
            elif a['date'] > b['date']:
                return 1
            else:
                return 0
    ## get newest compatible version
    # tqdm_log_module_folder: path to tqdm_log/{module_name}/ containing files denoting the progress of each process
    def get_best_version(self, tqdm_log_module_folder:str):
        gavc = {'g':self.GroupId, 'a':self.ArtifactId, 'v':self.Version, 'c':self.Classifier}
        rev = Revapi(gavc, self.ReachableAPIs, self.AllVersion, self.Pwd, self.JarFileName, self.DependedBy)
        return rev.get_best_version(tqdm_log_module_folder)
        
    