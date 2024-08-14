"""Main process of the tool"""
import os
import sys

from calculate import cal
from match import match
from preprocess import exec_maven_command
from preprocess.Restore import Restore


def expand_resolve_abspath(path):
    """expand the path to absolute path"""
    expanded_path = os.path.expanduser(path)
    resolved_path = os.path.normpath(expanded_path)
    absolute_path = os.path.abspath(resolved_path)
    return absolute_path

## preprocess
## input : the path to the cloned folder
## output ： client jar/dependencies jar(from dependency tree)
print("\n****** preprocessing ... ******\n")
path_to_folder = expand_resolve_abspath(sys.argv[1])
path_to_pom = os.path.join(path_to_folder, "pom.xml")
# only handle the module in relative_path_to_module;'.' means the pom of the module is just at the root directory of project
relative_path_to_module = sys.argv[2]
# set the git repository to the last tag status
status_command = f'cd {path_to_folder} && git add . && git reset --hard && git fetch --tags && git tag --sort=-creatordate | head -1 | xargs git checkout'
print("****** set the git repository to the lastest tag status ******")
os.system(status_command)
print("\n****** preprocess.package ... ******\n")
exit_code = exec_maven_command.mvn_package(path_to_folder, relative_path_to_module)
if exit_code != 0:
    print("\n****** module package fails. Please check the project ******\n")
    exit()
print("\n****** preprocess.package done! ******\n")
# execute mvn dependency:tree to generate dependency tree file in convenience of extracting GAV of dependencies
# result is in ./data/preprocess/dependency_tree.txt
print("\n****** get tree ... ******\n")
# exec_maven_command.mvn_dependency_tree(path_to_folder, relative_path_to_module)
# tree_file : path to the file containing resulting tree
tree_file = exec_maven_command.mvn_verbose_dependency_tree(path_to_folder, relative_path_to_module)
print("\n****** tree got! ******\n")
# parse dependency_tree.txt to get GAV of client jar and dependencies jar,
# then download dependencies jar and copy client jar
print("\n****** restore dependency to graph ... ******\n")
graph = Restore(path_to_folder, relative_path_to_module, tree_file)
json_path = graph.restore()
print("\n****** dependency graph got! ******\n")
print("\n****** preprocess done! ******\n")

# # match:
# # input ：the ./data/Jar folder containing all jars
# # output : the mapping from dep jars to APIs which are called directly or transitively by client
# print("\n****** match ... ******\n")
# # match.all(relative_path_to_module)
# match.all()
# print("\n****** match done ! ******\n")

# # create folder to contain false_cases; the false negative cases and false positive cases will be stored in false_cases/
# # project_error_folder(like _home_ray_Work_Tool_Data_fudan_paper_client_584_java-design-patterns/ in false_cases/) represents a project rather than a module
# # False_case_path is the folder to store false cases/
# False_case_path = os.path.join(os.getcwd(), 'false_cases/')
# project_name = path_to_folder.replace('/','_')
# project_error_folder = os.path.join(False_case_path, project_name)
# if os.path.isdir(project_error_folder) is False:
#     # if project_error_folder doesn't exist, create one
#     # don't delete the existing one as the it may contain other modules
#     # note: folder representing module of the project is the subfolder of project_error_folder
#     os.makedirs(project_error_folder)
    

# ## calculate:
# ## input : the ./data/Jar folder containing version.json
# ## output : the newest compatible version of each dep in version.json and finial lag result(after test)
# print("\n****** calculate: ******\n")
# cal.select_best_version(path_to_folder, project_error_folder)
# cal.calculate_lag()
# print("\n****** calculate done ! ******\n")
