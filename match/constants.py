# define the constants in this package
import os

MainProcess_pwd = os.getcwd()
DATA = f"data/"
## absolute path to mvn dependency:tree log
DEPENDENCY_TREE_FILE = os.path.join(MainProcess_pwd, DATA + f"dependency_tree.txt")
## absolute path to Jar folder in preprocess
JAR_FOLDER = os.path.join(MainProcess_pwd, DATA + f"Jar/")

# absolute path to utils/sootCG
UTILS = os.path.join(MainProcess_pwd, "utils/")
SOOTCG_PATH = os.path.join(UTILS, "sootCG-1.0-SNAPSHOT-jar-with-dependencies.jar")

# absolute path to utils/BCELgetAPI
BCEL_PATH = os.path.join(UTILS, f"BCELgetAPI-1.0-SNAPSHOT-jar-with-dependencies.jar")
