"""update dependency graph after computing the newest compatible version of a dependency"""
from collections import deque
from database.query import query_dependencies_from_mongo
from update.updateDB import populate_dep
class Update:

    def __init__(self, cur_node:dict, graph:list, queue:deque, old_deps:list):
        """
        Args:
            cur_node (dict): the node in graph that has been computed and validated
            graph (list): the dependency graph, a list of dict
            queue (deque): the queue that stores the dependencies can be computed(all dependents have been computed)
            old_deps (list): the old dependencies of cur_node
        """
        self.cur_node = cur_node
        self.graph = graph
        self.queue = queue
        # dict of old_deps; groupId:artifactId -> index
        self.old_dict = self.get_old_deps_dict(old_deps)
        # dict of graph; groupId:artifactId -> index
        self.graph_dict = self.get_graph_dict()
        # dict of new new_deps; groupId:artifactId -> [version, type]
        self.new_dict = self.get_new_deps_dict()
        # dict of queue; groupId:artifactId -> dep dict in queue
        self.queue_dict = self.get_queue_dict()

    def get_queue_dict(self):
        """transform queue from a deque of dicts to a dict of groupId:artifactId -> dep dict in queue
        Returns:
            queue (dict): the dependencies in the queue; groupId:artifactId -> dep dict in queue
        """
        queue_dict = {}
        if self.queue is None:
            self.queue = deque()
            return queue_dict
        for dep in self.queue:
            queue_dict[dep['GroupId']+':'+dep['ArtifactId']] = dep
        return queue_dict

    def get_old_deps_dict(self, old_deps:list):
        """transform old_deps from a list of dicts to a dict of groupId:artifactId -> index
        Args:
            old_deps (list): the old dependencies of cur_node
            consisting of dicts
            {
                'GroupId': str,
                'ArtifactId': str
            }
        Returns:
            old (dict): the old dependencies of cur_node; groupId:artifactId -> index
        """
        old = {}
        for old_dep in old_deps:
            for i, dep in enumerate(self.graph):
                if dep['GroupId'] == old_dep['GroupId'] and dep['ArtifactId'] == old_dep['ArtifactId']:
                    old[old_dep['GroupId']+':'+old_dep['ArtifactId']] = i
                    break
        return old

    def get_graph_dict(self):
        """transform graph from a list of dicts to a dict of groupId:artifactId -> index
        Returns:
            graph (dict): the dependency graph; groupId:artifactId -> index
        """
        graph = {}
        for i, dep in enumerate(self.graph):
            graph[dep['GroupId']+':'+dep['ArtifactId']] = i
        return graph

    def get_new_deps_dict(self):
        """get new deps first; then transform new_deps from a list of dicts to a dict of groupId:artifactId -> index
        Returns:
            new (dict): the new dependencies of cur_node; groupId:artifactId -> [version, type]
        """
        return self.query_dependencies()

    def query_dependencies(self):
        """query the dependencies of the cur_node from the database
        1. get new_deps from mongodb;
        2. filter gav and type of the new_deps;
        3. transform new_deps from a list of dicts to a dict of groupId:artifactId -> [version, type]
        """
        groupId = self.cur_node['GroupId']
        artifactId = self.cur_node['ArtifactId']
        version = self.cur_node['Best_Version']
        # query the dependencies of the cur_node from the database
        dependencies = query_dependencies_from_mongo(groupId, artifactId, version)
        if dependencies is None:
            # the dependencies of the cur_node are not in the database
            # get the dependencies and store them in the database
            dependencies = populate_dep(groupId, artifactId, version)
        dependencies_dict = self.filter_dep(dependencies)
        return dependencies_dict

    def filter_dep(self, dependencies:list):
        """filter the dependencies of the cur_node:
        1. remove the dependencies that are test or provided
        2. remove the dependencies that are optional and not the direct dependency of the client
        Returns:
            dependencies_dict (dict): the dependencies of the cur_node; groupId:artifactId -> [version, type]
        """
        dependencies_dict = {}
        for dependency in dependencies:
            gav = dependency['dep']
            # g,a,v is splited by the first two ':' of gav
            g, a, v = gav.split(':', 2)
            if dependency['dScope'] == 'test' or dependency['dScope'] == 'provided':
                continue
            if dependency['isoptional'] == 'true':
                # check if the dependency is the direct dependency of the client
                if f'{g}:{a}' in self.graph_dict:
                    index = self.graph_dict[f'{g}:{a}']
                    depth = self.graph[index]['Depth']
                    if depth == 1:
                        dependencies_dict[f'{g}:{a}'] = [f'{v}', dependency['dScope']]
                continue
            dependencies_dict[f'{g}:{a}'] = [f'{v}', dependency['dScope']]
        return dependencies_dict

    def update(self):
        """main method to update the dependency graph and the queue after computing the newest compatible version of a dependency"""
        new = set(self.new_dict.keys())
        old = set(self.old_dict.keys())
        graph = set(self.graph_dict.keys())
        # handle new & old
        self.update_existing_deps(new & old)
        # handle (new-old) & graph
        self.add_new_deps((new - old) & graph)
        # handle old - new
        self.remove_deps(old - new)
        # handle new - graph
        self.add_new_deps_to_graph(new - graph)

    def update_existing_deps(self, ga_set:set):
        """situation 1: the dependency is in both old_deps and new_deps"""
        best_version = self.cur_node['Best_Version']
        for ga in ga_set:
            idx = self.graph_dict[ga]
            dep_dict = self.graph[idx]
            # update graph
            for dependent in dep_dict['Dependents']:
                if self.cur_node['GroupId'] == dependent['GroupId'] and self.cur_node['ArtifactId'] == dependent['ArtifactId']:
                    # update the version of the dependent and the defined version(of this dep) by the dependent
                    if dependent['Version'] != best_version:
                        dependent['Version'] = best_version
                        # the best version of this dependency is outdated
                        dep_dict['Best_Version'] = ""
                        dependent['Define_Version'] = self.new_dict[ga][0]
                    break

            # update queue
            # 1. compute the in-degree to judge if the dependency is ready to be computed
            flag = self.is_ready(dep_dict['Dependents'])
            # 2. update queue by the in-degree(whether bigger than 0) and dep ga
            self.update_queue(flag, ga)

    def add_new_deps(self, ga_set:set):
        """situation 2: the dependency is in new_deps aw well as original graph but not in old_deps"""
        pass

    def remove_deps(self, ga_set:set):
        """situation 3: the dependency is in old_deps but not in new_deps"""
        pass

    def add_new_deps_to_graph(self, ga_set:set):
        """situation 4: the dependency is in new_deps but not in original graph"""
        pass


    def update_queue(self, is_ready:bool, ga:str):
        """update the queue after updating the dependency graph
        Args:
            is_ready (bool): if the dependency is ready to be computed(all dependents have been computed)
            ga (str): the groupId:artifactId of the dependency
        """
        # whether the dependency is in the queue
        is_in = ga in self.queue_dict
        if is_ready and not is_in:
            # the dependency is ready to be computed and not in the queue
            # add the dependency to the queue
            self.queue.append(self.graph[self.graph_dict[ga]])
            self.queue_dict[ga] = self.graph[self.graph_dict[ga]]
        elif not is_ready and is_in:
            # the dependency is not ready to be computed and in the queue
            # remove the dependency from the queue
            self.queue.remove(self.queue_dict[ga])
            self.queue_dict.pop(ga)

    def is_ready(self, dependents_list: list):
        """compute the in-degree of the dependents of the dependency
        if the in-degree is 0, return True; if in-degree is bigger than 0, return False
        """
        
        for dependent in dependents_list:
            dependent_g = dependent['GroupId']
            dependent_a = dependent['ArtifactId']
            if not self.is_computed_yet(f'{dependent_g}:{dependent_a}'):
                # a dependent is not computed yet
                return False
        return True

    def is_computed_yet(self, ga):
        """check if the dependency is computed yet
        Args:
            ga (str): the groupId:artifactId of the dependency
        """
        dep_dict = self.graph[self.graph_dict[ga]]
        if dep_dict['Best_Version'] == "":
            return False
        return True