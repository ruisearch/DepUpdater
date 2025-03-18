import os
import subprocess

import pandas as pd
from tqdm import tqdm


def find_maven_projects(dataset_dir):
    return map(
        lambda p, : p[0],
        # abs_path, dirs, files
        filter(lambda pdf: "src" in pdf[1] and "pom.xml" in pdf[2], os.walk(dataset_dir))
    )

def process(abs_module_path, repo_name, module_name, relative_path) -> bool:
    
    # print(cmd)
    # cmd = [""]
    # cmd = ["python3", "RQ3_MainProcess.py", "-r", abs_module_path, "-m", relative_path]
    # try:
    #     subprocess.check_call(cmd, text=True)
    #     return True
    # except Exception as e:
    #     print(e)
    #     return False
    # todo: 把cmd执行过程中原来输出到终端的内容写入到文件中。
    # 文件地址见get_log_path

    # try:
    #     with open(get_log_path(repo_name, relative_path), "w") as f:
    #         subprocess.check_call(cmd, text=True, stdout=f, stderr=f)
    #     # subprocess.run(cmd, shell=True, text=True, capture_output=True)
    #     return True
    # except Exception as e:
    #     print(e)
    #     return False
    
    # result = subprocess.run(cmd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    # write_log(repo_name, relative_path, result.stdout)
    # return result.returncode == 0
    
    cmd = f"python3 RQ3_MainProcess.py -r {abs_module_path} -m {relative_path}"
    result = subprocess.run(cmd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    write_log(repo_name, relative_path, result.stdout+result.stderr)
    return result.returncode == 0


def get_log_path(repo_name, relative_path):
    if relative_path == ".":
        # module_dir = os.path.join("data", "rq3_result", repo_name, "_")
        module_dir = os.path.join("data", "extended_rq3_result", repo_name, "_")
    else:
        # module_dir = os.path.join("data", "rq3_result", repo_name, relative_path)
        module_dir = os.path.join("data", "extended_rq3_result", repo_name, relative_path)
    os.makedirs(module_dir, exist_ok=True)
    return os.path.join(module_dir, "stdout.txt")

def write_log(repo, relative_path, log):
    with open(get_log_path(repo, relative_path), "w") as f:
        f.write(log)

def extract_path(dataset_dir: str, module_path: str) -> (str, str, str):
    relative_path = module_path.removeprefix(dataset_dir.removesuffix(os.path.sep)).removeprefix(os.path.sep)
    split_path = relative_path.split(os.path.sep)
    return split_path[0], split_path[-1], relative_path

def generate_mvn_tree_path(path):
    s = path.split("\\")
    s[0] = "."
    return "\\".join(s)


if __name__ == "__main__":
    # dataset_path = r"/home1/kaixuan/ray/RQ3_Dataset/clone2"
    # dataset_path = r"/home1/kaixuan/ray/RQ3_Dataset/clone"
    dataset_path = r"/home1/kaixuan/ray/RQ3_Dataset/clone3"

    # paths = list(find_maven_projects(dataset_path))
    # pd.DataFrame([{"abs_module_path": path} for path in paths]).to_csv(os.path.join("data","rq3_abs_module_path.csv"), index=False)
    paths = pd.read_csv(os.path.join("data","rq3_abs_module_path.csv"))["abs_module_path"].tolist()
    paths = paths[2619:]
    # print(paths[0])
    
    export_csv = pd.DataFrame()
    pbar = tqdm(total=len(paths), position=0)
    for abs_module_path in paths:
        repo_name, module_name, relative_path = extract_path(dataset_path, abs_module_path)
        print(repo_name, module_name, relative_path)
        if _p :=relative_path.removeprefix(f"{repo_name}"):
            _m = _p.removeprefix(os.path.sep)
        else:
            _m = "."

        _r = abs_module_path.removesuffix(relative_path)+repo_name

        process_ok =  process(_r, repo_name, module_name,_m)
        export_csv=pd.concat([export_csv, pd.DataFrame([{
            "repo": repo_name,
            "module": module_name,
            "abs_path": _r,
            "process": process_ok,
            "relative_path":relative_path,
            "mvn": _m
        }])], ignore_index=True)

        export_csv.to_csv(os.path.join("data","rq3_processed.csv"), index=False)
        pbar.update(1)
    pbar.close()
