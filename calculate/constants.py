# define the constants in this package
import os

MainProcess_pwd = os.getcwd()
DATA = f"data/"
## absolute path to mvn dependency:tree log
DEPENDENCY_TREE_FILE = os.path.join(MainProcess_pwd, DATA + f"dependency_tree.txt")
## absolute path to Jar folder in data
JAR_FOLDER = os.path.join(MainProcess_pwd, DATA + f"Jar/")

## absolute path to revapi-0.12.0 folder
REVAPI_FOLDER = os.path.join(MainProcess_pwd, 'utils/revapi-0.12.0/')

## absolute to BCEL_method_addedToInterface-1.0-SNAPSHOT-jar-with-dependencies.jar
ADDEDTOINTERFACE_PATH = os.path.join(MainProcess_pwd, 'utils/BCEL_method_addedToInterface-1.0-SNAPSHOT-jar-with-dependencies.jar')

## absolute to tqdm_log/
TQDM_LOG_PATH = os.path.join(MainProcess_pwd, 'tqdm_log/')