# define the constants in this package
import os
## path to mvn dependency:tree log
MainProcess_pwd = os.getcwd()
PREPROCESS = "out/preprocess/"
DEPENDENCY_TREE_FILE = os.path.join(MainProcess_pwd, PREPROCESS + f"dependency_tree.txt")