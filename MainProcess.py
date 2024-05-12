import sys
import os
from preprocess import exec_maven_command
from preprocess import Jar
from match import match
from calculate import cal

## expand the path to absolute path
def expand_resolve_abspath(path):
    expanded_path = os.path.expanduser(path)
    resolved_path = os.path.normpath(expanded_path)
    absolute_path = os.path.abspath(resolved_path)
    return absolute_path

## preprocess: 
## input : the path to the cloned folder
## output ： client jar/dependencies jar(from dependency tree)
print("\n****** preprocessing ... ******\n")
path_to_folder = expand_resolve_abspath(sys.argv[1])
path_to_pom = os.path.join(path_to_folder, "pom.xml")
# only handle the module in relative_path_to_module;'.' means handling all modules or the project has just one module whose pom is at the root of the project
relative_path_to_module = sys.argv[2]
print("\n****** preprocess.package ... ******\n")
exit_code = exec_maven_command.mvn_package(path_to_folder, relative_path_to_module)
if exit_code != 0:
    print("\n****** module package fails. Please check the project ******\n")
    exit()
print("\n****** preprocess.package done! ******\n")
# execute mvn dependency:tree to generate dependency tree file in convenience of extracting GAV of dependencies
# result is in ./data/preprocess/dependency_tree.txt
print("\n****** preprocess.analysis_tree ... ******\n")
exec_maven_command.mvn_dependency_tree(path_to_folder)
print("\n****** preprocess.analysis_tree done! ******\n")
# parse dependency_tree.txt to get GAV of client jar and dependencies jar,
# then download dependencies jar and copy client jar
print("\n****** preprocess.getjar ... ******\n")
Jar.Get(path_to_folder, relative_path_to_module)
print("\n****** preprocess.getjar done! ******\n")
print("\n****** preprocess done! ******\n")

# match:
# input ：the ./data/Jar folder containing all jars
# output : the mapping from dep jars to APIs which are called directly or transitively by client
print("\n****** match ... ******\n")
match.all(relative_path_to_module)
# match.all(relative_path_to_module)
print("\n****** match done ! ******\n")

# create folder to contain false_cases; the false negative cases and false positive cases will be stored in false_cases/
# project_error_folder represents a project. the folder won't be deleted by this script, can only be created
# if it is outdated, please remove project_error_folder firstly
# False_case_path is the folder to store false cases(already exists)
False_case_path = os.path.join(os.getcwd(), 'false_cases/')
project_name = path_to_folder.replace('/','_')
project_error_folder = os.path.join(False_case_path, project_name)
if os.path.isdir(project_error_folder) is False:
    os.makedirs(project_error_folder)
    

## calculate:
## input : the ./data/Jar folder containing match.json
## output : the newest compatible version of each dep in match.json and finial lag result(after test)
print("\n****** calculate: ******\n")
cal.select_best_version(path_to_folder, project_error_folder)
cal.calculate_lag()
print("\n****** calculate done ! ******\n")
