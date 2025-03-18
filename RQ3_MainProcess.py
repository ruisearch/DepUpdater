"""Main process of the tool"""
import os
import sys
import csv
import argparse

from preprocess import exec_maven_command
from preprocess.rq3_Restore import Restore
from traverse.rq3_traverse import Traverse
from constants import set_log_path, set_soot_empty_cases_csv, VERSIONS_DIR
from preprocess import multiModule
from logger.logger import log_debug


def expand_resolve_abspath(path):
    """expand the path to absolute path"""
    expanded_path = os.path.expanduser(path)
    resolved_path = os.path.normpath(expanded_path)
    absolute_path = os.path.abspath(resolved_path)
    return absolute_path

args_parser = argparse.ArgumentParser()
args_parser.add_argument('-r', '--root', help='the path to the cloned folder')
args_parser.add_argument('-m', '--module', help='the relative path to the module')
args_parser.add_argument('-j', '--jar', help='the relative path to the client jar')
args_parser.add_argument('-l','--local_dep_jar', nargs='+', help='the relative paths to the local module jar depended by client')
args = args_parser.parse_args()
## preprocess
## input : the path to the cloned folder
## output ： client jar/dependencies jar(from dependency tree)
path_to_folder = expand_resolve_abspath(args.root)
path_to_pom = os.path.join(path_to_folder, "pom.xml")
# only handle the module in relative_path_to_module;'.' means the pom of the module is just at the root directory of project
relative_path_to_module = args.module
relative_path_to_module = relative_path_to_module.removeprefix('./')


# get all local module
local_module_inform = {}
if args.local_dep_jar:
    MULTI_MODULE_FLAG = True
else:
    # no local dependencies, so no need to consider multi-module
    MULTI_MODULE_FLAG = False
if MULTI_MODULE_FLAG:
    module_paths = multiModule.get_all_module(path_to_folder)
    for module_path in module_paths:
        # local_module_inform is a mapping from local module's gav to its relative path
        local_module_inform.update(multiModule.get_gav(module_path, path_to_folder))


# set path to log file and soot empty cases file
repo_name = os.path.basename(path_to_folder)
if relative_path_to_module == '.':
    # if the module is located at the root directory of the project
    # store the result of it in _ folder
    data_dir = os.path.join(VERSIONS_DIR, repo_name, '_')
else:
    data_dir = os.path.join(VERSIONS_DIR, repo_name, relative_path_to_module)
log_path = os.path.join(data_dir, 'RQ3_log.txt')
set_log_path(log_path)
soot_empty_csv = os.path.join(data_dir, 'soot_empty_cases.csv')
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


# remove all the outdated files in the result directory if exist
for file in os.listdir(data_dir):
    os.remove(os.path.join(data_dir, file))

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
# RQ 3中不需要test

# execute mvn dependency:tree to generate dependency tree file in convenience of extracting GAV of dependencies
# result is in ./data/preprocess/dependency_tree.txt
print("\n****** get tree ... ******\n")
# exec_maven_command.mvn_dependency_tree(path_to_folder, relative_path_to_module)
# tree_file : path to the file containing resulting tree
tree_file, exit_code = exec_maven_command.mvn_verbose_dependency_tree(path_to_folder, relative_path_to_module)
if exit_code != 0:
    print("\n****** module dependency tree fails. Please check the project ******\n")
    exit(exit_code)
print("\n****** tree got! ******\n")
# parse dependency_tree.txt to get GAV of client jar and dependencies jar,
# then download dependencies jar and copy client jar
print("\n****** restore dependency to graph ... ******\n")
graph = Restore(path_to_folder, relative_path_to_module, tree_file, local_module_inform, args.local_dep_jar)
json_path, original_json_path, local_dep_gav = graph.restore(args.jar)
print("\n****** dependency graph got! ******\n")
print("\n****** preprocess done! ******\n")
log_debug('\npreprocess done\n')

# # if the original tech lag is 0, then the module is already up-to-date
# if original_tech_lag[0] == 0:
#     print("\n ****** The module is already up-to-date ******\n")
#     log_debug('The module is already up-to-date')
#     print("\n****** result ******\n")
#     print('compile success:', True)
#     print('test pass:', True)
#     print('original technical lag:', 0)
#     print('current technical lag:', 0)
#     print('reduced technical lag:', 0)
#     print('original dependency count:', original_dep_count)
#     print('current dependency count:', original_dep_count)
#     print('reduced dependency count:', 0)
#     exit()

# Traverse the dependency graph to compute the newest compatible version of each dependency
log_debug(f"Start traversing for {repo_name}/{relative_path_to_module}")
tra = Traverse(json_path, path_to_folder, relative_path_to_module)
tra.traverse(local_dep_gav)
