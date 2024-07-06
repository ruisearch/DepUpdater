# define the constants in this package
import os

MainProcess_pwd = os.getcwd()
DATA = f"data/"
## path to mvn dependency:tree log
DEPENDENCY_TREE_FILE = os.path.join(MainProcess_pwd, DATA + f"dependency_tree.txt")
## path to Jar folder in preprocess
JAR_FOLDER = os.path.join(MainProcess_pwd, DATA + f"Jar/")
## path to mvn dependency:tree -Dverbose log
DEPENDENCY_VERBOSE_TREE_FILE = os.path.join(MainProcess_pwd, DATA + f"dependency_verbose_tree.txt")