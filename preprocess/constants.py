# define the constants in this package
import os

MainProcess_pwd = os.getcwd()
PREPROCESS = f"out/preprocess/"
## path to mvn dependency:tree log
DEPENDENCY_TREE_FILE = os.path.join(MainProcess_pwd, PREPROCESS + f"dependency_tree.txt")
## path to Jar folder in preprocess
JAR_FOLDER = os.path.join(MainProcess_pwd, PREPROCESS + f"Jar/")
