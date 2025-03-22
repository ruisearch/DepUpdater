"""download a pom.xml accroding to the gav"""
import os
import subprocess
import shutil
from constants import POM_PATH, M2_PATH

def download_pom_one(jar_info):
    print('Downloading', jar_info)

    group_id, artifact_id, version_name = jar_info.split('|')
    local_path = POM_PATH
    #os.path.join(download_path, group_id, artifact_id, version_name)
    # os.makedirs(local_path, exist_ok=True)

    # if os.path.exists(os.path.join(local_path, artifact_id+'-'+version_name+'.jar')):
    #     return
    try:
        result = subprocess.check_output(f'mvn dependency:get \
            -DgroupId=%s \
            -DartifactId=%s \
            -Dversion=%s \
            -Dtransitive=false \
            -Ddest={local_path} \
            -DremoteRepositories=https://repo1.maven.org/maven2/ \
            -Dpackaging=pom' % (group_id,
                                 artifact_id,
                                 version_name), shell=True)

        # print(result)
        if not os.path.exists(os.path.join(local_path, artifact_id+'-'+version_name+'.pom')):
            shutil.copyfile(M2_PATH+group_id.replace('.', '/')+'/'+artifact_id+'/'+version_name+ '/'+ artifact_id+'-'+version_name+'.pom', local_path+artifact_id+'-'+version_name+'.pom')
        return True
    except Exception as e:
        print(e)
        return False
