## calculate best version and then calcute lag(after testing)
import os
import json
from calculate.constants import JAR_FOLDER
from calculate.Dep import Dep

## calculate best version for all dep in all modules or specific module
def select_best_version(relative_path_to_module:str):
    ## handle all modules
    if relative_path_to_module == '.':
        Jar_contents = os.listdir(JAR_FOLDER)
        for item in Jar_contents:
            item_path = os.path.join(JAR_FOLDER, item)
            ## item is a subfolder in Jar folder
            if os.path.isdir(item_path):
                # travel the match.json and pass one dep for Dep
                json_path = os.path.join(item_path, f"dep/match.json")
                dep_path = os.path.join(item_path, f"dep/")
                with open(json_path, 'r') as f:
                    dict_list = json.load(f)
                for one_dict in dict_list:
                    dep = Dep(one_dict, dep_path)
                    # get all version of each dep
                    one_dict.update({'AllVersion':dep.fetch_versions_sorted_by_date()})
                    # get the newest compatible versoin
                    one_dict.update({'BestVersion':dep.get_best_version()})
                with open(json_path, 'w') as f:
                    json.dump(dict_list, f, indent=4)
    ## handle a specific module
    ## test : just deal with one module folder in data/Jar
    # item_path = os.path.join(JAR_FOLDER, '148')
    # item_path = os.path.join(JAR_FOLDER, '3')
    # item_path = os.path.join(JAR_FOLDER, '169')
    # item_path = os.path.join(JAR_FOLDER, '165')
    # item_path = os.path.join(JAR_FOLDER, '2')
    # travel the match.json and pass one dep for Dep
    else:
        items = os.listdir(JAR_FOLDER)
        for item in items:
            if os.path.isdir(os.path.join(JAR_FOLDER, item)):
                item_path = os.path.join(JAR_FOLDER, item)
                break
        json_path = os.path.join(item_path, f"dep/match.json")
        dep_path = os.path.join(item_path, f"dep/")
        with open(json_path, 'r') as f:
            dict_list = json.load(f)
        for one_dict in dict_list:
            dep = Dep(one_dict, dep_path)
            # get all version of each dep
            print(f"-- sort versions of {one_dict['GroupId']}:{one_dict['ArtifactId']} ... -- ")
            one_dict.update({'AllVersion':dep.fetch_versions_sorted()})
            # get the newest compatible versoin
            print(f"-- calculate best version of {one_dict['GroupId']}:{one_dict['ArtifactId']} ... -- ")
            one_dict.update({'BestVersion':dep.get_best_version()})
            print(f"-- best version got -- ")
        with open(json_path, 'w') as f:
            json.dump(dict_list, f, indent=4)
            
## calculate lag
def calculate_lag():
    print("cal")