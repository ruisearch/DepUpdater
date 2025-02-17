import os
import json

def record_api(ret: list):
    """record all client-impacting API"""
    for dep in ret:
        if dep["Depth"] <= 1:
            continue
        if "Versions" in dep:
            versions = reversed(dep["Versions"])
            for version in versions:
                bc_reason = version["breaking_reason"]
                for reason in bc_reason:
                    if "api" in reason:
                        print(reason["api"], dep["GroupId"], dep["ArtifactId"], dep["Original_Version"],version["version"])
                        
def read_json(file_path: str):
    """read the json file"""
    with open(file_path, "r") as file:
        data = json.load(file)
    return data

def select_json():
    """select the json file"""
    root_dir_path = os.path.join("..","data","result")
    print(root_dir_path)
    json_files = []
    """递归读取root_dir_path下的所有子文件夹中的version.json文件"""
    for dir, _, files in os.walk(root_dir_path):
        for file in files:
            if file == "version.json":
                json_files.append(os.path.join(dir, file))
    return json_files

if __name__ == "__main__":
    json_files = select_json()
    for file in json_files:
        data = read_json(file)
        print(file)
        print('-------')
        record_api(data)