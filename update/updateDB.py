import csv
import subprocess
import xml.etree.ElementTree as ET
import os

import pymongo

from config import MONGO_HOST, MONGO_PORT, pom_path
from download_pom import download_pom_one


def populate_dep(gav, c=None):
    if c==None:
        c = pymongo.MongoClient(MONGO_HOST,
                                port=MONGO_PORT)
    maven_deps = c['library-crawler']['maven_deps']
    # if maven_deps.find_one({'parent': gav.replace('|', ':')}):
    #     return
    os.makedirs(pom_path, exist_ok=True)
    download_pom_one(gav)
    cwd = os.getcwd()
    go, ao, vo = gav.split('|')
    if not os.path.exists(pom_path +ao+'-'+vo+'.pom'):
        return
    os.rename(pom_path +ao+'-'+vo+'.pom', pom_path+'pom.xml')
    os.chdir(pom_path)
    try:
        output = subprocess.check_output('mvn help:effective-pom -Doutput=tmp_pom.xml',stderr=subprocess.STDOUT, shell=True)
        # print(output)
    except:
        with open('/Users/lyuye/workspace/collegues/yiran/errored.csv', 'a') as fc:
            csv.writer(fc).writerow([gav.replace('|', ':')])
    os.chdir(cwd)
    try:
        mytree = ET.parse(pom_path+'tmp_pom.xml')
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

        os.remove(pom_path+'pom.xml',)

        maven_deps.update_one({'parent': gav.replace('|', ":")}, {'$set':{'dependencies':dependencies, }},upsert=True)
        # maven_deps.insert_one({'dependencies':dependencies, 'parent': go+':'+ao+':'+vo})
    except Exception as e:
        print(gav, e)
    # c.close()