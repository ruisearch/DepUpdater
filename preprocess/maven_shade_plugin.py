# deprecated ! 
from bs4 import BeautifulSoup
## insert maven-shade-plugin into the <build><plugins> in pom.xml
# input : path to pom.xml
# output : the inserted pom.xml
def insert(pom_file_path:str):
    # Read the XML file
    with open(pom_file_path, 'r') as file:
        xml_data = file.read()

    # Create a BeautifulSoup object
    soup = BeautifulSoup(xml_data, 'xml')
    # soup = BeautifulSoup(xml_data, 'xml', parser='lxml')
    # soup = BeautifulSoup(xml_data, 'lxml-xml')

    # Find the <build> section
    build_section = soup.find('build')

    # # Find the <plugins> section within the <build> section
    # plugins_section = build_section.find('plugins')
    
    # Find the <plugins> section within the <build> section
    plugins_section = None
    for child in build_section.children:
        if child.name == 'plugins':
            plugins_section = child
            break

    # Check if the plugin already exists
    # existing_plugin = plugins_section.find('plugin', artifactId='maven-shade-plugin')
    existing_plugin = None
    all_plugins = plugins_section.find_all('plugin')
    for plugin in all_plugins:
        artifact_id = plugin.find('artifactId')
        if artifact_id and artifact_id.text.strip() == 'maven-shade-plugin':
            existing_plugin = plugin
            break
    

    # Add the plugin only if it doesn't already exist
    if not existing_plugin:
        # Create a new <plugin> element for Maven Shade Plugin
        plugin_element = soup.new_tag('plugin')

        # Create the <groupId> element
        group_id_element = soup.new_tag('groupId')
        group_id_element.string = 'org.apache.maven.plugins'
        plugin_element.append(group_id_element)

        # Create the <artifactId> element
        artifact_id_element = soup.new_tag('artifactId')
        artifact_id_element.string = 'maven-shade-plugin'
        plugin_element.append(artifact_id_element)

        # Create the <version> element
        version_element = soup.new_tag('version')
        version_element.string = '3.5.2'
        plugin_element.append(version_element)
        
        # Create the <executions> element
        executions_element = soup.new_tag('executions')

        # Create the <execution> element
        execution_element = soup.new_tag('execution')

        # Create the <phase> element
        phase_element = soup.new_tag('phase')
        phase_element.string = 'package'
        execution_element.append(phase_element)

        # Create the <goals> element
        goals_element = soup.new_tag('goals')

        # Create the <goal> element
        goal_element = soup.new_tag('goal')
        goal_element.string = 'shade'
        goals_element.append(goal_element)

        # Append elements to the corresponding sections
        execution_element.append(goals_element)
        executions_element.append(execution_element)
        plugin_element.append(executions_element)
        
        # Append the <plugin> element to the <plugins> section
        plugins_section.append(plugin_element)

        # Save the modified XML to the original file
        with open(pom_file_path, 'w') as file:
            # file.write(str(soup))
            file.write(str(soup.prettify()))
## test
if __name__ == "__main__":
    insert("/home/ray/Work/Tool/Data/fudan_paper_client/584/java-design-patterns/pom.xml")