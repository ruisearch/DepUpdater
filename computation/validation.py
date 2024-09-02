"""all operations for validating the best version got by the computation module"""
import os
import json
import concurrent.futures
import time

from lxml import etree
from tqdm import tqdm
class Validation:
    def __init__(self, path_to_cloned_folder: str, relative_path_to_module: str) -> None:
        self.path_to_cloned_folder = path_to_cloned_folder
        self.relative_path_to_module = relative_path_to_module
        self.pom_path = os.path.join(path_to_cloned_folder, relative_path_to_module, 'pom.xml')
    
    def get_actual_best_version(self, group_id: str, artifact_id: str, versions: list, direct_or_transitive:str)->str:
        """recompile the project from the initial version to the newest version of the dependency
        to get the actual best version
        Args:
            versions (list): all versions of the dependency
            direct_or_transitive (str): 'direct' or 'transitive'
        Return:
            best_version (str): the actual best version of the dependency
        """
        # copy the pom.xml to a new file
        original_pom_path = os.path.join(self.path_to_cloned_folder, self.relative_path_to_module, '_original_pom.xml')
        with open(self.pom_path, 'r') as f:
            content = f.read()
        with open(original_pom_path, 'w') as f:
            f.write(content)
        # add the property about version of the dependency into the pom.xml
        # and set the version to the property
        # direct_dependency and transitive_dependency are not in the same format
        initial_version = versions[0]
        if direct_or_transitive == 'direct':
            self.add_direct_dependency(group_id, artifact_id, initial_version)
        elif direct_or_transitive == 'transitive':
            self.add_transitive_dependency(group_id, artifact_id, initial_version)
            
        # recompile the module from the initial version to the newest version of the dependency
        # to get the actual best version
        num_workers = os.cpu_count()
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            # initializing the progress bar
            pbar = tqdm(total=len(versions), desc=f'Recompiling versions of {group_id}:{artifact_id}', position=0, leave=True)
            # submit the tasks to the executor
            tasks = {executor.submit(self.recompile, group_id, artifact_id, version): version for version in versions}
            
            for success,result in concurrent.futures.as_completed(tasks):
                pbar.update(1)
                if success:
                    # get the actual best version
                    best_version = result
                    break

    def recompile(self, group_id: str, artifact_id: str, version: str):
        """recompile the module with the specific version of the dependency
        Return:
            success (bool): whether the recompilation is successful
            result (str): the result of the recompilation
        """
        # note: skip maven-enforcer-plugin
        command = f"cd {self.path_to_cloned_folder} && mvn -Dmaven.test.skip=true -Dcheckstyle.skip=true -Denforcer.skip=true -D{group_id}_{artifact_id}_version={version} compile -am"
        # to be implemented ....
        
    def add_direct_dependency(self, group_id: str, artifact_id: str, initial_version: str):
        """add the direct dependency into the pom.xml
        1. update the <dependencies>;
        2. add {group_id}_{artifact_id}_version property im the <properties>;
        3. set the version of the dependency to the property
        """
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.parse(self.pom_path, parser)
        root = tree.getroot()
        ns = {'m': 'http://maven.apache.org/POM/4.0.0'}  # Make sure this matches your pom.xml's namespace
        
        # add {group_id}_{artifact_id}_version into the properties
        properties = root.find('.//m:properties', namespaces=ns)
        if properties is None:
            properties = etree.SubElement(root, '{http://maven.apache.org/POM/4.0.0}properties')
        _property = etree.SubElement(properties, '{http://maven.apache.org/POM/4.0.0}property')
        # add {group_id}_{artifact_id}_version into the property tag and set its value to the initial version
        property_name = etree.SubElement(_property, '{http://maven.apache.org/POM/4.0.0}{group_id}_{artifact_id}_version')
        property_name.text = initial_version
        
        # Check if dependency exists and create/update as necessary
        dependencies = root.find('.//m:dependencies', namespaces=ns)
        if dependencies is None:
            dependencies = etree.SubElement(root, '{http://maven.apache.org/POM/4.0.0}dependencies')

        dependency = None
        for dep in dependencies.findall('m:dependency', namespaces=ns):
            g_id = dep.find('m:groupId', namespaces=ns)
            a_id = dep.find('m:artifactId', namespaces=ns)
            if g_id is not None and a_id is not None and g_id.text == group_id and a_id.text == artifact_id:
                # set version to the property
                version = dep.find('m:version', namespaces=ns)
                version.text = f'${{{group_id}_{artifact_id}_version}}'
                dependency = dep
                break

        if dependency is None:
            dependency = etree.SubElement(dependencies, '{http://maven.apache.org/POM/4.0.0}dependency')
            gid = etree.SubElement(dependency, '{http://maven.apache.org/POM/4.0.0}groupId')
            gid.text = group_id
            aid = etree.SubElement(dependency, '{http://maven.apache.org/POM/4.0.0}artifactId')
            aid.text = artifact_id
            version = etree.SubElement(dependency, '{http://maven.apache.org/POM/4.0.0}version')
            version.text = f'${{{group_id}_{artifact_id}_version}}'


    def add_transitive_dependency(self, group_id: str, artifact_id: str, initial_version: str):
        """add the transitive dependency into the pom.xml
        1. update the <dependencyManagemen>;
        2. add {group_id}_{artifact_id}_version property im the <properties>;
        3. set the version of the dependency to the property
        """
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.parse(self.pom_path, parser)
        root = tree.getroot()
        ns = {'m': 'http://maven.apache.org/POM/4.0.0'}
        
        # add {group_id}_{artifact_id}_version into the properties
        properties = root.find('.//m:properties', namespaces=ns)
        if properties is None:
            properties = etree.SubElement(root, '{http://maven.apache.org/POM/4.0.0}properties')
        _property = etree.SubElement(properties, '{http://maven.apache.org/POM/4.0.0}property')
        # add {group_id}_{artifact_id}_version into the property tag and set its value to the initial version
        property_name = etree.SubElement(_property, '{http://maven.apache.org/POM/4.0.0}{group_id}_{artifact_id}_version')
        property_name.text = initial_version
        
        # Check if dependency exists and create/update as necessary
        dependencyManagement = root.find('.//m:dependencyManagement', namespaces=ns)
        if dependencyManagement is None:
            dependencyManagement = etree.SubElement(root, '{http://maven.apache.org/POM/4.0.0}dependencyManagement')
            
        dependencies = dependencyManagement.find('m:dependencies', namespaces=ns)
        if dependencies is None:
            dependencies = etree.SubElement(dependencyManagement, '{http://maven.apache.org/POM/4.0.0}dependencies')

        dependency = None
        for dep in dependencies.findall('m:dependency', namespaces=ns):
            g_id = dep.find('m:groupId', namespaces=ns)
            a_id = dep.find('m:artifactId', namespaces=ns)
            if g_id is not None and a_id is not None and g_id.text == group_id and a_id.text == artifact_id:
                # set version to the property
                version = dep.find('m:version', namespaces=ns)
                version.text = f'${{{group_id}_{artifact_id}_version}}'
                dependency = dep
                break

        if dependency is None:
            dependency = etree.SubElement(dependencies, '{http://maven.apache.org/POM/4.0.0}dependency')
            gid = etree.SubElement(dependency, '{http://maven.apache.org/POM/4.0.0}groupId')
            gid.text = group_id
            aid = etree.SubElement(dependency, '{http://maven.apache.org/POM/4.0.0}artifactId')
            aid.text = artifact_id
            version = etree.SubElement(dependency, '{http://maven.apache.org/POM/4.0.0}version')
            version.text = f'${{{group_id}_{artifact_id}_version}}'