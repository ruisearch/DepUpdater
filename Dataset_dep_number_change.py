"""utilize the result of dataset to calculate the dep number change of each module after update
,which is not completed in the original code"""
import pandas as pd
import json
import os
from constants import DATA_DIR, TREE_DIR, RET_DIR
import concurrent.futures
from preprocess.Restore import Restore
import re
from logger import logger
from evaluation.dep_count import count_deps

def add_new_columns(row):
    """add new columns to the dataset.csv,
    new columns are the dep number change of each module after update and the reduced dep num
    """
    print(f"processing {row['repo']} : {row['module']}")
    if row['compile_success'] == '?':
        # '?' means the module can not compile before update, so skip such modules
        return pd.Series(['?', '?'])
    repo_path = os.path.join('/home/kaixuan/ray/SRC_dataset/', row['repo'])
    tree_path = os.path.join(TREE_DIR, row['repo'], row['module'], 'verbose_tree.txt')
    # compute the dep number before upgrade
    original_dep_count = compute_original_dep_number(tree_path, repo_path, row['module'])
    # compute the dep number after upgrade
    json_path = os.path.join(DATA_DIR, 'result', row['repo'], row['module'], 'version.json')
    current_dep_count = count_deps(json_path)
    return pd.Series([original_dep_count, current_dep_count, original_dep_count-current_dep_count])


def compute_original_dep_number(tree_path:str, path_to_cloned_folder:str, relative_path_to_module:str):
    """compute the original dependency number"""
    # extract the original dependency graph from verbose_tree.txt
    with open(tree_path, 'r') as f:
        tree = f.read()
    res = Restore(path_to_cloned_folder, relative_path_to_module, tree_path)
    # extract the original dependency graph from verbose_tree.txt
    # inspired by preprocess/Restore.py
    block_pattern = r'\[INFO\] Building .+?\n\[INFO\].+?from (.*?)pom.xml\n\[INFO\] -+?\[ (.+?) \]-+?\n.*?\[INFO\] (\S+?):(\S+?):\S+?:(\S+?)\n(.+?)\[INFO\] -'
    blocks = re.finditer(block_pattern, tree, flags=re.DOTALL)
    deps = None
    for block in blocks:
        if relative_path_to_module == '.':
            flag = (block.group(1) == '')
        elif relative_path_to_module.endswith('/'):
            # the second parameter represents the relative path to the module ends with '/'
            # block.group(1) endswith '/'
            flag = (block.group(1) == relative_path_to_module)
        else :
            flag = (block.group(1) == relative_path_to_module+'/')
        if block.group(2) == 'jar' and flag:
            res.client_groupId = block.group(3)
            res.client_artifactId = block.group(4)
            res.client_version = block.group(5)
            deps = res.parse_all_dep(block.group(6))
            break
    valid_deps, omitted_deps = res.filter_dep(deps)
    res.change_valid_deps(valid_deps)
    res.change_omitted_deps(omitted_deps)
    mappings = [{'GroupId':res.client_groupId, 'ArtifactId':res.client_artifactId,\
            'Original_Version':res.client_version, 'Best_Version':'', 'Type':'',\
                'Depth':0, 'Count':0, 'Dependents':[]}] # add client at first
    num_workers = os.cpu_count()
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = []
        for valid_dep in valid_deps:
            futures.append(executor.submit(res.process_a_valid_dep, valid_dep, omitted_deps))
    for future in futures:
        mappings.append(future.result())
    
    res.process_omitted_deps(valid_deps, omitted_deps, mappings)
    res.prune_graph(mappings)
    # mappings is the original dependency graph
    mappings = [node for node in mappings if node['Dependents'] or node['Depth'] == 0]
    # write mappings to original_version.json
    original_json_path = os.path.join(RET_DIR, os.path.base(path_to_cloned_folder), relative_path_to_module, 'original_version.json')
    with open(original_json_path, 'w') as f:
        json.dump(mappings, f, indent=4)
    return count_deps(original_json_path)

csv_path = os.path.join(DATA_DIR,'dataset.csv')
df = pd.read_csv(csv_path)
# add new columns to the dataset.csv
df [['original_dep_count', 'current_dep_count', 'reduced_dep_count']] = df.apply(add_new_columns, axis=1)

df.to_csv(csv_path, index=False)