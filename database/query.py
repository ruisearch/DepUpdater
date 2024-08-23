"""query to sqlite"""
import os
from database.sqlite import Sqlite
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
    
def query_revapi_report(groudId, artifactId, oldVersion, newVersion):
    """query Revapi table to get the compatibility report"""
    db = Sqlite(SQLITE_PATH)
    db.connect()
    condition = [('groupId','=',groudId),'AND',('artifactId','=',artifactId),'AND',('oldVersion','=',oldVersion),'AND',('newVersion','=',newVersion)]
    report_record = db.query_data('Revapi', 'report', condition)
    report = report_record[0][0] if report_record else ""
    db.close()
    return report

def store_revapi_report(groudId, artifactId, oldVersion, newVersion, report):
    """store the compatibility report"""
    db = Sqlite(SQLITE_PATH)
    db.connect()
    # insert ga v1 v2 first if not exists
    db.insert_data('Revapi', {'groupId':groudId, 'artifactId':artifactId, 'oldVersion':oldVersion, 'newVersion':newVersion, 'report':report})
    db.close()