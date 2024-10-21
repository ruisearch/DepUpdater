"""Main process of the tool"""
import os
import sys
import csv


from preprocess import exec_maven_command
from preprocess.Restore import Restore
from traverse.traverse import Traverse
from constants import set_log_path, set_soot_empty_cases_csv, RET_DIR, DATA_DIR
from evaluation.tech_lag import TechLag
from logger.logger import log_debug


def expand_resolve_abspath(path):
    """expand the path to absolute path"""
    expanded_path = os.path.expanduser(path)
    resolved_path = os.path.normpath(expanded_path)
    absolute_path = os.path.abspath(resolved_path)
    return absolute_path

## preprocess
## input : the path to the cloned folder
## output ： client jar/dependencies jar(from dependency tree)
path_to_folder = expand_resolve_abspath(sys.argv[1])
path_to_pom = os.path.join(path_to_folder, "pom.xml")
# only handle the module in relative_path_to_module;'.' means the pom of the module is just at the root directory of project
relative_path_to_module = sys.argv[2]
# set path to log file and soot empty cases file
repo_name = os.path.basename(path_to_folder)
log_path = os.path.join(RET_DIR, repo_name, relative_path_to_module, 'log.txt')
set_log_path(log_path)
soot_empty_csv = os.path.join(RET_DIR, repo_name, relative_path_to_module, 'soot_empty_cases.csv')
set_soot_empty_cases_csv(soot_empty_csv)
# remove existing soot empty cases file
if os.path.exists(soot_empty_csv):
    os.remove(soot_empty_csv)
# remove existing log file
if os.path.exists(log_path):
    os.remove(log_path)
# create the directory for result if not exist
if not os.path.exists(os.path.dirname(log_path)):
    os.makedirs(os.path.dirname(log_path))

print("\n****** preprocessing ... ******\n")
log_debug(f"Start preprocessing for {repo_name}/{relative_path_to_module}")

# set the git repository to the last tag status
# status_command = f'cd {path_to_folder} && git add . && git reset --hard && git fetch --tags && git tag --sort=-creatordate | head -1 | xargs git checkout'
status_command = f'cd {path_to_folder} && git add . && git stash && git stash clear'
print("****** set the git repository to the lastest tag status ******")
os.system(status_command)
print("\n****** preprocess.package ... ******\n")
exit_code = exec_maven_command.mvn_package(path_to_folder, relative_path_to_module)
if exit_code != 0:
    print("\n****** module package fails. Please check the project ******\n")
    exit()
print("\n****** preprocess.package done! ******\n")
exit_code = exec_maven_command.mvn_test(path_to_folder, relative_path_to_module)
original_test_flag = True
if exit_code != 0:
    print("\n****** module test fails. Please check the project ******\n")
    original_test_flag = False

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
json_path, original_tech_lag = graph.restore()
print("\n****** dependency graph got! ******\n")
print("\n****** preprocess done! ******\n")
log_debug('\npreprocess done\n')

# Traverse the dependency graph to compute the newest compatible version of each dependency
log_debug(f"Start traversing for {repo_name}/{relative_path_to_module}")
tra = Traverse(json_path, path_to_folder, relative_path_to_module)
compile_flag, test_flag = tra.traverse()

# compute the technical lag of the module
print("\n****** compute technical lag ... ******\n")
log_debug(f"Start computing tech lag for {repo_name}/{relative_path_to_module}")
lag = TechLag(json_path)
# record the original lag, current lag and reduced lag in a csv file
lag_csv_path = os.path.join(DATA_DIR, 'lag.csv')
with open(lag_csv_path, 'a') as f:
    writer = csv.writer(f)
    writer.writerow([repo_name, relative_path_to_module, original_tech_lag, lag.current_lag, original_tech_lag - lag.current_lag])

# print the result of the tool
print("\n****** result ******\n")
print('compile success:', compile_flag)
print('original test pass:', original_test_flag)
print('test pass:', test_flag)
print('original technical lag:', original_tech_lag)
print('current technical lag:', lag.current_lag)
print('reduced technical lag:', original_tech_lag - lag.current_lag)