"""get GAV and relative path of local modules"""
import os
import subprocess
from lxml import etree

def get_all_module(root_dir:str):
    """get paths to all submodules
    Args:
        root_dir (str): path to root of project
    Return:
        local_modules (list): all absolute paths to submodules from root_dir
    """
    local_modules = []
    for dirpath, _, filenames in os.walk(root_dir):
        if "pom.xml" in filenames:
            # a local module
            local_modules.append(dirpath)
    return local_modules

def get_gav(module_path:str, root_dir:str):
    """get GAV of a local module
    Args:
        module_path (str): absolute path to a module dir
        root_dir (str): absolute path to root
    Return:
        inform (dict): {g:a:v --> relative module_path}
    """
    # generate effective-pom
    command = f"cd {module_path} && mvn help:effective-pom -Doutput=effective-pom.xml"
    result = subprocess.run(command, shell=True, text=True, capture_output=True)
    effective_pom_path = os.path.join(module_path, 'effective-pom.xml')

    # get GAV from effective-pom
    g,a,v = parse_pom(effective_pom_path)
    return {
        f'{g}:{a}:{v}':os.path.relpath(module_path, root_dir)
    }

def parse_pom(pom:str):
    """parse effective-pom to get gav
    Args:
        pom (str): path to the effective pom
    Return:
        g (str):groupId,
        a (str):artifactId,
        v (str):version
    """
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(pom, parser)
    root = tree.getroot()
    ns = {'m': 'http://maven.apache.org/POM/4.0.0'}
    project = root.find('m:project', namespaces=ns)
    
    g_id = project.find('m:groupId', namespaces=ns)
    a_id = project.find('m:artifactId', namespaces=ns)
    v = project.find('m:version', namespaces=ns)

    return g_id.text, a_id.text, v.text

if __name__ == '__main__':
    # path = '/home/ray/Tool/Dataset/canal/admin/tmp_pom.xml'
    
    # print(parse_pom(path))
    print(get_gav('/home/ray/Tool/Dataset/canal/admin/','/home/ray/Tool/Dataset/canal/'))