import os
import requests
import json
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
        
        response = requests.get(url, params=params)
        data = response.json()

        versions = []
        if 'docs' in data['response']:
            for doc in data['response']['docs']:
                if 'timestamp' in doc:
                    versions.append({
                        'version': doc['v'],
                        'date': doc['timestamp']
                    })
        
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
    def get_best_version(self):
        gav = {'g':self.GroupId, 'a':self.ArtifactId, 'v':self.Version}
        rev = Revapi(gav, self.ReachableAPIs, self.AllVersion, self.Pwd, self.JarFileName, self.DependedBy)
        return rev.get_best_version()
        
    