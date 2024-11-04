"""utilize the result of dataset to calculate the tech lag reduction of each depth after upgrade
which is not computed in the original code
note: this script is not tested yet, it may contain bugs
"""
import pandas as pd
import os
from constants import DATA_DIR, TREE_DIR
from preprocess.Restore import Restore
import re
import concurrent.futures
from evaluation.tech_lag import TechLag
from logger import logger

def calculate_new_columns(row):
    """compute and add new columns to the row in dataset.csv"""
    print(f"processing {row['repo']} : {row['module']}")
    if row['compile_success'] == '?':
        # '?' means the module can not compile before update, so skip such modules
        return pd.Series(['?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?'])
    repo_path = os.path.join('/home/kaixuan/ray/SRC_dataset/', row['repo'])
    tree_path = os.path.join(TREE_DIR, row['repo'], row['module'], 'verbose_tree.txt')
    # compute the tech lag at each depth before upgrade
    original_depth_tech_lag = compute_original_depth_tech_lag(tree_path, repo_path, row['module'])
    # compute the tech lag at each depth after upgrade
    json_path = os.path.join(DATA_DIR, 'result', row['repo'], row['module'], 'version.json')
    current_depth_tech_lag = compute_current_depth_tech_lag(json_path)
    
    # too lengthy, need to refactor this. @Ray
    # return pd.Series([original_depth_tech_lag[1]-current_depth_tech_lag[1], \
    #     original_depth_tech_lag[2]-current_depth_tech_lag[2], original_depth_tech_lag[3]-current_depth_tech_lag[3],\
    #         original_depth_tech_lag[4]-current_depth_tech_lag[4], original_depth_tech_lag[5]-current_depth_tech_lag[5], \
    #             original_depth_tech_lag[6]-current_depth_tech_lag[6], original_depth_tech_lag[7]-current_depth_tech_lag[7], \
    #                 original_depth_tech_lag[8]-current_depth_tech_lag[8], original_depth_tech_lag[9]-current_depth_tech_lag[9],\
    #                     original_depth_tech_lag[10]-current_depth_tech_lag[10]], \
    #                         original_depth_tech_lag[11]-current_depth_tech_lag[11])
    return pd.Series([original_depth_tech_lag[i]-current_depth_tech_lag[i] for i in range(1, 12)])

def compute_original_depth_tech_lag(tree_path:str, path_to_cloned_folder:str, relative_path_to_module:str):
    """compute the original tech lag of each depth"""
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
    mappings = [node for node in mappings if node['Dependents'] or node['Depth'] == 0]
    # get original tech lag(sum and each depth 1 ~ 10 and >10)
    original_tech_lag = res.compute_original_tech_lag(mappings)
    return original_tech_lag

def compute_current_depth_tech_lag(json_path:str):
    lag = TechLag(json_path)
    return lag.current_lag

csv_path = os.path.join(DATA_DIR,'dataset.csv')
df = pd.read_csv(csv_path)
# add new columns to the dataset.csv
df[['1_depth_reduction', '2_depth_reduction', '3_depth_reduction', '4_depth_reduction', '5_depth_reduction',\
    '6_depth_reduction', '7_depth_reduction', '8_depth_reduction', '9_depth_reduction', \
        '10_depth_reduction', 'more_than_10_depth_reduction']] = df.apply(calculate_new_columns, axis=1)

df.to_csv(csv_path, index=False)