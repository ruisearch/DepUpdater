import sys
from preprocess import exec_maven_command

## preprocess: 
## input : the path to the cloned folder
## output ： client jar/ Uber jar / dependency tree file
path_to_folder = sys.argv[1]
# declear maven-shade-plugin in pom.xml
exec_maven_command.mvn_package(path_to_folder)