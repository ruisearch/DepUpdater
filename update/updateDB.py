import csv
import subprocess
import xml.etree.ElementTree as ET
import os

from database.query import insert_dependencies_into_mongo

from constants import POM_PATH
from update.download_pom import download_pom_one


def populate_dep(go, ao, vo):
    """get the dependencies of an artifact and store them in the database
    Args:
        go (str): groupId
        ao (str): artifactId
        vo (str): version
    """
    os.makedirs(POM_PATH, exist_ok=True)
    gav = go+'|'+ao+'|'+vo
    download_pom_one(gav)
    cwd = os.getcwd()
    if not os.path.exists(POM_PATH +ao+'-'+vo+'.pom'):
        return
    os.rename(POM_PATH +ao+'-'+vo+'.pom', POM_PATH+'pom.xml')
    os.chdir(POM_PATH)
    try:
        # get the effective pom from the pom.xml
        print(f'extracting dependencies of {gav}...')
        output = subprocess.check_output('mvn help:effective-pom -Doutput=tmp_pom.xml',stderr=subprocess.STDOUT, shell=True)
        # print(output)
    except:
        with open(os.path.join(POM_PATH,'errored.csv'), 'a') as fc:
            csv.writer(fc).writerow([gav.replace('|', ':')])
    os.chdir(cwd)
    try:
        mytree = ET.parse(POM_PATH+'tmp_pom.xml')
        root = mytree.getroot()
        dependencies = []
        order = 1
        for child in root:
            if 'dependencies' in child.tag:
                for dep in child:
                    each = {}
                    for ele in dep:
                        s = ''
                        opt=''
                        if 'groupId' in ele.tag:
                            g = ele.text
                        if 'artifactId' in ele.tag:
                            a = ele.text
                        if 'version' in ele.tag:
                            v = ele.text
                        if 'isoptional' in ele.tag:
                            opt = ele.text
                        if 'scope' in ele.tag:
                            s = ele.text
                    gav_d = g+':'+a+':'+v
                    if s=='':
                        s = 'compile'
                    # if s== 'test':
                    #     continue
                    if opt.lower() =='true':
                        opt = 'true'
                    else:
                        opt = 'false'
                    each['dep'] = gav_d
                    each['dScope'] = s
                    each['dType'] = "dependency"
                    each['isoptional'] = opt
                    each['order'] = str(order)
                    each['exclusion'] = []
                    dependencies.append(each)
                    order += 1

        os.remove(POM_PATH+'pom.xml')

        insert_dependencies_into_mongo(go, ao, vo, dependencies)
    except Exception as e:
        print(gav, e)

    print(f'dependencies of {gav} got')

    return dependencies

if __name__ == '__main__':
    g = 'com.fasterxml.jackson.core'
    a = 'jackson-databind'
    v = '2.17.2'
    dependencies = populate_dep(g, a, v)
    print(dependencies)