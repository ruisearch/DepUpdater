'''
    execute GoblinUpdater for RQ1
    GoblinWeaver should be executed firstly
'''
import os

import requests
import semver
from pyparsing import Word, alphas, nums, Literal, Group, ZeroOrMore, SkipTo
from io import StringIO
from typing import Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET
from datetime import datetime
import shutil
from dataclasses import dataclass
from tqdm import tqdm

import subprocess

import pandas as pd


@dataclass
class SolutionResult:
    module: List[str]
    # old_version: str
    new_version: str

@dataclass
class VersionInfo:
    version: str
    id: str
    published_epoch_millis: int
    
@dataclass
class DependencyInfo:
    group_id: str
    arch_id: str
    version: str
    scope: str

def get_versions(group_id: str, artifact_id: str) -> List[VersionInfo]:
    """
    Request the first 5 pages and sort. For non-semver versions, sort by publication time.
    """
    components = list()
    for i in range(0,5):
        url = f"https://central.sonatype.com/api/internal/browse/component/versions?sortField=normalizedVersion&sortDirection=desc&page={i}&size=20&filter=namespace:{group_id},name:{artifact_id}"
        response = requests.get(url)
        data = response.json()
        components+=data['components']
    # print(components)
    versions = [
        VersionInfo(
            version=component['version'],
            id=component['id'],
            published_epoch_millis=component['publishedEpochMillis']
        )
        for component in components
    ]

    # versions.sort(key=lambda v: v.published_epoch_millis, reverse=True)
    # versions.sort(key=lambda v: [int(x) for x in v.version.split('.')], reverse=True)
    try:
        versions.sort(key=lambda v: semver.VersionInfo.parse(v.version))
    except ValueError:
        versions.sort(key=lambda v: v.published_epoch_millis)
    return versions

# Get the interval between two versions
__version_cache = dict()
__get_version_cache_key = lambda x, y: f"{x}:{y}"
def get_version_distance(group_id: str, artifact_id: str, v1: str, v2: str) -> Optional[int]:
    if v1 == v2:
        return 0
    key = __get_version_cache_key(group_id, artifact_id)
    if key not in __version_cache:
        __version_cache[key] = get_versions(group_id, artifact_id)
    idx = list()
    for i, v in enumerate(__version_cache[key]):
        if v.version == v1 or v.version == v2:
            idx.append(i)

    return abs(idx[0]- idx[1])-1 if len(idx) == 2 else None

def get_latest_version(group_id: str, artifact_id: str) -> str:
    """
    If not in cache, request it; otherwise, return the last one.
    """
    key = __get_version_cache_key(group_id, artifact_id)
    if key not in __version_cache:
        __version_cache[key] = get_versions(group_id, artifact_id)

    return __version_cache[key][-1].version


ET.register_namespace('', 'http://maven.apache.org/POM/4.0.0')

class PomModifier:
    def __init__(self, file_path):
        self.file_path = file_path
        self.tree = ET.parse(file_path)
        self.root = self.tree.getroot()
        self.namespaces = {'': 'http://maven.apache.org/POM/4.0.0'}
        self.backup_file_path = ""
        self.properties = self._parse_properties()

    def _parse_properties(self) -> Dict[str, str]:
        """
        Parse properties
        Returns:
            Dict[str, str]: xml_key: xml_value
        """
        properties = {}
        properties_element = self.root.find('.//properties', self.namespaces)
        if properties_element is not None:
            for prop in properties_element:
                properties[prop.tag.lstrip("{"+self.namespaces['']+"}")] = prop.text
        return properties

    def list_dependency(self):
        """
        Print the dependencies in the current POM
        """
        dependencies = self.root.findall('.//dependencies/dependency', self.namespaces)
        for dep in dependencies:
            dep_group_id = dep.find('groupId', self.namespaces)
            dep_artifact_id = dep.find('artifactId', self.namespaces)
            if dep_group_id is not None and dep_artifact_id is not None:
                dep_version = dep.find('version', self.namespaces)
                if dep_version is not None:
                    print(f"artifactId:{dep_artifact_id.text}, version:{dep_version.text}")


    def modify(self, group_id: str, artifact_id: str, new_version: str) -> Optional[Tuple]:
        """
        Find the corresponding value, modify it if it exists, and return the values before and after the modification.
        """
        
        dependencies = self.root.findall('.//dependencies/dependency', self.namespaces)

        for dep in dependencies:
            dep_group_id = dep.find('groupId', self.namespaces)
            dep_artifact_id = dep.find('artifactId', self.namespaces)

            if dep_group_id is not None and dep_artifact_id is not None:
                if dep_group_id.text == group_id and dep_artifact_id.text == artifact_id:
                    dep_version = dep.find('version', self.namespaces)
                    if dep_version is not None:
                        _old_version = dep_version.text
                        if dep_version.text.startswith("$"):
                            _old_version = self.properties[f"{dep_version.text.strip('${').strip('}')}"]
                        dep_version.text = new_version
                        print(f"Updated {group_id}:{artifact_id} to version {new_version}")
                        return _old_version, new_version

        print(f"Dependency {group_id}:{artifact_id} not found!")
        return None
    def save(self):
        """
        Generate a backup of the original file based on the time.
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        self.backup_file_path = f"{self.file_path}.{timestamp}.bak"
        shutil.copy(self.file_path, self.backup_file_path)
        self.tree.write(self.file_path)
        
    def rollback(self):
        """
        Restore the file from the backup.
        """
        os.remove(self.file_path)
        shutil.copy(self.backup_file_path, self.file_path)


def _parse_result(result: List) -> SolutionResult:
    """
    The parsed result is approximately (['a', ':', 'b', ':', '1.2.3']), extract and parse.
    """
    x1=list(filter(lambda x: x != ":", result[1]))
    return SolutionResult(x1[:-1], x1[-1])


class GoblinUpdaterParser:
    module_part = Word(alphas + nums + "._-") + ZeroOrMore(Literal(":"))
    module_parts = Group(ZeroOrMore(module_part))
    version_part = Word(nums + ".")

    parser = Literal("(") + module_parts + ZeroOrMore(version_part) + Literal(")") + Literal(":") + version_part

    def __init__(self):
        self.exec_result = ""

    def exec(self, module_path, _cfg_path, _jar_path, _dweaver_url="http://localhost:8080"):
        cmd = ['bash', '-c', f'java -DweaverUrl={_dweaver_url} -DprojectPath={module_path} -DconfFile={_cfg_path} -jar {_jar_path}']
        try:
            self.exec_result = subprocess.run(cmd, text=True, timeout=4800, stdout=subprocess.PIPE).stdout
            print(self.exec_result)
        except subprocess.TimeoutExpired as e:
            self.exec_result = ""
            print(f"Timeout: {e}")
        except subprocess.CalledProcessError as e:
            self.exec_result = ""
            print(f"Check environment: {e}")
        return self

    def parse(self)->List[SolutionResult]:
        """
        Ignoring the text before 'solution', start parsing from the line after 'solution'
        """
        if self.exec_result == "":
            return []
        # buffer = StringIO(solution_with_version.strip())
        buffer = StringIO(self.exec_result.strip())

        while line := buffer.readline():
            if line.__contains__("## Solution:"):
                break
        
        return [_parse_result(m) for m in self.parser.searchString(buffer.read())]


def mvn_compile(_module_path: str) -> bool:
    cmd = ['bash', '-c', f"cd {_module_path} && mvn compile"]
    try:
        subprocess.check_call(cmd, text=True, timeout=4800)
    except subprocess.CalledProcessError:
        return False
    return True


def mvn_test(_module_path: str) -> bool:
    cmd = ['bash', '-c', f"cd {_module_path} && mvn test"]
    try:
        subprocess.check_call(cmd, text=True, timeout=4800)
    except subprocess.CalledProcessError:
        return False
    return True

def get_maven_dependencies(path) -> Optional[List[DependencyInfo]]:
    try:
        exec_result = subprocess.run(['bash', '-c', f'cd {path} && mvn dependency:tree'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except subprocess.CalledProcessError as e:
        print(f"Check env: {e}")
        return
    if exec_result.returncode != 0:
        print(f"Error executing mvn command: {exec_result.stderr}")
        print(f"if mvn not found, can exec: export PATH=$PATH:/home1/kaixuan/ray/apache-maven-3.9.5/bin/")
        return
    return parse_dependencies_tree(extract_dep_tree(exec_result.stdout))

def extract_dep_tree(output: str) -> str:
    """
    Extract the content between 'tree (default-cli) @' and 'BUILD SUCCESS'
    """
    start_marker = Literal(":tree (default-cli) @")
    end_marker = Literal("BUILD SUCCESS")
    content_parser =  SkipTo(start_marker) + SkipTo(end_marker)("content") + end_marker
    return content_parser.parseString(output)["content"]

def parse_dependencies_tree(output: str) -> List[DependencyInfo]:
    """
    The parsed result can be retrieved in a key-value (kv) format.
    """
    group = Word(alphas + ".")
    artifact = Word(alphas + "-")
    version = Word(nums + alphas + ".")
    scope = Word(alphas)
    dependency = group("group") + Literal(":") + artifact("artifact") + Literal(":jar:") + version("version") + Literal(":") + scope("scope")
    return [DependencyInfo(x["group"], x["artifact"], x["version"], x["scope"]) for x in dependency.searchString(output)]

if __name__ == "__main__":
    cfg_path = "/home1/kaixuan/ray/Baselines/goblinUpdater/gUpdaterConfig.yml"
    jar_path = "/home1/kaixuan/ray/Baselines/goblinUpdater/target/goblinUpdater-1.0.0-jar-with-dependencies.jar"
    dataset = [
        ('mall','mall-common'),
        ('mall','mall-security'),
        # ('guava','guava'),
        ('guava','guava-testlib'),
        ('dubbo','dubbo-test/dubbo-test-common'),
        # ('dubbo','dubbo-test/dubbo-test-check'),
        ('dubbo','dubbo-test/dubbo-test-modules'),
        # ('dubbo','dubbo-serialization/dubbo-serialization-api'),
        ('dubbo','dubbo-serialization/dubbo-serialization-fastjson2'),
        ('dubbo','dubbo-serialization/dubbo-serialization-hessian2'),
        # ('dubbo','dubbo-maven-plugin'),
        ('dubbo','dubbo-spring-boot/dubbo-spring-boot-3-autoconfigure'),
        # ('dubbo','dubbo-configcenter/dubbo-configcenter-apollo'),
        # ('dubbo','dubbo-configcenter/dubbo-configcenter-nacos'),
        # ('dubbo','dubbo-configcenter/dubbo-configcenter-file'),
        # ('dubbo','dubbo-configcenter/dubbo-configcenter-zookeeper'),
        ('dubbo','dubbo-metrics/dubbo-metrics-api'),
        ('dubbo','dubbo-metrics/dubbo-metrics-event'),
        # ('dubbo','dubbo-metrics/dubbo-metrics-prometheus'),
        ('dubbo','dubbo-metrics/dubbo-metrics-config-center'),
        # ('dubbo','dubbo-metrics/dubbo-metrics-metadata'),
        ('dubbo','dubbo-metrics/dubbo-metrics-default'),
        ('dubbo','dubbo-metrics/dubbo-metrics-netty'),
        ('dubbo','dubbo-metrics/dubbo-tracing'),
        ('dubbo','dubbo-plugin/dubbo-auth'),
        ('dubbo','dubbo-plugin/dubbo-filter-validation'),
        ('dubbo','dubbo-plugin/dubbo-spring-security'),
        ('dubbo','dubbo-plugin/dubbo-compiler'),
        # ('dubbo','dubbo-plugin/dubbo-qos-api'),
        ('dubbo','dubbo-plugin/dubbo-filter-cache'),
        ('dubbo','dubbo-remoting/dubbo-remoting-api'),
        # ('dubbo','dubbo-remoting/dubbo-remoting-netty4'),
        # ('dubbo','dubbo-remoting/dubbo-remoting-netty'),
        ('dubbo','dubbo-remoting/dubbo-remoting-zookeeper-curator5'),
        ('dubbo','dubbo-cluster'),
        ('dubbo','dubbo-rpc/dubbo-rpc-api'),
        # ('dubbo','dubbo-rpc/dubbo-rpc-dubbo'),
        ('dubbo','dubbo-rpc/dubbo-rpc-injvm'),
        ('dubbo','dubbo-demo/dubbo-demo-interface'),
        ('dubbo','dubbo-demo/dubbo-demo-spring-boot/dubbo-demo-spring-boot-interface'),
        ('netty','buffer'),
        # ('netty','handler-proxy'),
        ('netty','testsuite-autobahn'),
        # ('netty','handler-ssl-ocsp'),
        ('netty','testsuite-http2'),
        # ('netty','codec'),
        ('netty','codec-dns'),
        ('netty','codec-haproxy'),
        ('netty','codec-memcache'),
        ('netty','codec-mqtt'),
        ('netty','codec-redis'),
        ('netty','codec-smtp'),
        ('netty','codec-stomp'),
        ('netty','codec-socks'),
        ('netty','codec-xml'),
        # ('netty','common'),
        # ('netty','transport'),
        ('netty','transport-rxtx'),
        # ('netty','transport-sctp'),
        ('netty','transport-udt'),
        ('netty','example'),
        # ('netty','dev-tools'),
        ('java-design-patterns', 'monad'),
        ('java-design-patterns', 'value-object'),
        ('java-design-patterns', 'ambassador'),
        ('java-design-patterns', 'model-view-controller'),
        ('java-design-patterns', 'bridge'),
        ('java-design-patterns', 'facade'),
        ('java-design-patterns', 'event-driven-architecture'),
        ('java-design-patterns', 'lockable-object'),
        ('java-design-patterns', 'collection-pipeline'),
        ('java-design-patterns', 'interpreter'),
        ('java-design-patterns', 'resource-acquisition-is-initialization'),
        ('java-design-patterns', 'page-controller'),
        ('java-design-patterns', 'version-number'),
        ('java-design-patterns', 'command-query-responsibility-segregation'),
        ('java-design-patterns', 'data-locality'),
        ('java-design-patterns', 'double-checked-locking'),
        ('java-design-patterns', 'repository'),
        ('java-design-patterns', 'composite-entity'),
        ('java-design-patterns', 'gateway'),
        ('java-design-patterns', 'master-worker'),
        ('java-design-patterns', 'multiton'),
        ('java-design-patterns', 'monostate'),
        ('java-design-patterns', 'trampoline'),
        ('java-design-patterns', 'notification'),
        ('java-design-patterns', 'singleton'),
        ('java-design-patterns', 'throttling'),
        ('java-design-patterns', 'producer-consumer'),
        ('java-design-patterns', 'component'),
        ('java-design-patterns', 'object-pool'),
        ('java-design-patterns', 'table-module'),
        ('java-design-patterns', 'optimistic-offline-lock'),
        ('java-design-patterns', 'flux'),
        ('java-design-patterns', 'delegation'),
        ('java-design-patterns', 'extension-objects'),
        ('java-design-patterns', 'anti-corruption-layer'),
        ('java-design-patterns', 'dynamic-proxy'),
        ('java-design-patterns', 'caching'),
        ('java-design-patterns', 'bytecode'),
        # ('java-design-patterns', 'microservices-aggregrator'),
        ('java-design-patterns', 'servant'),
        ('java-design-patterns', 'visitor'),
        ('java-design-patterns', 'null-object'),
        # ('java-design-patterns', 'page-object'),
        ('java-design-patterns', 'fluent-interface'),
        ('java-design-patterns', 'event-sourcing'),
        ('java-design-patterns', 'reactor'),
        ('java-design-patterns', 'fanout-fanin'),
        ('java-design-patterns', 'client-session'),
        ('java-design-patterns', 'half-sync-half-async'),
        ('java-design-patterns', 'marker-interface'),
        ('java-design-patterns', 'function-composition'),
        ('java-design-patterns', 'promise'),
        # ('java-design-patterns', 'naked-objects'),
        ('java-design-patterns', 'saga'),
        # ('java-design-patterns', 'localization'),
        ('java-design-patterns', 'microservices-log-aggregation'),
        ('java-design-patterns', 'transaction-script'),
        ('java-design-patterns', 'poison-pill'),
        ('java-design-patterns', 'service-layer'),
        ('java-design-patterns', 'data-transfer-object'),
        ('java-design-patterns', 'data-mapper'),
        ('java-design-patterns', 'builder'),
        ('java-design-patterns', 'health-check'),
        ('java-design-patterns', 'specification'),
        ('java-design-patterns', 'strangler'),
        ('java-design-patterns', 'queue-based-load-leveling'),
        ('java-design-patterns', 'converter'),
        ('java-design-patterns', 'collecting-parameter'),
        # ('java-design-patterns', 'model-view-presenter'),
        ('java-design-patterns', 'proxy'),
        ('java-design-patterns', 'serialized-entity'),
        ('java-design-patterns', 'business-delegate'),
        ('java-design-patterns', 'combinator'),
        # ('java-design-patterns', 'etc'),
        ('java-design-patterns', 'layered-architecture'),
        # ('java-design-patterns', 'intercepting-filter'),
        ('java-design-patterns', 'data-access-object'),
        ('java-design-patterns', 'abstract-document'),
        ('java-design-patterns', 'virtual-proxy'),
        ('java-design-patterns', 'async-method-invocation'),
        ('java-design-patterns', 'observer'),
        ('java-design-patterns', 'filterer'),
        ('java-design-patterns', 'identity-map'),
        ('java-design-patterns', 'object-mother'),
        ('java-design-patterns', 'factory-method'),
        ('java-design-patterns', 'special-case'),
        ('java-design-patterns', 'chain-of-responsibility'),
        ('java-design-patterns', 'memento'),
        ('java-design-patterns', 'mediator'),
        ('java-design-patterns', 'abstract-factory'),
        ('java-design-patterns', 'callback'),
        ('java-design-patterns', 'domain-model'),
        ('java-design-patterns', 'data-bus'),
        ('java-design-patterns', 'leader-election'),
        ('java-design-patterns', 'service-to-worker'),
        ('java-design-patterns', 'acyclic-visitor'),
        ('java-design-patterns', 'registry'),
        # ('java-design-patterns', 'hexagonal-architecture'),
        ('java-design-patterns', 'front-controller'),
        ('java-design-patterns', 'model-view-intent'),
        ('java-design-patterns', 'type-object'),
        ('java-design-patterns', 'decorator'),
        ('java-design-patterns', 'service-locator'),
        ('java-design-patterns', 'composite'),
        ('java-design-patterns', 'strategy'),
        ('java-design-patterns', 'flyweight'),
        ('java-design-patterns', 'server-session'),
        ('java-design-patterns', 'subclass-sandbox'),
        ('java-design-patterns', 'dirty-flag'),
        ('java-design-patterns', 'twin'),
        ('java-design-patterns', 'active-object'),
        ('java-design-patterns', 'double-buffer'),
        ('java-design-patterns', 'game-loop'),
        ('java-design-patterns', 'context-object'),
        ('java-design-patterns', 'template-method'),
        ('java-design-patterns', 'separated-interface'),
        ('java-design-patterns', 'commander'),
        ('java-design-patterns', 'step-builder'),
        ('java-design-patterns', 'state'),
        ('java-design-patterns', 'tolerant-reader'),
        ('java-design-patterns', 'guarded-suspension'),
        ('java-design-patterns', 'sharding'),
        ('java-design-patterns', 'property'),
        ('java-design-patterns', 'balking'),
        ('java-design-patterns', 'currying'),
        # ('java-design-patterns', 'microservices-distributed-tracing'),
        ('java-design-patterns', 'event-aggregator'),
        ('java-design-patterns', 'leader-followers'),
        ('java-design-patterns', 'partial-response'),
        ('java-design-patterns', 'update-method'),
        ('java-design-patterns', 'private-class-data'),
        ('java-design-patterns', 'metadata-mapping'),
        ('java-design-patterns', 'prototype'),
        ('java-design-patterns', 'serialized-lob'),
        ('java-design-patterns', 'retry'),
        ('java-design-patterns', 'mute-idiom'),
        ('java-design-patterns', 'role-object'),
        # ('java-design-patterns', 'model-view-viewmodel'),
        ('java-design-patterns', 'event-based-asynchronous'),
        ('java-design-patterns', 'curiously-recurring-template-pattern'),
        ('java-design-patterns', 'adapter'),
        ('java-design-patterns', 'pipeline'),
        # ('java-design-patterns', 'presentation-model'),
        ('java-design-patterns', 'circuit-breaker'),
        ('java-design-patterns', 'factory-kit'),
        ('java-design-patterns', 'monitor'),
        ('java-design-patterns', 'double-dispatch'),
        ('java-design-patterns', 'single-table-inheritance'),
        ('java-design-patterns', 'unit-of-work'),
        ('java-design-patterns', 'event-queue'),
        ('java-design-patterns', 'factory'),
        # ('java-design-patterns', 'dependency-injection'),
        ('java-design-patterns', 'execute-around'),
        ('java-design-patterns', 'command'),
        ('java-design-patterns', 'spatial-partition'),
        # ('java-design-patterns', 'microservices-api-gateway'),
        ('java-design-patterns', 'feature-toggle'),
        ('java-design-patterns', 'composite-view'),
        ('java-design-patterns', 'parameter-object'),
        ('java-design-patterns', 'arrange-act-assert'),
        ('java-design-patterns', 'iterator'),
        ('java-design-patterns', 'lazy-loading'),
        ('easyexcel', 'easyexcel'),
        ('easyexcel', 'easyexcel-test'),
        ('easyexcel', 'easyexcel-support'),
        ('easyexcel', 'easyexcel-core'),
        # ('nacos', 'plugin'),
        ('nacos', 'plugin/environment'),
        ('nacos', 'plugin/trace'),
        ('nacos', 'plugin/datasource'),
        ('nacos', 'plugin/encryption'),
        ('nacos', 'plugin/config'),
        ('nacos', 'plugin/control'),
        ('nacos', 'plugin/auth'),
        ('nacos', 'common'),
        ('nacos', 'client'),
        # ('nacos', 'api'),
        # ('nacos', 'logger-adapter-impl'),
        ('nacos', 'logger-adapter-impl/log4j2-adapter'),
        ('nacos', 'logger-adapter-impl/logback-adapter-12'),
        ('nacos', 'consistency'),
        # ('nacos', 'plugin-default-impl'),
        ('nacos', 'plugin-default-impl/nacos-default-control-plugin'),
        # ('spring-boot-demo', 'demo-oauth'),
        # ('spring-boot-demo', 'demo-dubbo'),
        # ('spring-boot-demo', 'demo-dubbo/dubbo-common'),
        # ('spring-boot-demo', 'demo-admin'),
        ('WxJava', 'weixin-java-cp'),
        ('WxJava', 'weixin-graal'),
        # ('WxJava', 'spring-boot-starters'),
        ('WxJava', 'spring-boot-starters/wx-java-qidian-spring-boot-starter'),
        ('WxJava', 'spring-boot-starters/wx-java-miniapp-multi-spring-boot-starter'),
        ('WxJava', 'spring-boot-starters/wx-java-miniapp-spring-boot-starter'),
        ('WxJava', 'spring-boot-starters/wx-java-channel-multi-spring-boot-starter'),
        ('WxJava', 'spring-boot-starters/wx-java-cp-spring-boot-starter'),
        ('WxJava', 'spring-boot-starters/wx-java-open-spring-boot-starter'),
        ('WxJava', 'spring-boot-starters/wx-java-channel-spring-boot-starter'),
        ('WxJava', 'spring-boot-starters/wx-java-mp-multi-spring-boot-starter'),
        ('WxJava', 'spring-boot-starters/wx-java-mp-spring-boot-starter'),
        ('WxJava', 'spring-boot-starters/wx-java-pay-spring-boot-starter'),
        ('WxJava', 'spring-boot-starters/wx-java-cp-multi-spring-boot-starter'),
        ('WxJava', 'weixin-java-miniapp'),
        ('WxJava', 'weixin-java-mp'),
        ('WxJava', 'weixin-java-pay'),
        ('WxJava', 'weixin-java-qidian'),
        ('WxJava', 'weixin-java-channel'),
        ('WxJava', 'weixin-java-open'),
        ('WxJava', 'weixin-java-common'),
        # ('WxJava', 'others/weixin-java-osgi'),
        # ('WxJava', 'solon-plugins'),
        ('WxJava', 'solon-plugins/wx-java-pay-solon-plugin'),
        ('WxJava', 'solon-plugins/wx-java-open-solon-plugin'),
        ('WxJava', 'solon-plugins/wx-java-cp-multi-solon-plugin'),
        ('WxJava', 'solon-plugins/wx-java-miniapp-multi-solon-plugin'),
        ('WxJava', 'solon-plugins/wx-java-channel-solon-plugin'),
        ('WxJava', 'solon-plugins/wx-java-miniapp-solon-plugin'),
        ('WxJava', 'solon-plugins/wx-java-cp-solon-plugin'),
        ('WxJava', 'solon-plugins/wx-java-mp-solon-plugin'),
        ('WxJava', 'solon-plugins/wx-java-channel-multi-solon-plugin'),
        ('WxJava', 'solon-plugins/wx-java-qidian-solon-plugin'),
        ('WxJava', 'solon-plugins/wx-java-mp-multi-solon-plugin'),
        # ('zxing', 'core'),
        # ('zxing', 'zxing.appspot.com'),
        # ('zxing', 'javase')
    ]
    dataset_root_dir = "/home1/kaixuan/ray/Extended_dataset"
    module_paths=[]
    for module in dataset:
        relative_path = os.path.join(module[0], module[1])
        module_paths.append(os.path.join(dataset_root_dir, relative_path))
    
    module_data = list()
    compile_data = list()
    
    pbar = tqdm(total=len(module_paths), desc=f"goblinUpdater", position=0, leave=True)
    for mod_path in module_paths:
        # solutions = GoblinUpdaterParser().exec(mod_path, cfg_path, jar_path).parse()
        print(f"***** Processing {mod_path} *****")
        dep_tree_old = get_maven_dependencies(mod_path)
        dep_filtered_old = list(filter(lambda x: x.scope in ["compile", "runtime"], dep_tree_old))
        dep_ga_list = [(x.group_id, x.arch_id) for x in dep_filtered_old]
        
        solutions = GoblinUpdaterParser().exec(mod_path, cfg_path, jar_path).parse()
        modifier = PomModifier(rf"{mod_path}/pom.xml")
        modifier.list_dependency()
        for solution in solutions:
            if len(solution.module) == 0:
                continue
            group_id, artifact_id = solution.module[0], solution.module[1]
            if (group_id, artifact_id) not in dep_ga_list:
                continue
            if solution.module == ["ROOT"]:
                continue
            result = modifier.modify(group_id, artifact_id, solution.new_version)
            if result is not None:
                # old version, new_version
                ov , nv = result[0], result[1]
                # latest_version
                lv = get_latest_version(group_id, artifact_id)

                module_data.append(
                    {
                        "path": mod_path,
                        "group_id": solution.module[0],
                        "artifact_id": solution.module[1],
                        "version_old":ov,
                        "version_new": nv,
                        "original_tech_lag": get_version_distance(group_id, artifact_id, ov, lv),
                        "current_tech_lag": get_version_distance(group_id, artifact_id, nv, lv)
                    }
                )
        modifier.save()

        dep_tree_new = get_maven_dependencies(mod_path)
        dep_filtered_new = list(filter(lambda x: x.scope in ["compile", "runtime"], dep_tree_new))

        compile_success = mvn_compile(mod_path)
        test_success = mvn_test(mod_path)
        compile_data.append({
            "path": mod_path,
            "compile_success:": compile_success,
            "test_pass": test_success,
            "original_dep": len(dep_filtered_old),
            "current_dep_count": len(dep_filtered_new),
            "original_tech_lag": 0,
            "current_tech_lag": 0,
        })
        # print(f"{mod_path}: compile:{compile_success}, test:{test_success}")
        modifier.rollback()
        
        pbar.update(1)
    pbar.close()

    df_module = pd.DataFrame(module_data)
    df_compile = pd.DataFrame(compile_data)

    for mod_path in module_paths:
        compile_mask = df_compile["path"] == mod_path
        module_mask = df_module["path"] == mod_path
        df_compile.loc[compile_mask, "original_tech_lag"] = df_module[module_mask]["original_tech_lag"].sum()
        df_compile.loc[compile_mask, "current_tech_lag"] = df_module[module_mask]["current_tech_lag"].sum()

    pd.set_option('display.width',None)
    df_compile["reduced_tech_lag"] =  df_compile["original_tech_lag"] - df_compile["current_tech_lag"]
    df_compile["reduced_dep_count"] =  df_compile["original_dep"] - df_compile["current_dep_count"]

    print(df_module)
    print(df_compile)
    
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    df_module.to_csv(f"./module_data_{timestamp}.csv")
    df_compile.to_csv(f"./compile_data_{timestamp}.csv")