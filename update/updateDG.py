"""update dependency graph after computing the newest compatible version of a dependency"""
from collections import deque

class Update:

    def __init__(self, cur_dep:dict, graph:list, queue:deque, old_deps:list):
        """
        Args:
            cur_dep (dict): the dependency that has been computed and validated
            graph (list): the dependency graph, a list of dict
            queue (deque): the queue that stores the dependencies can be computed(all dependents have been computed)
            old_deps (list): the old dependencies of cur_dep
        """
        self.cur_dep = cur_dep
        self.graph = graph
        self.queue = queue
        # dict of old_deps
        self.old_dict = self.get_old_deps_dict(old_deps)
        # dict of graph
        self.graph_dict = self.get_graph_dict()
        # dict new new_deps
        self.new_dict = self.get_new_deps_dict()

    def get_old_deps_dict(self, old_deps:list):
        """transform old_deps from a list of dicts to a dict of groupId:artifactId -> index
        Args:
            old_deps (list): the old dependencies of cur_dep
            consisting of dicts
            {
                'groupId': str,
                'artifactId': str
            }
        Returns:
            old (dict): the old dependencies of cur_dep; groupId:artifactId -> index
        """
        old = {}
        for old_dep in old_deps:
            for i, dep in enumerate(self.graph):
                if dep['groupId'] == old_dep['groupId'] and dep['artifactId'] == old_dep['artifactId']:
                    old[old_dep['groupId']+':'+old_dep['artifactId']] = i
                    break
        return old
    
    def get_graph_dict(self):
        """transform graph from a list of dicts to a dict of groupId:artifactId -> index
        Returns:
            graph (dict): the dependency graph; groupId:artifactId -> index
        """
        graph = {}
        for i, dep in enumerate(self.graph):
            graph[dep['groupId']+':'+dep['artifactId']] = i
        return graph
    
    def get_new_deps_dict(self):
        """get new deps first; then transform new_deps from a list of dicts to a dict of groupId:artifactId -> index
        Returns:
            new (dict): the new dependencies of cur_dep; groupId:artifactId -> [version, type]
        """
        new = {}
        # 1. get new_deps from mongodb;
        # 2. filter gav and type of the new_deps;
        # 3. transform new_deps from a list of dicts to a dict of groupId:artifactId -> [version, type]
        # ... todo
        return new
    
    def update_graph(self):
        """main method to update the dependency graph and the queue after computing the newest compatible version of a dependency"""
        new = set(self.new_dict.keys())
        old = set(self.old_dict.keys())
        graph = set(self.graph_dict.keys())
        # handle new & old
        self.update_existing_deps(new & old)
        # handle (new-old) & graph
        self.add_new_deps(new - old)
        # handle old - new
        self.remove_deps(old - new)
        # handle new - graph
        self.add_new_deps_to_graph(new - graph)
        
    def update_existing_deps(self, ga_set:set):
        """situation 1: the dependency is in both old_deps and new_deps"""
        pass
    
    def add_new_deps(self, ga_set:set):
        """situation 2: the dependency is in new_deps but not in old_deps"""
        pass
    
    def remove_deps(self, ga_set:set):
        """situation 3: the dependency is in old_deps but not in new_deps"""
        pass
    
    def add_new_deps_to_graph(self, ga_set:set):
        """situation 4: the dependency is in new_deps but not in original graph"""
        pass
    
    def return_dep_by_idx(self, idx:int):
        """return the dependency by index"""
        return self.graph[idx]