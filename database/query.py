"""query to sqlite"""
import os
import json
from database.sqlite import Sqlite
from database.mongodb import Mongo
from database.constants import SQLITE_PATH
from constants import JAR_DIR

def create_folder(folder_path):
    """create folder if not exist"""
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

def query_to_get_jar_location(groupId, artifactId, version):
    """query artifacts table to find the absolute path to jar\n
    and create folder if not exist"""
    db = Sqlite(SQLITE_PATH)
    db.connect()
    condition = [('groupId','=',groupId),'AND',('artifactId','=',artifactId),'AND',('version','=',version)]
    relative_path = db.query_data('artifacts', 'relative_path',condition)
    if not relative_path:
        # not in artifacts yet, so insert the record
        path_to_record = f'{groupId}/{artifactId}/{version}/{artifactId}-{version}.jar'
        db.insert_data('artifacts', {'groupId':groupId, 'artifactId':artifactId, 'version':version, \
            'relative_path': path_to_record})
        relative_path = [(path_to_record,)]
    db.close()
    jar_path = os.path.join(JAR_DIR, relative_path[0][0])
    dir_path = os.path.dirname(jar_path)
    create_folder(dir_path)
    return jar_path

def query_call_graph(groupId, artifactId, version):
    """query api table to get the call graph of the jar file if exists"""
    db = Sqlite(SQLITE_PATH)
    db.connect()
    condition = [('groupId','=',groupId),'AND',('artifactId','=',artifactId),'AND',('version','=',version)]
    cg_record = db.query_data('api', 'callGraph', condition)
    cg = cg_record[0][0] if cg_record else ""
    db.close()
    return cg

def store_call_graph(groupId, artifactId, version, cg):
    """store the call graph of the jar file"""
    db = Sqlite(SQLITE_PATH)
    db.connect()
    condition = [('groupId','=',groupId),'AND',('artifactId','=',artifactId),'AND',('version','=',version)]
    # insert gav first if not exists
    db.insert_data('api', {'groupId':groupId, 'artifactId':artifactId, 'version':version})
    db.update_data('api', {'callGraph':cg}, condition)
    db.close()
    
def query_type_dependency_graph(groupId, artifactId, version):
    """query api table to get the type dependency graph of the jar file if exists"""
    db = Sqlite(SQLITE_PATH)
    db.connect()
    condition = [('groupId','=',groupId),'AND',('artifactId','=',artifactId),'AND',('version','=',version)]
    tdg_record = db.query_data('api', 'typeDependencyGraph', condition)
    tdg = tdg_record[0][0] if tdg_record else ""
    db.close()
    return tdg

def store_type_dependency_graph(groupId, artifactId, version, tdg):
    """store the type dependency graph of the jar file"""
    db = Sqlite(SQLITE_PATH)
    db.connect()
    condition = [('groupId','=',groupId),'AND',('artifactId','=',artifactId),'AND',('version','=',version)]
    # insert gav first if not exists
    db.insert_data('api', {'groupId':groupId, 'artifactId':artifactId, 'version':version})
    db.update_data('api', {'typeDependencyGraph':tdg}, condition)
    db.close()
    
def query_revapi_report(groupId, artifactId, oldVersion, newVersion):
    """query Revapi table to get the compatibility report"""
    print(f"query revapi report of {groupId}:{artifactId}:{oldVersion} -> {newVersion}")
    db = Sqlite(SQLITE_PATH)
    db.connect()
    condition = [('groupId','=',groupId),'AND',('artifactId','=',artifactId),'AND',('oldVersion','=',oldVersion),'AND',('newVersion','=',newVersion)]
    report_record = db.query_data('Revapi', 'report', condition)
    report = report_record[0][0] if report_record else ""
    db.close()
    return report

def store_revapi_report(groupId, artifactId, oldVersion, newVersion, report):
    """store the compatibility report"""
    db = Sqlite(SQLITE_PATH)
    db.connect()
    # insert ga v1 v2 first if not exists
    db.insert_data('Revapi', {'groupId':groupId, 'artifactId':artifactId, 'oldVersion':oldVersion, 'newVersion':newVersion, 'report':report})
    db.close()
    
def query_revapi_bc_api(groupId, artifactId, oldVersion, newVersion):
    """query Revapi table to get binaryBcMethod, binaryBcType, sourceBcMethod, sourceBcType"""
    # print(f'query bc api of {groupId}:{artifactId}:{oldVersion} -> {newVersion}')
    db = Sqlite(SQLITE_PATH)
    db.connect()
    condition = [('groupId','=',groupId),'AND',('artifactId','=',artifactId),'AND',('oldVersion','=',oldVersion),'AND',('newVersion','=',newVersion)]
    api_record = db.query_data('Revapi', 'binaryBcMethod, binaryBcType, sourceBcMethod, sourceBcType', condition)
    # if not exists, return None
    if not api_record:
        return None, None, None, None
    binaryBcMethod = json.loads(api_record[0][0]) if api_record[0][0] is not None else None
    binaryBcType = json.loads(api_record[0][1]) if api_record[0][1] is not None else None
    sourceBcMethod = json.loads(api_record[0][2]) if api_record[0][2] is not None else None
    sourceBcType = json.loads(api_record[0][3]) if api_record[0][3] is not None else None
    db.close()
    return binaryBcMethod, binaryBcType, sourceBcMethod, sourceBcType

def store_revapi_binary_bc_api(groupId, artifactId, oldVersion, newVersion, binary_bc_method, binary_bc_type):
    """store the binary bc api"""
    db = Sqlite(SQLITE_PATH)
    db.connect()
    condition = [('groupId','=',groupId),'AND',('artifactId','=',artifactId),'AND',('oldVersion','=',oldVersion),'AND',('newVersion','=',newVersion)]
    # insert ga v1 v2 first if not exists
    db.insert_data('Revapi', {'groupId':groupId, 'artifactId':artifactId, 'oldVersion':oldVersion, 'newVersion':newVersion})
    db.update_data('Revapi', {'binaryBcMethod':json.dumps(binary_bc_method), 'binaryBcType':json.dumps(binary_bc_type)}, condition)
    db.close()
    
def store_revapi_source_bc_api(groupId, artifactId, oldVersion, newVersion, source_bc_method, source_bc_type):
    """store the source bc api"""
    db = Sqlite(SQLITE_PATH)
    db.connect()
    condition = [('groupId','=',groupId),'AND',('artifactId','=',artifactId),'AND',('oldVersion','=',oldVersion),'AND',('newVersion','=',newVersion)]
    # insert ga v1 v2 first if not exists
    db.insert_data('Revapi', {'groupId':groupId, 'artifactId':artifactId, 'oldVersion':oldVersion, 'newVersion':newVersion})
    db.update_data('Revapi', {'sourceBcMethod':json.dumps(source_bc_method), 'sourceBcType':json.dumps(source_bc_type)}, condition)
    db.close()
    
def store_revapi_bc_api(groupId, aritifactId, oldVersion, newVersion, binary_bc_method, binary_bc_type, source_bc_method, source_bc_type):
    """store the binary and source bc api"""
    db = Sqlite(SQLITE_PATH)
    db.connect()
    condition = [('groupId','=',groupId),'AND',('artifactId','=',aritifactId),'AND',('oldVersion','=',oldVersion),'AND',('newVersion','=',newVersion)]
    # insert ga v1 v2 first if not exists
    db.insert_data('Revapi', {'groupId':groupId, 'artifactId':aritifactId, 'oldVersion':oldVersion, 'newVersion':newVersion})
    db.update_data('Revapi', {'binaryBcMethod':json.dumps(binary_bc_method), 'binaryBcType':json.dumps(binary_bc_type), \
        'sourceBcMethod':json.dumps(source_bc_method), 'sourceBcType':json.dumps(source_bc_type)}, condition)
    db.close()
    
def query_japicmp_bc_api(groupId, artifactId, oldVersion, newVersion):
    """query Japicmp table to get binaryBcMethod, binaryBcType"""
    # print(f'query bc api of {groupId}:{artifactId}:{oldVersion} -> {newVersion}')
    db = Sqlite(SQLITE_PATH)
    db.connect()
    condition = [('groupId','=',groupId),'AND',('artifactId','=',artifactId),'AND',('oldVersion','=',oldVersion),'AND',('newVersion','=',newVersion)]
    api_record = db.query_data('Japicmp', 'binaryBcMethod, binaryBcType', condition)
    # if not exists, return None
    if not api_record:
        return None, None
    binaryBcMethod = json.loads(api_record[0][0]) if api_record[0][0] is not None else None
    binaryBcType = json.loads(api_record[0][1]) if api_record[0][1] is not None else None
    db.close()
    return binaryBcMethod, binaryBcType

def query_japicmp_report(groupId, artifactId, oldVersion, newVersion):
    """query Japicmp table to get the compatibility report"""
    print(f'query Japicmp report of {groupId}:{artifactId}:{oldVersion} -> {newVersion}')
    db = Sqlite(SQLITE_PATH)
    db.connect()
    condition = [('groupId','=',groupId),'AND',('artifactId','=',artifactId),'AND',('oldVersion','=',oldVersion),'AND',('newVersion','=',newVersion)]
    report_record = db.query_data('Japicmp', 'report', condition)
    report = report_record[0][0] if report_record else ""
    db.close()
    return report

def store_japicmp_report(groupId, artifactId, oldVersion, newVersion, report):
    """store the compatibility report"""
    db = Sqlite(SQLITE_PATH)
    db.connect()
    # insert ga v1 v2 first if not exists
    db.insert_data('Japicmp', {'groupId':groupId, 'artifactId':artifactId, 'oldVersion':oldVersion, 'newVersion':newVersion, 'report':report})
    db.close()
    
def store_japicmp_bc_api(groupId, aritifactId, oldVersion, newVersion, binary_bc_method, binary_bc_type):
    """store the binary bc api"""
    db = Sqlite(SQLITE_PATH)
    db.connect()
    condition = [('groupId','=',groupId),'AND',('artifactId','=',aritifactId),'AND',('oldVersion','=',oldVersion),'AND',('newVersion','=',newVersion)]
    # insert ga v1 v2 first if not exists
    db.insert_data('Japicmp', {'groupId':groupId, 'artifactId':aritifactId, 'oldVersion':oldVersion, 'newVersion':newVersion})
    db.update_data('Japicmp', {'binaryBcMethod':json.dumps(binary_bc_method), 'binaryBcType':json.dumps(binary_bc_type)}, condition)
    db.close()

def query_dependencies_from_mongo(groupId, artifactId, version):
    """query the dependencies of a gav
    Args:
        gav (str): groupId:artifactId:version
    Returns:
        dependencies (list): the dependencies of the gav
    """
    gav = f'{groupId}:{artifactId}:{version}'
    db = Mongo('maven_deps', 'maven_deps')
    db.connect()
    document = db.find_document({'parent':gav})
    if document == []:
        # no document found
        db.close()
        return None
    # if multiple documents are found, clear all and return None
    if len(document) > 1:
        db.delete_documents({'parent':gav})
        db.close()
        return None
    dependencies = document[0]['dependencies']
    db.close()
    return dependencies

def insert_dependencies_into_mongo(groupId, artifactId, version, dependencies):
    """insert the dependencies of a gav if not exists
    Args:
        dependencies (list): the dependencies of the gav
    """
    gav = f'{groupId}:{artifactId}:{version}'
    db = Mongo('maven_deps', 'maven_deps')
    db.connect()
    document = db.find_document({'parent':gav})
    if document == []:
        db.insert_document({'dependencies':dependencies,'parent':gav})
    db.close()