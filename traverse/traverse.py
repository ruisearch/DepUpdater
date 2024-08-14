"""main file for traversing in the dependency graph"""
from collections import deque

class Traverse:
    def __init__(self, module):
        self.module = module
        self.visited = set()
        self.queue = deque()

    def __iter__(self):
        self.queue.append(self.module)
        return self

    def __next__(self):
        if not self.queue:
            raise StopIteration
        module = self.queue.popleft()
        if module in self.visited:
            return self.__next__()
        self.visited.add(module)
        self.queue.extend(module.dependencies)
        return module