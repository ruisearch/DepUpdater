"""
define the constants about the data location

data folder structure:
    {MainProcess_pwd}/data/
    ├── jar/
    | ├── {group_id}/
    | | ├── {artifact_id}/
    | | | ├── {version}/
    | ...
    ├── tree/
    | ├── {repo_name}/
    | | ├── {relative_path_to_module}/
    | | | ├── verbose_tree.txt
    |  ...
    ├── result/
    | ├── {repo_name}/
    | | ├── {relative_path_to_module}/
    | | | ├── version.json
    | ...
    ├── reachableApi/
    | ├── {repo_name}/
    | | ├── {relative_path_to_module}/
    | | | | ├── {group_id}/
    | | | | | ├── {artifact_id}/
    | | | | | | ├── methods.txt
    | | | | | | ├── types.txt
    | ...
    ├── tqdm_log/
    | ├── {module_name}/
    | | ├── {relative_path_to_module}/
    | | | ├── {groupId}_{artifactId}.tqdm_log.txt
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
# absolute to tqdm_log/
TQDM_LOG_PATH = os.path.join(DATA_DIR, 'tqdm_log/')
# path to data/reachableApi/
REACHABLE_API_DIR = os.path.join(DATA_DIR, 'reachableApi/')

# path to sootCG
SOOTCG_PATH = os.path.join(MainProcess_pwd, 'utils/sootCG-1.0-SNAPSHOT-jar-with-dependencies.jar')
# path to soot_Type_DG
SOOT_TYPE_DG_PATH = os.path.join(MainProcess_pwd, 'utils/soot_Type_DG-1.0-SNAPSHOT-jar-with-dependencies.jar')
# path to revapi.sh
REVAPI_SH_PATH = os.path.join(MainProcess_pwd, 'utils', 'revapi-0.12.0', 'revapi.sh')