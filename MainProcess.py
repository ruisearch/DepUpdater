import sys
import os
from preprocess import exec_maven_command
from preprocess import maven_shade_plugin

## preprocess: 
## input : the path to the cloned folder
## output ： client jar/ Uber jar / dependencies jar(from dependency tree)
path_to_folder = os.path.normpath(sys.argv[1])
path_to_pom = os.path.join(path_to_folder, "pom.xml")
# declear maven-shade-plugin in pom.xml
maven_shade_plugin.insert(path_to_pom)
# execute mvn clean and mvn package to generate Uber jar and jar
exec_maven_command.mvn_package(path_to_folder)
# execute mvn dependency:tree to generate dependency tree file in convenience of extracting GAV of dependencies
# result is in ./out/preprocess/dependency_tree.txt
exec_maven_command.mvn_dependency_tree(path_to_folder)
# parse dependency_tree.txt to get GAV of client jar and dependencies jar
