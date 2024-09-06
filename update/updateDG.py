"""update dependency graph after computing the newest compatible version of a dependency"""

class Update:

    def __init__(self, cur_dep, graph, queue):
        """
        Args:
            cur_dep (dict): the dependency that has been computed and validated
            graph (list): the dependency graph, a list of dict
            queue (deque): the queue that stores the dependencies can be computed()
        """
        self.cur_dep = cur_dep
        self.graph = graph
        self.queue = queue
