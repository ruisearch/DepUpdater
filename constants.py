# define the constants about the data location
"""data folder structure:
    {MainProcess_pwd}/data/
    ├── jar/
    | ├── {group_id}/
    | | ├── {artifact_id}/
    | | | ├── {version}/
    | ...
    ├── tree/
    | {path_to_repo}_{relative_path_to_module}.txt
    |  ...
    ├── result/
    | ├── {repo_name}/
    | | ├── {relative_path_to_module}/
    | | | ├── match.json
    | ...
"""
import os

# path to the root dir of this Tool
MainProcess_pwd = os.path.dirname(os.path.abspath(__file__))

# path to data/
DATA_DIR = os.path.join(MainProcess_pwd, 'data/')
# path to data/tree/
TREE_DIR = os.path.join(DATA_DIR, 'tree/')
# path to data/jar/
JAR_DIR = os.path.join(DATA_DIR, 'jar/')
# path to data/result/
RET_DIR = os.path.join(DATA_DIR, 'result/')