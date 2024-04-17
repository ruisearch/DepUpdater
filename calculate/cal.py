## calculate best version and then calcute lag(after testing)
import os
import json
from calculate.constants import JAR_FOLDER
from calculate.Dep import Dep

## calculate best version for all dep in all module
def select_best_version():
# ## travel all subfolder in Jar folder
    # Jar_contents = os.listdir(JAR_FOLDER)
    # for item in JAR_FOLDER:
    #     item_path = os.path.join(JAR_FOLDER, item)
    #     ## item is a subfolder in Jar folder
    #     if os.path.isdir(item_path):

    ## test : just deal with one module folder in data/Jar
    # item_path = os.path.join(JAR_FOLDER, '2')
    item_path = os.path.join(JAR_FOLDER, '169')
    # travel the match.json and pass one dep for Dep
    json_path = os.path.join(item_path, f"dep/match.json")
    with open(json_path, 'r') as f:
        dict_list = json.load(f)
    for one_dict in dict_list:
        dep = Dep(one_dict)
        one_dict = one_dict.update({'AllVersion':dep.fetch_versions_sorted_by_date()})
    with open(json_path, 'w') as f:
        json.dump(dict_list, f, indent=4)
        
## calculate lag
def calculate_lag():
    print("cal")