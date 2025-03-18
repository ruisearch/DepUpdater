import os
import json
import pandas as pd


def get_MMP_mMP_mmP_versions(original_version:str, candidate_versions:list):
    """get the MMP, mMP, mmP versions of the original version"""
    original_major = original_version.split(".")[0]
    original_minor = original_version.split(".")[1] if len(original_version.split(".")) > 1 else 0
    resulting_versions = []
    MMP_version = ""
    mMP_version = ""
    mmP_version = ""
    for version in reversed(candidate_versions):
        # reversed: from old to new
        major = version.split(".")[0]
        minor = version.split(".")[1] if len(version.split(".")) > 1 else 0
        MMP_version = version
        if major == original_major:
            mMP_version = version
        if major == original_major and minor == original_minor:
            mmP_version = version
    resulting_versions.append(MMP_version)
    resulting_versions.append(mMP_version)
    resulting_versions.append(mmP_version)
    return resulting_versions

def get_breaking_change_count(dest_version: str, versions: list):
    for v in versions:
        if v.get("version", "") == dest_version:
            return len(list(filter(lambda x: "api" in x, v.get("breaking_reason", []))))
    return 0

def read_json_file(path):
    
    # print(path)
    
    mmp_raw_data = json.load(open(path))
    _result = list()
    for module in filter(lambda d: d.get("Depth", 0) >= 2, mmp_raw_data):
        if "Versions" not in module:
            print(f"Waring: module {module} no versions")
            continue
        if len(module["Versions"]) < 1:
            print(f"Waring: module {module} only one version")
        origin_version = module["Original_Version"]
        versions = module.get("Versions", [])
        MMP, mMP, mmP = get_MMP_mMP_mmP_versions(origin_version, list(map(lambda x: x.get("version", ""), versions)))
        d = {
            "depth": module["Depth"],
            "MMP": get_breaking_change_count(MMP, versions) if MMP != origin_version else 0,
            "mMP": get_breaking_change_count(mMP, versions) if mMP != origin_version else 0,
            "mmP": get_breaking_change_count(mmP, versions) if mmP != origin_version else 0,
        }
        # print(module["ArtifactId"], origin_version, f"MMP: {d.get('MMP')}@{MMP}, mMP: {d.get('mMP')}@{mMP}, mmP: {d.get('mmP')}@{mmP}")
        _result.append(d)
    return _result

def find_version_json(root_dir):
    import os
    version_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        if "version.json" in filenames:
            version_files.append(os.path.join(dirpath, "version.json"))
    return version_files

def extract_path(dataset_dir: str, module_path: str) -> (str, str, str):
    import os
    relative_path = module_path.removeprefix(dataset_dir.removesuffix(os.path.sep)).removeprefix(os.path.sep).removesuffix(os.path.sep)
    print(relative_path)
    split_path = relative_path.split(os.path.sep)
    return split_path[0], split_path[-1], relative_path

if __name__ == "__main__":
    # paths = [
    #     ('mall', 'module_name', './version.json')
    # ]
    #
    # export = pd.DataFrame(columns=['repo', 'module', 'depth', 'MMP', 'mMP', 'mmP'])
    #
    # result_dir = ""
    # for (repo, module, p) in paths:
    #     result = read_json_file(p)
    #     r = pd.DataFrame(result).groupby("depth", as_index=False).sum()
    #     r["repo"] = repo
    #     r["module"] = module
    #
    #     export = pd.concat([export, r], ignore_index=True)
    #
    # export.to_csv("./rqs2.csv", index=False)


    # # 现有json位置写法
    # export = pd.DataFrame(columns=['repo', 'module', 'depth', 'MMP', 'mMP', 'mmP'])

    # result_dir = os.path.join("data", "rq3_result")
    # for p in find_version_json(result_dir):
    #     print(p)
    #     repo_name, module_name, relative_path = extract_path(result_dir, p.removesuffix("version.json"))
    #     # for (repo, module, p) in paths:
    #     result = read_json_file(p)
    #     r = pd.DataFrame(result, columns=['depth', 'MMP', 'mMP', 'mmP'], dtype=int).groupby("depth", as_index=False).sum()

    #     r["repo"] = repo_name
    #     r["module"] = module_name if module_name != "_" else "."
    #     export = pd.concat([export, r], ignore_index=True)

    # export.to_csv(os.path.join("data","rq3_module_api_count.csv"), index=False)

    # # 从processed.csv读取写法
    export = pd.DataFrame(columns=['repo', 'module', 'depth', 'MMP', 'mMP', 'mmP'])
    df = pd.read_csv(os.path.join("data", "rq3_processed.csv"))
    # result_dir=os.path.join("data", "rq3_result")
    result_dir=os.path.join("data", "extended_rq3_result")
    for _, row in df.iterrows():
        if row["process"] == False:
            continue
        root_module_dir = os.path.join(row["repo"], "_")
        json_path = os.path.join(result_dir,\
            row["relative_path"] if row["relative_path"] != row["repo"] else root_module_dir, "version.json")
        if not os.path.exists(json_path):
            print(f"Warning: {json_path} not exist")
            continue
        result = read_json_file(json_path)
        r = pd.DataFrame(result,columns=['depth', 'MMP', 'mMP', 'mmP']).groupby("depth", as_index=False).sum()
        r["repo"] = row["repo"]
        # r["module"] = row["module"] if row["relative_path"] != row["repo"] else "."
        r["module"] = row["relative_path"].removeprefix(row["repo"]+"/") if row["relative_path"] != row["repo"] else "."
        export = pd.concat([export, r], ignore_index=True)
    
    export.to_csv(os.path.join("data","rq3_module_api_count.csv"), index=False)
