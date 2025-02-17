"""
    count the client-impacting transitive api from the result of our tool
    to validate RQ3

"""
import os
import json

def record_api(dep: dict):
    """
        record the client-impacting transitive api of a dependencies under MMP, mMP, mmP
        Args:
            dep: the transitive dependency extracted from version.json
    """
    # find the MMP, mMP, mmP versions
    original_version = dep["Original_Version"]
    original_major = original_version.split(".")[0]
    original_minor = original_version.split(".")[1] if len(original_version.split(".")) > 1 else 0
    MMP_version = ""
    mMP_version = ""
    mmP_version = ""
    if "Versions" in dep:
        versions = reversed(dep["Versions"])
        for version in versions:
            version_name = version["version"]
            major = version_name.split(".")[0]
            minor = version_name.split(".")[1] if len(version_name.split(".")) > 1 else 0
            MMP_version = version_name
            if major == original_major:
                mMP_version = version_name
            if major == original_major and minor == original_minor:
                mmP_version = version_name

    # record the client-impacting transitive api under MMP, mMP, mmP
    MMP_api = []
    mMP_api = []
    mmP_api = []
    MMP_debloating_count = 0
    MMP_semver_count = 0
    mMP_debloating_count = 0
    mMP_semver_count = 0
    mmP_debloating_count = 0
    mmP_semver_count = 0

    if "Versions" in dep:
        versions = dep["Versions"]
        for version in versions:
            bc_reason = version["breaking_reason"]
            if version["version"] == MMP_version:
                for reason in bc_reason:
                    if "api" in reason:
                        api = reason["api"]
                        MMP_api.append(api)
                    if reason == "software debloating":
                        MMP_debloating_count += 1
                    if "by semantic versioning" in reason:
                        MMP_semver_count += 1

            if version["version"] == mMP_version:
                for reason in bc_reason:
                    if "api" in reason:
                        api = reason["api"]
                        mMP_api.append(api)
                    if reason == "software debloating":
                        mMP_debloating_count += 1
                    if "by semantic versioning" in reason:
                        mMP_semver_count += 1

            if version["version"] == mmP_version:
                for reason in bc_reason:
                    if "api" in reason:
                        api = reason["api"]
                        mmP_api.append(api)
                    if reason == "software debloating":
                        mmP_debloating_count += 1
                    if "by semantic versioning" in reason:
                        mmP_semver_count += 1

    return MMP_api, mMP_api, mmP_api,\
        MMP_debloating_count, MMP_semver_count, \
            mMP_debloating_count, mMP_semver_count, \
                mmP_debloating_count, mmP_semver_count

def get_current_dep(original_dep:dict, module_dir:str):
    """
        get the current dependency in version.json
        Args:
            original_dep: the original dependency in original_version.json    
            module_dir: the result directory of the module
    """
    current_dep = {}
    version_file = os.path.join(module_dir, "version.json")
    if os.path.exists(version_file):
        data = read_json(version_file)
        for dep in data:
            if dep["GroupId"] == original_dep["GroupId"] and dep["ArtifactId"] == original_dep["ArtifactId"]:
                current_dep = dep
                break
    return current_dep

def read_json(file_path: str):
    """read the json file"""
    with open(file_path, "r") as file:
        data = json.load(file)
    return data

def select_json():
    """select the json file"""
    root_dir_path = os.path.join("..","data","result")
    json_files = []
    """递归读取root_dir_path下的所有子文件夹中的original_version.json文件"""
    for dir, _, files in os.walk(root_dir_path):
        for file in files:
            if file == "version.json":
                json_files.append(os.path.join(dir, file))
    print(len(json_files))
    return json_files

def get_max_depth(json_files: list):
    """
        get the maximum depth of the dependencies
        Args:
            json_files: the list of original_version.json files
    """
    max_depth = 0
    for file in json_files:
        data = read_json(file)
        for dep in data:
            if dep["Depth"] > max_depth:
                max_depth = dep["Depth"]
    return max_depth

if __name__ == "__main__":
    json_files = select_json()
    max_depth = get_max_depth(json_files)
    for depth in range(2, max_depth+1):
        total_MMP = []
        total_mMP = []
        total_mmP = []
        total_MMP_debloating = 0
        total_MMP_semver = 0
        total_mMP_debloating = 0
        total_mMP_semver = 0
        total_mmP_debloating = 0
        total_mmP_semver = 0
        
        for json_file in json_files:
            module_dir = os.path.dirname(json_file)
            data = read_json(json_file)
            for dep in data:
                if dep["Depth"] == depth:
                    current_dep = get_current_dep(dep, os.path.dirname(json_file))
                    MMP,mMP,mmP,\
                        MMP_debloating, MMP_semver,\
                            mMP_debloating, mMP_semver,\
                                mmP_debloating, mmP_debloating= record_api(current_dep)
                    total_MMP.extend(MMP)
                    total_mMP.extend(mMP)
                    total_mmP.extend(mmP)
                    total_MMP_debloating += MMP_debloating
                    total_MMP_semver += MMP_semver
                    total_mMP_debloating += mMP_debloating
                    total_mMP_semver += mMP_semver
                    total_mmP_debloating += mmP_debloating
        print("Depth: ", depth, "\nMMP: ", len(total_MMP), "mMP: ", len(total_mMP), "mmP: ", len(total_mmP))
        print("MMP debloating: ", total_MMP_debloating, "MMP semver: ", total_MMP_semver)
        print("mMP debloating: ", total_mMP_debloating, "mMP semver: ", total_mMP_semver)
        print("mmP debloating: ", total_mmP_debloating, "mmP semver: ", total_mmP_semver)
        print("===============================================")
        
        # print("MMP: ", total_MMP)
        # print("mMP: ", total_mMP)
        # print("mmP: ", total_mmP)