import os
import requests
import json
from operator import itemgetter
from calculate.Revapi import Revapi

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
        self.Pwd = dep_path

    def fetch_versions_sorted_by_date(self):
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
        versions.sort(key=itemgetter('date'))
        self.AllVersion = versions
        return versions
    ## get newest compatible version
    def get_best_version(self):
        gav = {'g':self.GroupId, 'a':self.ArtifactId, 'v':self.Version}
        rev = Revapi(gav, self.ReachableAPIs, self.AllVersion, self.Pwd, self.JarFileName)
        return rev.get_best_version()
        
    