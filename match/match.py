## finish match 
import os

from match.Api import Api
from match.CallGraph import CallGraph
from match.constants import JAR_FOLDER
from match.Reference import Reference


def all():
    ## test : deal with the module folder in data/Jar
    items = os.listdir(JAR_FOLDER)
    item_path = None
    for item in items:
        if os.path.isdir(os.path.join(JAR_FOLDER, item)):
            item_path = os.path.join(JAR_FOLDER, item)
            break
    if item_path is None:
        print("jar doesn't exist, exit")
        exit()
    cg = CallGraph(item_path)
    ## generate call_graph.txt as well as call_graph.json
    cg.gen_json()
    ## extract api of effective deps
    Jar = Api(item_path, cg)
    Jar.extract_api()
    ## map dep jar to the apis which are reachable
    # get the apis which are reachable,stored in Jar.reachable_apis as a set
    Jar.get_reachable_api()
    # dep jar(effective & omitted)->reachable api mapping
    Jar.jar_to_reachable_api()
    # dep jar(effective & omitted)->reference mapping
    ref = Reference(item_path)
    ref.gen_ref()

    