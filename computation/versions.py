"""get and sort all versions of a dependency"""
import time
from functools import cmp_to_key
from database.query import query_versions_from_mongo
from logger.logger import log_debug

import semver
import requests


def get_candidate_versions(groupId, artifactId, original_version, whether_rq3=False):
    """
        main function to get all versions of a dependency to be computed
        Args:
            groupId (str): groupId of the dependency
            artifactId (str): artifactId of the dependency
            original_version (str): original version of the dependency
            whether_rq3 (bool): whether to compute the versions for RQ3, just compute MMP, MmP, mmP versions
    """
    # all_versions are version from new to old
    all_versions = get_versions(groupId, artifactId)
    # the version to be computed are the versions after the original version
    original_version_idx = find_original_version_idx(all_versions, original_version)
    if original_version_idx == -1:
        # print(f"Fail to find the original version {original_version} in {groupId}:{artifactId}")
        log_debug(f"Fail to find the original version {original_version} in {groupId}:{artifactId}")
        # just return the original version
        return [original_version]
    # exclude pre-release versions
    candidate_versions = []
    for version in all_versions[:original_version_idx]:
        upper_version = version.upper()
        if 'SNAPSHOT' in upper_version or 'ALPHA' in upper_version or 'BETA' in upper_version or 'RC' in upper_version:
            continue
        candidate_versions.append(version)
    if original_version not in candidate_versions:
        candidate_versions.append(original_version)
    if whether_rq3:
        candidate_versions = get_MMP_MmP_mmP_versions(original_version, candidate_versions)
    return candidate_versions

def get_MMP_MmP_mmP_versions(original_version:str, candidate_versions:list):
    """get the MMP, MmP, mmP versions of the original version"""
    original_major = original_version.split(".")[0]
    original_minor = original_version.split(".")[1] if len(original_version.split(".")) > 1 else 0
    resulting_versions = []
    MMP_version = ""
    mMP_version = ""
    mmP_version = ""
    for version in reversed(candidate_versions):
        # reversed: from old to new
        major = version.split(".")[0]
        minor = version.split(".")[1] if len(version.split(".")) > 1 else 0
        MMP_version = version
        if major == original_major:
            mMP_version = version
        if major == original_major and minor == original_minor:
            mmP_version = version    
    resulting_versions.append(MMP_version)
    resulting_versions.append(mMP_version)
    resulting_versions.append(mmP_version)
    # 现在的问题是，MMP,MmP,mmP可能重复，需要去重，同时还要保持原来的顺序,即从新到旧，MMP，MmP,mmP
    # todo
    return resulting_versions

def find_original_version_idx(all_versions, original_version):
    """find the index of the original version in all versions"""
    for idx, version in enumerate(all_versions):
        if version == original_version:
            return idx
    return -1

def fetch_versions(groupId, artifactId):
    """fetch all versions of the dependency
    deprecated: use mongodb instead"""
    # Fetch all versions(up to 200) of the dependency from Maven Central
    url = f"http://search.maven.org/solrsearch/select?q=g:{groupId}+AND+a:{artifactId}&core=gav&rows=200&wt=json"
    try:
        response = get_resource_with_retry(url)
        if response:
            data = response.json()

            all_versions = []
            if 'docs' in data['response']:
                for doc in data['response']['docs']:
                    if 'timestamp' in doc:
                        all_versions.append({
                            'version': doc['v'],
                            'date': doc['timestamp']
                        })
    except Exception as e:
        print(f"Fail to handle {groupId}:{artifactId}, reason:{e}")

    # Sort versions using a custom comparison function
    all_versions.sort(key=cmp_to_key(version_comparator))

    # the versions in all_versions have been sorted by Maven Central
    # only return the version string
    all_versions = [version['version'] for version in all_versions]
    return all_versions

def get_versions(groupId, artifactId):
    """get all versions of an artifact"""
    all_versions = query_versions_from_mongo(groupId, artifactId)

    # Sort versions using a custom comparison function
    all_versions.sort(key=cmp_to_key(version_comparator))

    # the versions in all_versions have been sorted
    # only return the version string
    all_versions = [version['version'] for version in all_versions]
    return all_versions

def version_comparator(a, b):
    """Try to parse versions as SemVer and sort by SemVer if possible, otherwise sort by date
    arrange versions in descending order
    """
    try:
        a_semver = semver.VersionInfo.parse(a['version'])
        a_is_semver = True
    except ValueError:
        a_semver = None
        a_is_semver = False

    try:
        b_semver = semver.VersionInfo.parse(b['version'])
        b_is_semver = True
    except ValueError:
        b_semver = None
        b_is_semver = False

    # If both are SemVer compliant, sort by SemVer
    if a_is_semver and b_is_semver:
        if a_semver < b_semver:
            return 1
        elif a_semver > b_semver:
            return -1
        else:
            return 0

    # If either is not SemVer compliant, sort by date
    if a['date'] < b['date']:
        return 1
    elif a['date'] > b['date']:
        return -1
    else:
        return 0


def get_resource_with_retry(url, params=None, max_retries=5, backoff_factor=0.3):
    """get a resource with retry mechanism"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            print(f"Attempt {attempt + 1} failed to get {url} :{e}")
            time.sleep(backoff_factor * (2 ** attempt))  # Exponential backoff
            if attempt == max_retries - 1:
                raise  # Re-raise the last exception if all retries fail

if __name__ == '__main__':
    pass
    # # test get_all_versions
    # # http://search.maven.org/solrsearch/select?q=g:org.junit-pioneer+AND+a:junit-pioneer&core=gav&rows=200&wt=json
    # g = "org.junit-pioneer"
    # a = "junit-pioneer"
    # v = '1.9.1'
    # print(get_all_versions(g, a, v))
    
    # # test fetch_versions
    # g = "org.apache.logging.log4j"
    # a = "log4j-api"
    # v = '2.24.0'
    # # print(fetch_versions(g, a))
    # print(get_all_versions(g, a, v))