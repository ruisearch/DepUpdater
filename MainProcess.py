import sys
import os
from preprocess import exec_maven_command
from preprocess import maven_shade_plugin

## preprocess: 
## input : the path to the cloned folder
## output ： client jar/ Uber jar / dependency tree file
path_to_folder = os.path.normpath(sys.argv[1])
path_to_pom = os.path.join(path_to_folder, "pom.xml")
# declear maven-shade-plugin in pom.xml
maven_shade_plugin.insert(path_to_pom)
exec_maven_command.mvn_package(path_to_folder)