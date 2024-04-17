## finish match 
import os 
from match.CallGraph import CallGraph
from match.constants import JAR_FOLDER
from match.Api import Api
    
## doing match in all modules
def all():
    # ## travel all subfolder in Jar folder
    # Jar_contents = os.listdir(JAR_FOLDER)
    # for item in JAR_FOLDER:
    #     item_path = os.path.join(JAR_FOLDER, item)
    #     ## item is a subfolder in Jar folder
    #     ## use CallGraph to generate call graph
    #     if os.path.isdir(item_path):
    #         cg = CallGraph(item_path)
    
    ## test : just deal with one module folder in data/Jar
    # item_path = os.path.join(JAR_FOLDER, '2')
    # item_path = os.path.join(JAR_FOLDER, '170')
    item_path = os.path.join(JAR_FOLDER, '169')
    # item_path = os.path.join(JAR_FOLDER, '3')
    # item_path = os.path.join(JAR_FOLDER, '4')
    cg = CallGraph(item_path)
    ## generate call_graph.txt as well as call_graph.json
    cg.gen_json()
    ## extract api
    Jar = Api(item_path, cg)
    Jar.extract_api()
    ## map dep jar to the apis which are reachable
    # get the apis which are reachable,stored in Jar.reachable_apis as a set
    Jar.get_reachable_api()
    # dep jar->reachable api mapping
    Jar.jar_to_reachable_api()
    
    