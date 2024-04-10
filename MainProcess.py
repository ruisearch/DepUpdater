import sys
import os
from preprocess import exec_maven_command
from preprocess import maven_shade_plugin
from preprocess import Jar
from match import match

## expand the path to absolute path
def expand_resolve_abspath(path):
    expanded_path = os.path.expanduser(path)
    resolved_path = os.path.normpath(expanded_path)
    absolute_path = os.path.abspath(resolved_path)
    return absolute_path

## preprocess: 
## input : the path to the cloned folder
## output ： client jar/ Uber jar / dependencies jar(from dependency tree)
print("\n****** preprocessing ... ******\n")
path_to_folder = expand_resolve_abspath(sys.argv[1])
path_to_pom = os.path.join(path_to_folder, "pom.xml")
# # declear maven-shade-plugin in pom.xml
# print("\n****** preprocess.package ... ******\n")
# maven_shade_plugin.insert(path_to_pom)
# # execute mvn clean and mvn package to generate Uber jar and jar
# exec_maven_command.mvn_package(path_to_folder)
# print("\n****** preprocess.package done! ******\n")
# # execute mvn dependency:tree to generate dependency tree file in convenience of extracting GAV of dependencies
# # result is in ./data/preprocess/dependency_tree.txt
# print("\n****** preprocess.analysis_tree ... ******\n")
# exec_maven_command.mvn_dependency_tree(path_to_folder)
# print("\n****** preprocess.analysis_tree done! ******\n")
# # parse dependency_tree.txt to get GAV of client jar and dependencies jar,
# # then download dependencies jar and copy client jar as well as Uber jar
# print("\n****** preprocess.getjar ... ******\n")
# Jar.Get(path_to_folder)
# print("\n****** preprocess.getjar done! ******\n")
# print("\n****** preprocess done! ******\n")

## match:
## input ：the ./data/Jar folder containing all jars
## output : the mapping from dep jars to APIs which are called directly or transitively by client
print("\n****** match ... ******\n")
match.all()
print("\n****** match done ! ******\n")