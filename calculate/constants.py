# define the constants in this package
import os

MainProcess_pwd = os.getcwd()
DATA = f"data/"
## absolute path to mvn dependency:tree log
DEPENDENCY_TREE_FILE = os.path.join(MainProcess_pwd, DATA + f"dependency_tree.txt")
## absolute path to Jar folder in data
JAR_FOLDER = os.path.join(MainProcess_pwd, DATA + f"Jar/")

##  