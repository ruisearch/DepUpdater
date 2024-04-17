## 
import requests
import json
from operator import itemgetter

class Dep:
    def __init__(self, dep_dict:dict):
        self.JarFileName = dep_dict["JarFileName"]
        self.GroupId = dep_dict["GroupId"]
        self.ArtifactId = dep_dict["ArtifactId"]
        self.Version = dep_dict["Version"]
        self.ReachableAPIs = dep_dict["ReachableAPIs"]
    
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
        versions.sort(key=itemgetter('date'), reverse=True)
        self.AllVersion = versions
        return versions
    