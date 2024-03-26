import xml.etree.ElementTree as ET
## insert maven-shade-plugin into the <build><plugins> in pom.xml
# input : path to pom.xml
# output : the inserted pom.xml
def insert(pom_file_path:str):
    # Load the pom.xml file
    tree = ET.parse(pom_file_path)
    root = tree.getroot()
    
    ## Define the namespace mappings
    ## map URI to prefix
    ns = {
        "xmlns":"http://maven.apache.org/POM/4.0.0"
    }
    # # Define the namespace URI
    # namespace_uri = "http://example.com/namespace"

    # # Register the namespace with an empty prefix
    # ET.register_namespace("", namespace_uri)

    # Check if Maven Shade Plugin is already declared
    is_maven_shade_plugin_declared = False
    for plugin in root.findall(".//build/plugins/plugin"):
    # for plugin in root.findall(".//xmlns:build/xmlns:plugins/xmlns:plugin", ns):
        # groupId = plugin.find("xmlns:groupId", ns)
        groupId = plugin.find("groupId")
        # artifactId = plugin.find("xmlns:artifactId", ns)
        artifactId = plugin.find("artifactId")
        if groupId is not None and groupId.text == "org.apache.maven.plugins" and artifactId is not None and artifactId.text == "maven-shade-plugin":
            is_maven_shade_plugin_declared = True
            break

    # Only add Maven Shade Plugin if it's not already declared
    if not is_maven_shade_plugin_declared:
        # Find the <build> tag
        # build_tag = root.find("xmlns:build", ns)
        build_tag = root.find("build")
        
        # Find or create the <plugins> tag within <build>
        # plugins_tag = build_tag.find("xmlns:plugins", ns)
        plugins_tag = build_tag.find("plugins")
        if plugins_tag is None:
            plugins_tag = ET.SubElement(build_tag, "plugins")

        # Create the <plugin> element and its child elements
        plugin_element = ET.Element("plugin")
        groupId_element = ET.SubElement(plugin_element, "groupId")
        groupId_element.text = "org.apache.maven.plugins" 
        artifactId_element = ET.SubElement(plugin_element, "artifactId")
        artifactId_element.text = "maven-shade-plugin" 
        version_element = ET.SubElement(plugin_element, "version")
        version_element.text = "3.5.2" 

        # Create <executions> element
        executions_element = ET.SubElement(plugin_element, "executions")
        execution_element = ET.SubElement(executions_element, "execution")
        phase_element = ET.SubElement(execution_element, "phase")
        phase_element.text = "package"
        goals_element = ET.SubElement(execution_element, "goals")
        goal_element = ET.SubElement(goals_element, "goal")
        goal_element.text = "shade"

        # Append the <plugin> element to <plugins> tag
        plugins_tag.append(plugin_element)

        # Save the modified pom.xml file
        tree.write(pom_file_path)

## test
if __name__ == "__main__":
    insert("/home/ray/Work/Tool/Data/fudan_paper_client/584/java-design-patterns/pom.xml")