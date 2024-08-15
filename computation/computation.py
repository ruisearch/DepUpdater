"""get the newest compatible version of a dependency"""
class Computation:
    def __init__(self, cur_node:dict, graph:list, json_path: str):
        """
        Args:
            cur_node : the dependency to be computed
            graph : the dependency graph
            json_path : the path to the json file to record the graph
        """
        self.cur_node = cur_node
        self.graph = graph
        self.json_path = json_path
        
    def get_old_deps(self):
        """get the old dependencies of the current dependency\n
        just return groupId and artifactId of the old dependencies
        """
        old_deps = []
        for dep in self.graph:
            dependents = dep['Dependents']
            for dependent in dependents:
                if dependent['GroupId'] == self.cur_node['GroupId'] and dependent['ArtifactId'] == self.cur_node['ArtifactId']:
                    old_deps.append({'GroupId': dep['GroupId'], 'ArtifactId': dep['ArtifactId']})
        return old_deps

    def compute_best_version(self):
        """main function to compute the newest compatible version of the dependency"""
        print('to be continued...')
        
    def get_reachable_methods(self):
        """get all reachable methods of the dependency"""
        # if dependent is empty, then it is the client, and all methods are reachable
        print('to be continued...')
        
    def get_reachable_types(self):
        """get all reachable types of the dependency"""
        # if dependent is empty, then it is the client, and all types are reachable
        print('to be continued...')