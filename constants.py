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
    | | | ├── log.txt
    | | | ├── soot_empty_cases.csv 
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
    | ├── {repo_name}/
    | | ├── {relative_path_to_module}/
    | | | ├── {groupId}_{artifactId}.tqdm_log.txt
    | ...
    ├── validation_log/
    | ├── {repo_name}/
    | | ├── {relative_path_to_module}/
    | | | ├── {group_id}/
    | | | | ├── {artifact_id}/
    | | | | | ├── {version}/
    | | | | | | ├── recompile.txt
    | | | | | | ├── binary_bc_api.json
    ├── pom/
    | ├── errored.csv
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
# path to data/validation_log/
VALIDATION_LOG_DIR = os.path.join(DATA_DIR, 'validation_log/')
# path to pom, which store the pom.xml used to update mongodb temporarily
POM_PATH = os.path.join(DATA_DIR, 'pom/')

# path to sootCG
SOOTCG_PATH = os.path.join(MainProcess_pwd, 'utils/sootCG-1.0-SNAPSHOT-jar-with-dependencies.jar')
# path to soot_Type_DG
SOOT_TYPE_DG_PATH = os.path.join(MainProcess_pwd, 'utils/soot_Type_DG-1.0-SNAPSHOT-jar-with-dependencies.jar')
# path to revapi.sh
REVAPI_SH_PATH = os.path.join(MainProcess_pwd, 'utils', 'revapi-0.12.0', 'revapi.sh')
# path to BCELgetMethod
BCEL_METHOD_PATH = os.path.join(MainProcess_pwd, 'utils', 'BCELgetMethod-1.0-SNAPSHOT-jar-with-dependencies.jar')
# path to BCELgetType
BCEL_TYPE_PATH = os.path.join(MainProcess_pwd, 'utils', 'BCELgetType-1.0-SNAPSHOT-jar-with-dependencies.jar')
# path to japicmp-0.18.3-jar-with-dependencies.jar
JAPICMP_PATH = os.path.join(MainProcess_pwd, 'utils', 'japicmp-0.18.3-jar-with-dependencies.jar')
# path to local maven repository, '~/.m2/repository/' default
M2_PATH = os.path.expanduser('~') + '/.m2/repository/'

# path to the log file. set in process
LOG_PATH = None
# path to the soot empty cases file. set in process
SOOT_EMPTY_CASES_CSV = None

def set_log_path(path:str):
    """lazy-initialize LOG_PATH"""
    global LOG_PATH
    LOG_PATH = path

def set_soot_empty_cases_csv(path:str):
    """lazy-initialize SOOT_EMPTY_CASES_CSV"""
    global SOOT_EMPTY_CASES_CSV
    SOOT_EMPTY_CASES_CSV = path

def get_log_path():
    """get LOG_PATH after setting"""
    global LOG_PATH
    return LOG_PATH

# get SOOT_EMPTY_CASES_CSV after setting
def get_soot_empty_cases_csv():
    """get SOOT_EMPTY_CASES_CSV after setting"""
    global SOOT_EMPTY_CASES_CSV
    return SOOT_EMPTY_CASES_CSV