"""
    used to get the modules which can compile and test before updating
    and add them into the dataset of RQs
"""
import os
def check_all_modules(repo_root_path:str):
    """
        check all modules in the repository
        return a list of tuples, each tuple is the parameters of the chosen module
        Args:
            repo_root_path: the path of the repository
        Returns:
            success_modules: a list of tuples, each tuple is the parameters of the chosen module in repo_root_path
    """
    success_modules = []
    
    for root, _, files in os.walk(repo_root_path):
        if 'pom.xml' in files:
            # a module
            relative_path = os.path.relpath(root, repo_root_path)
            if check_one_module(repo_root_path, relative_path):
                repo_name = os.path.basename(repo_root_path)
                success_modules.append((repo_name, relative_path))

    return success_modules

def check_one_module(path_to_folder:str, relative_path_to_module:str)->bool:
    """
        check whether the module can package and test
        Args:
            path_to_folder: the path to the root of the repository
            relative_path_to_module: the relative path to the module
    """
    package_exit_code = mvn_package(path_to_folder, relative_path_to_module)
    if package_exit_code != 0:
        return False
    test_exit_code = mvn_test(path_to_folder, relative_path_to_module)
    if test_exit_code != 0:
        return False
    return True

def mvn_package(path_to_folder:str, relative_path_to_module:str):
    """execute \"mvn package\""""
    # firstly, execute mvn package in module folder
    if relative_path_to_module == '.':
        command = f"cd {path_to_folder} && mvn -Dmaven.test.skip=true -Dcheckstyle.skip=true clean package"
    else :
        command = f"cd {os.path.join(path_to_folder, relative_path_to_module)} && mvn -Dmaven.test.skip=true -Dcheckstyle.skip=true clean package"
    print("mvn clean and mvn package...")
    exit_status = os.system(command)
    if exit_status != 0 and relative_path_to_module != '.':
        # mvn package is unexecutable in module folder, so execute it in root with the help of -pl -am
        command = f"cd {path_to_folder} && mvn -Dmaven.test.skip=true -Dcheckstyle.skip=true -pl {relative_path_to_module} -am clean package "
        exit_status = os.system(command)
    # if exit_status != 0:
    #     # mvn package is unexecutable with -pl -am, so execute it in root without -pl -am
    #     command = f"cd {path_to_folder} && mvn -Dmaven.test.skip=true -Dcheckstyle.skip=true clean package"
    #     exit_status = os.system(command)
    return exit_status

def mvn_test(path_to_folder:str, relative_path_to_module:str):
    """execute mvn test"""
    # firstly, execute mvn test in module folder
    if relative_path_to_module == '.':
        command = f"cd {path_to_folder} && mvn -Dcheckstyle.skip=true -Denforcer.skip=true -Dflatten.skip=true test"
    else :
        command = f"cd {os.path.join(path_to_folder, relative_path_to_module)} && \
            mvn -Dcheckstyle.skip=true \
            -Denforcer.skip=true -Dflatten.skip=true test" 
    print("mvn test...")
    exit_status = os.system(command)
    if exit_status != 0 and relative_path_to_module != '.':
        # mvn test is unexecutable in module folder, so execute it in root with the help of -pl -am
        command = f"cd {path_to_folder} && mvn -Dcheckstyle.skip=true -Denforcer.skip=true -Dflatten.skip=true -pl {relative_path_to_module} -am test"
        exit_status = os.system(command)
    # if exit_status != 0:
    #     # mvn test is unexecutable with -pl -am, so execute it in root without -pl -am
    #     command = f"cd {path_to_folder} && mvn -Dcheckstyle.skip=true -Denforcer.skip=true -Dflatten.skip=true test"
    #     exit_status = os.system(command)
    return exit_status

if __name__ == "__main__":
    success_modules = []
    path_to_extended_dataset_root = "/home1/kaixuan/ray/Extended_dataset"
    repos = [
        "easyexcel",
        "nacos",
        "spring-boot-demo",
        "WxJava",
        "zxing"
    ]
    for repo in repos:
        repo_path = os.path.join(path_to_extended_dataset_root, repo)
        added_modules = check_all_modules(repo_path)
        success_modules.extend(added_modules)
        print("===============================================")
        for added_module in added_modules:
            print(added_module)
        print("===============================================")

    print("All success modules:")
        
    for module in success_modules:
        print(module)