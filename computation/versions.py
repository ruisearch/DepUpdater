"""get and sort all versions of a dependency"""
import copy
import time
from functools import cmp_to_key

import semver
import requests


def get_all_versions(groupId, artifactId, original_version):
    """main function to get all versions of a dependency to be computed"""
    all_versions = fetch_versions(groupId, artifactId)
    # the version to be computed are the versions after the original version
    original_version_idx = find_original_version_idx(all_versions, original_version)
    if original_version_idx == -1:
        print(f"Fail to find the original version {original_version} in {groupId}:{artifactId}")
        return []
    return all_versions[original_version_idx :]

def find_original_version_idx(all_versions, original_version):
    """find the index of the original version in all versions"""
    for idx, version in enumerate(all_versions):
        if version == original_version:
            return idx
    return -1

def fetch_versions(groupId, artifactId):
    """fetch all versions of the dependency"""
    url = f"http://search.maven.org/solrsearch/select?q=g:{groupId}+AND+a:{artifactId}&core=gav&rows=20&wt=json"
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
    # only return the version string
    all_versions = [version['version'] for version in all_versions]
    return all_versions

def version_comparator(a, b):
    # Try to parse versions as SemVer
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
            return -1
        elif a_semver > b_semver:
            return 1
        else:
            return 0

    # If either is not SemVer compliant, sort by date
    if a['date'] < b['date']:
        return -1
    elif a['date'] > b['date']:
        return 1
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
    # test get_all_versions
    g = "net.bytebuddy"
    a = "byte-buddy"
    v = '1.12.19'
    print(get_all_versions(g, a, v))