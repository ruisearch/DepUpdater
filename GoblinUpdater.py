import os

import pyparsing
import requests
import semver
from pyparsing import Word, alphas, nums, Literal, Group, ZeroOrMore, SkipTo
from io import StringIO
from typing import List, Optional, Tuple, Any, Callable
import xml.etree.ElementTree as ET
from datetime import datetime
import shutil
from dataclasses import dataclass

import subprocess

import pandas as pd

import json
import concurrent.futures
import logging
import re
from tqdm import tqdm
from constants import DATA_DIR, RET_DIR, set_log_path
from preprocess.Restore import Restore
from evaluation.dep_count import count_deps
from computation.versions import get_versions

# solution_with_version = """[INFO ] 2025/02/15 18:15:46 ## Solution:
# [INFO ] 2025/02/15 18:15:46 (com.fasterxml.jackson.core:jackson-databind:2.17.2) : 1.0
# [INFO ] 2025/02/15 18:15:46 (org.mockito:mockito-core:5.2.0) : 1.0
# [INFO ] 2025/02/15 18:15:46 (com.google.code.gson:gson:2.10.1) : 1.0
# [INFO ] 2025/02/15 18:15:46 (commons-io:commons-io:2.16.1) : 1.0
# [INFO ] 2025/02/15 18:15:46 (ROOT) : 1.0
# [INFO ] 2025/02/15 18:15:46 (net.sf.jopt-simple:jopt-simple:5.0.4) : 1.0
# [INFO ] 2025/02/15 18:15:46 (junit:junit:4.13.2) : 1.0
# [INFO ] 2025/02/15 18:15:46 (org.slf4j:slf4j-simple:1.7.36) : 1.0
# [INFO ] 2025/02/15 18:15:46 (org.mockito:mockito-inline:5.2.0) : 1.0
# [INFO ] 2025/02/15 18:15:46 (com.fasterxml.jackson.core:jackson-core:2.17.2) : 1.0
# [INFO ] 2025/02/15 18:15:46 (com.googlecode.aviator:aviator:5.4.3) : 1.0
# [INFO ] 2025/02/15 18:15:46 (com.github.seancfoley:ipaddress:5.5.1) : 1.0
# [INFO ] 2025/02/15 18:15:46 (org.slf4j:slf4j-api:1.7.36) : 1.0
# [INFO ] 2025/02/15 18:15:46 (org.openjdk.jmh:jmh-generator-annprocess:1.37) : 1.0
# [INFO ] 2025/02/15 18:15:46 (org.apache.commons:commons-math3:3.6.1) : 1.0
# [INFO ] 2025/02/15 18:15:46 (net.bytebuddy:byte-buddy:1.14.1) : 1.0
# [INFO ] 2025/02/15 18:15:46 (com.fasterxml.jackson.core:jackson-annotations:2.17.2) : 1.0
# [INFO ] 2025/02/15 18:15:46 (org.openjdk.jmh:jmh-core:1.37) : 1.0
# [INFO ] 2025/02/15 18:15:46 (org.hamcrest:hamcrest-core:1.3) : 1.0
# [INFO ] 2025/02/15 18:15:46 (org.apache.commons:commons-csv:1.10.0) : 1.0
# [INFO ] 2025/02/15 18:15:46 (net.bytebuddy:byte-buddy-agent:1.14.1) : 1.0"""
def dataset():
    """set modules in the dataset"""
    modules = [
        # 226 modules
        # ('mall','mall-security'),
        # ('mall','mall-common'),
        # # ('guava','guava'),
        # # ('guava','guava-testlib'),
        # ('dubbo','dubbo-test/dubbo-test-common'),
        # ('dubbo','dubbo-test/dubbo-test-check'),
        # ('dubbo','dubbo-test/dubbo-test-modules'),
        # # ('dubbo','dubbo-serialization/dubbo-serialization-api'),
        # # ('dubbo','dubbo-serialization/dubbo-serialization-fastjson2'),
        # ('dubbo','dubbo-serialization/dubbo-serialization-hessian2'),
        # # ('dubbo','dubbo-maven-plugin'),
        # ('dubbo','dubbo-spring-boot/dubbo-spring-boot-3-autoconfigure'),
        # # ('dubbo','dubbo-configcenter/dubbo-configcenter-apollo'),
        # # ('dubbo','dubbo-configcenter/dubbo-configcenter-nacos'),
        # # ('dubbo','dubbo-configcenter/dubbo-configcenter-file'),
        # # ('dubbo','dubbo-configcenter/dubbo-configcenter-zookeeper'),
        # # ('dubbo','dubbo-metrics/dubbo-metrics-api'),
        # ('dubbo','dubbo-metrics/dubbo-metrics-event'),
        # # ('dubbo','dubbo-metrics/dubbo-metrics-prometheus'),
        # ('dubbo','dubbo-metrics/dubbo-metrics-config-center'),
        # # ('dubbo','dubbo-metrics/dubbo-metrics-metadata'),
        # # ('dubbo','dubbo-metrics/dubbo-metrics-default'),
        # ('dubbo','dubbo-metrics/dubbo-metrics-netty'),
        # # ('dubbo','dubbo-metrics/dubbo-tracing'),
        # ('dubbo','dubbo-plugin/dubbo-auth'),
        # # ('dubbo','dubbo-plugin/dubbo-filter-validation'),
        # # ('dubbo','dubbo-plugin/dubbo-spring-security'),
        # ('dubbo','dubbo-plugin/dubbo-compiler'),
        # # ('dubbo','dubbo-plugin/dubbo-qos-api'),
        # ('dubbo','dubbo-plugin/dubbo-filter-cache'),
        # ('dubbo','dubbo-remoting/dubbo-remoting-api'),
        # # ('dubbo','dubbo-remoting/dubbo-remoting-netty4'),
        # # ('dubbo','dubbo-remoting/dubbo-remoting-netty'),
        # # ('dubbo','dubbo-remoting/dubbo-remoting-zookeeper-curator5'),
        # ('dubbo','dubbo-cluster'),
        # ('dubbo','dubbo-rpc/dubbo-rpc-api'),
        # # ('dubbo','dubbo-rpc/dubbo-rpc-dubbo'),
        # ('dubbo','dubbo-rpc/dubbo-rpc-injvm'),
        # ('dubbo','dubbo-demo/dubbo-demo-interface'),
        # ('dubbo','dubbo-demo/dubbo-demo-spring-boot/dubbo-demo-spring-boot-interface'),
        # # ('netty','buffer'),
        # # ('netty','handler-proxy'),
        # ('netty','testsuite-autobahn'),
        # # ('netty','handler-ssl-ocsp'),
        # ('netty','testsuite-http2'),
        # # ('netty','codec'),
        # ('netty','codec-dns'),
        # ('netty','codec-haproxy'),
        # ('netty','codec-memcache'),
        # ('netty','codec-mqtt'),
        # ('netty','codec-redis'),
        # ('netty','codec-smtp'),
        # ('netty','codec-stomp'),
        # ('netty','codec-socks'),
        # ('netty','codec-xml'),
        # # ('netty','common'),
        # # ('netty','transport'),
        # ('netty','transport-rxtx'),
        # # ('netty','transport-sctp'),
        # ('netty','transport-udt'),
        # ('netty','example'),
        # # ('netty','dev-tools'),
        # ('java-design-patterns', 'monad'),
        # ('java-design-patterns', 'value-object'),
        # ('java-design-patterns', 'ambassador'),
        # ('java-design-patterns', 'model-view-controller'),
        # ('java-design-patterns', 'bridge'),
        # ('java-design-patterns', 'facade'),
        # ('java-design-patterns', 'event-driven-architecture'),
        # ('java-design-patterns', 'lockable-object'),
        # ('java-design-patterns', 'collection-pipeline'),
        # ('java-design-patterns', 'interpreter'),
        # ('java-design-patterns', 'resource-acquisition-is-initialization'),
        # ('java-design-patterns', 'page-controller'),
        # ('java-design-patterns', 'version-number'),
        # # ('java-design-patterns', 'command-query-responsibility-segregation'),
        # ('java-design-patterns', 'data-locality'),
        # ('java-design-patterns', 'double-checked-locking'),
        # ('java-design-patterns', 'repository'),
        # ('java-design-patterns', 'composite-entity'),
        # ('java-design-patterns', 'gateway'),
        # ('java-design-patterns', 'master-worker'),
        # ('java-design-patterns', 'multiton'),
        # ('java-design-patterns', 'monostate'),
        # ('java-design-patterns', 'trampoline'),
        # ('java-design-patterns', 'notification'),
        # ('java-design-patterns', 'singleton'),
        # ('java-design-patterns', 'throttling'),
        # ('java-design-patterns', 'producer-consumer'),
        # ('java-design-patterns', 'component'),
        # ('java-design-patterns', 'object-pool'),
        # ('java-design-patterns', 'table-module'),
        # ('java-design-patterns', 'optimistic-offline-lock'),
        # ('java-design-patterns', 'flux'),
        # ('java-design-patterns', 'delegation'),
        # ('java-design-patterns', 'extension-objects'),
        # ('java-design-patterns', 'anti-corruption-layer'),
        # ('java-design-patterns', 'dynamic-proxy'),
        # ('java-design-patterns', 'caching'),
        # ('java-design-patterns', 'bytecode'),
        # # ('java-design-patterns', 'microservices-aggregrator'),
        # ('java-design-patterns', 'servant'),
        # ('java-design-patterns', 'visitor'),
        # ('java-design-patterns', 'null-object'),
        # # ('java-design-patterns', 'page-object'),
        # ('java-design-patterns', 'fluent-interface'),
        # ('java-design-patterns', 'event-sourcing'),
        # ('java-design-patterns', 'reactor'),
        # ('java-design-patterns', 'fanout-fanin'),
        # ('java-design-patterns', 'client-session'),
        # ('java-design-patterns', 'half-sync-half-async'),
        # ('java-design-patterns', 'marker-interface'),
        # ('java-design-patterns', 'function-composition'),
        # ('java-design-patterns', 'promise'),
        # # ('java-design-patterns', 'naked-objects'),
        # ('java-design-patterns', 'saga'),
        # # ('java-design-patterns', 'localization'),
        # ('java-design-patterns', 'microservices-log-aggregation'),
        # ('java-design-patterns', 'transaction-script'),
        # ('java-design-patterns', 'poison-pill'),
        # # ('java-design-patterns', 'service-layer'),
        # ('java-design-patterns', 'data-transfer-object'),
        # ('java-design-patterns', 'data-mapper'),
        # ('java-design-patterns', 'builder'),
        # ('java-design-patterns', 'health-check'),
        # ('java-design-patterns', 'specification'),
        # ('java-design-patterns', 'strangler'),
        # ('java-design-patterns', 'queue-based-load-leveling'),
        # ('java-design-patterns', 'converter'),
        # ('java-design-patterns', 'collecting-parameter'),
        # # ('java-design-patterns', 'model-view-presenter'),
        # ('java-design-patterns', 'proxy'),
        # ('java-design-patterns', 'serialized-entity'),
        # ('java-design-patterns', 'business-delegate'),
        # ('java-design-patterns', 'combinator'),
        # # ('java-design-patterns', 'etc'),
        # ('java-design-patterns', 'layered-architecture'),
        # # ('java-design-patterns', 'intercepting-filter'),
        # ('java-design-patterns', 'data-access-object'),
        # ('java-design-patterns', 'abstract-document'),
        # ('java-design-patterns', 'virtual-proxy'),
        # ('java-design-patterns', 'async-method-invocation'),
        # ('java-design-patterns', 'observer'),
        # ('java-design-patterns', 'filterer'),
        # ('java-design-patterns', 'identity-map'),
        # ('java-design-patterns', 'object-mother'),
        # ('java-design-patterns', 'factory-method'),
        # ('java-design-patterns', 'special-case'),
        # ('java-design-patterns', 'chain-of-responsibility'),
        # ('java-design-patterns', 'memento'),
        # ('java-design-patterns', 'mediator'),
        # ('java-design-patterns', 'abstract-factory'),
        # ('java-design-patterns', 'callback'),
        # ('java-design-patterns', 'domain-model'),
        # ('java-design-patterns', 'data-bus'),
        # ('java-design-patterns', 'leader-election'),
        # ('java-design-patterns', 'service-to-worker'),
        # ('java-design-patterns', 'acyclic-visitor'),
        # ('java-design-patterns', 'registry'),
        # # ('java-design-patterns', 'hexagonal-architecture'),
        # ('java-design-patterns', 'front-controller'),
        # ('java-design-patterns', 'model-view-intent'),
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
    return modules

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

def walk(sn: List[Any], d: int, f):
    for s in sn:
        f(s, d)
        if s.sub_nodes:
            walk(s.sub_nodes, d+1, f)

@dataclass
class DependencyInfo:
    group_id: str
    arch_id: str
    version: str
    scope: Optional[str]


@dataclass
class DepTreeNode:
    level: int
    dep_info: DependencyInfo
    sub_nodes: List[Any]

    def select_node(self, gid, aid):
        if self.dep_info.group_id == gid and self.dep_info.arch_id == aid:
            return self

        result = []
        def _set(x,d):
            if x.dep_info.group_id == gid and x.dep_info.arch_id == aid:
                result.append(x)
        walk(self.sub_nodes, 0, lambda x, d: _set(x,d))
        return result.pop()

    def filter_scope(self):
        results = []
        _scopes = ["runtime", "compile"]
        walk(self.sub_nodes, 0, lambda x, d: results.append(x) if x.dep_info.scope in _scopes else None)
        return results


def get_all_versions(group_id: str, artifact_id: str) -> List[VersionInfo]:
    # components = list()
    # for i in range(0, 5):
    #     url = f"https://central.sonatype.com/api/internal/browse/component/versions?sortField=normalizedVersion&sortDirection=desc&page={i}&size=20&filter=namespace:{group_id},name:{artifact_id}"
    #     response = requests.get(url)
    #     data = response.json()
    #     components += data['components']
    # versions = [
    #     VersionInfo(
    #         version=component['version'],
    #         id=component['id'],
    #         published_epoch_millis=component['publishedEpochMillis']
    #     )
    #     for component in components
    # ]

    # # versions.sort(key=lambda v: v.published_epoch_millis, reverse=True)
    # # versions.sort(key=lambda v: [int(x) for x in v.version.split('.')], reverse=True)
    # try:
    #     versions.sort(key=lambda v: semver.VersionInfo.parse(v.version))
    # except ValueError:
    #     versions.sort(key=lambda v: v.published_epoch_millis)
    # return versions
    
    all_versions = get_versions(group_id, artifact_id)
    actual_all_versions = []
    # exclude pre-release versions
    for version in all_versions:
        upper_version = version.upper()
        if 'SNAPSHOT' in upper_version or 'ALPHA' in upper_version or 'BETA' in upper_version or 'RC' in upper_version:
            continue
        actual_all_versions.append(version)
    return [VersionInfo(version=v, id="", published_epoch_millis=0) for v in actual_all_versions]
    


# 获取两个版本之间的间隔
__version_cache = dict()
__get_version_cache_key = lambda x, y: f"{x}:{y}"


def get_version_distance(group_id: str, artifact_id: str, v1: str, v2: str) -> Optional[int]:
    if v1 == v2:
        return 0
    key = __get_version_cache_key(group_id, artifact_id)
    if key not in __version_cache:
        __version_cache[key] = get_all_versions(group_id, artifact_id)
    idx = list()
    for i, v in enumerate(__version_cache[key]):
        if v.version == v1 or v.version == v2:
            idx.append(i)

    return abs(idx[0] - idx[1]) - 1 if len(idx) == 2 else None


def get_latest_version(group_id: str, artifact_id: str):
    # print(group_id, artifact_id)
    key = __get_version_cache_key(group_id, artifact_id)
    if key not in __version_cache:
        __version_cache[key] = get_all_versions(group_id, artifact_id)
    # print(len(__version_cache[key]))
    if len(__version_cache[key]) == 0:
        # cann't get version from remote repository
        # means the artifact is a local module
        return None
    
    # # debug
    # for i in range(len(__version_cache[key])):
    #     print(__version_cache[key][i].version)
    # return __version_cache[key][-1].version
    # now, the latest version is the first one
    return __version_cache[key][0].version


ET.register_namespace('', 'http://maven.apache.org/POM/4.0.0')


class PomModifier:
    def __init__(self, file_path):
        self.file_path = file_path
        self.tree = ET.parse(file_path)
        self.root = self.tree.getroot()
        self.namespaces = {'': 'http://maven.apache.org/POM/4.0.0'}
        self.backup_file_path = ""
        self.properties = self._parse_properties()

    def _parse_properties(self):
        """
        解析 properties 元素并返回一个字典，包含所有的属性及其值
        """
        properties = {}
        properties_element = self.root.find('.//properties', self.namespaces)
        if properties_element is not None:
            for prop in properties_element:
                properties[prop.tag.lstrip("{" + self.namespaces[''] + "}")] = prop.text
        return properties

    def list_dependency(self):
        dependencies = self.root.findall('.//dependencies/dependency', self.namespaces)
        for dep in dependencies:
            dep_group_id = dep.find('groupId', self.namespaces)
            dep_artifact_id = dep.find('artifactId', self.namespaces)
            if dep_group_id is not None and dep_artifact_id is not None:
                dep_version = dep.find('version', self.namespaces)
                if dep_version is not None:
                    print(f"artifactId:{dep_artifact_id.text}, version:{dep_version.text}")

    def modify(self, group_id, artifact_id, new_version) -> Optional[Tuple]:
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
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        self.backup_file_path = f"{self.file_path}.{timestamp}.bak"
        shutil.copy(self.file_path, self.backup_file_path)
        self.tree.write(self.file_path)

    def rollback(self):
        os.remove(self.file_path)
        shutil.copy(self.backup_file_path, self.file_path)


def _parse_result(result: List) -> SolutionResult:
    x1 = list(filter(lambda x: x != ":", result[1]))
    return SolutionResult(x1[:-1], x1[-1])


class GoblinUpdaterParser:
    module_part = Word(alphas + nums + "._-") + ZeroOrMore(Literal(":"))
    module_parts = Group(ZeroOrMore(module_part))
    version_part = Word(nums + ".")

    parser = Literal("(") + module_parts + ZeroOrMore(version_part) + Literal(")") + Literal(":") + version_part

    def __init__(self):
        self.exec_result = ""

    def exec(self, module_path, _cfg_path, _jar_path, _dweaver_url="http://localhost:8080"):
        print(f"goblinUpdater exec: {module_path}")
        cmd = ['bash', '-c',
               f'java -DweaverUrl={_dweaver_url} -DprojectPath={module_path} -DconfFile={_cfg_path} -jar {_jar_path}']
        # 存放结果的文件所在目录data/goblin_result/
        ret_dir = os.path.join("data", "goblin_result")
        os.makedirs(ret_dir, exist_ok=True)
        try:
            self.exec_result = subprocess.run(cmd, text=True, timeout=4800, stdout=subprocess.PIPE).stdout
            # self.exec_result = subprocess.run(cmd, text=True, timeout=2, stdout=subprocess.PIPE).stdout
            # print(self.exec_result) 
        except subprocess.TimeoutExpired as e:
            self.exec_result = ""
            print(f"Timeout: {e}")
        except subprocess.CalledProcessError as e:
            self.exec_result = ""
            print(f"Check environment: {e}")
        # 结果存放到一个文件中,文件名为module的最后一级文件夹名
        ret_file = os.path.join(ret_dir, os.path.basename(module_path) + ".txt")
        with open(ret_file, "w") as f:
            f.write(self.exec_result)
        return self

    def parse(self) -> List[SolutionResult]:
        if self.exec_result == "":
            return []
        # buffer = StringIO(solution_with_version.strip())
        buffer = StringIO(self.exec_result.strip())

        while line := buffer.readline():
            if line.__contains__("## Solution:"):
                break

        return [_parse_result(m) for m in self.parser.searchString(buffer.read())]


# def mvn_compile(_module_path: str) -> bool:
    # cmd = ['bash', '-c', f"cd {_module_path} && mvn compile"]
    # try:
    #     subprocess.check_call(cmd, text=True, timeout=4800)
    # except subprocess.CalledProcessError:
    #     return False
    # return True
def mvn_compile(repo_path: str, module_relative_path: str) -> bool:
    print('****compile****')
    # firstly, mvn compile in module folder
    command = f"cd {os.path.join(repo_path, module_relative_path)} &&\
        mvn -Dmaven.test.skip=true -Dcheckstyle.skip=true -Denforcer.skip=true -Dflatten.skip=true \
            -Dspotless.check.skip=true compile"
    try:
        result = subprocess.run(command, shell=True, text=True, capture_output=True)
        if result.returncode != 0:
            # second, mvn compile in root folder with -pl -am
            command = f"cd {repo_path} && mvn -Dmaven.test.skip=true -Dcheckstyle.skip=true -Denforcer.skip=true \
                -Dflatten.skip=true -Dspotless.check.skip=true \
                    -pl {module_relative_path} compile -am"
            result = subprocess.run(command, shell=True, text=True, capture_output=True)
            if result.returncode != 0:
                # recompile fails
                print("Compile failed.")
                return False
        print("Compile success.")
        return True
    except subprocess.SubprocessError as e:
        print(f"An error occured while execute the command: {e}")
        return False


# def mvn_test(_module_path: str) -> bool:
#     cmd = ['bash', '-c', f"cd {_module_path} && mvn test"]
#     try:
#         subprocess.check_call(cmd, text=True, timeout=4800)
#     except subprocess.CalledProcessError:
#         return False
#     return True
def mvn_test(repo_path: str, module_relative_path: str) -> bool:
    print('****test****')
    # first, mvn test in module folder
    command = f"cd {os.path.join(repo_path, module_relative_path)} && \
        mvn -Dcheckstyle.skip=true -Denforcer.skip=true -Dflatten.skip=true -Dspotless.check.skip=true test"
    try:
        result = subprocess.run(command, shell=True, text=True, capture_output=True)
        if result.returncode != 0:
            # second, mvn test in root folder with -pl -am
            command = f"cd {repo_path} && \
                mvn -Dcheckstyle.skip=true -Denforcer.skip=true -Dflatten.skip=true -Dspotless.check.skip=true\
                    -pl {module_relative_path} -am test"
            result = subprocess.run(command, shell=True, text=True, capture_output=True)
            if result.returncode != 0:
                # test fails
                print("Test failed.")
                return False
        print("Test success.")
        return True
    except subprocess.SubprocessError as e:
        print(f"An error occured while execute the command: {e}")
        return False


# def get_maven_dependencies(path):
    # print("get_maven_dependencies", f'cd {path} && mvn dependency:tree')
    # try:
    #     exec_result = subprocess.run(['bash', '-c', f'cd {path} && mvn dependency:tree'], stdout=subprocess.PIPE,
    #                                  stderr=subprocess.PIPE, text=True)
    # except subprocess.CalledProcessError as e:
    #     print(f"Check env: {e}")
    #     return
    # if exec_result.returncode != 0:
    #     print("get_maven_dependencies", exec_result.stdout)
    #     print(f"Error executing mvn command: {exec_result.stderr}")
    #     print(f"if mvn not found, can exec: export PATH=$PATH:/home/ray/Env/maven/apache-maven-3.9.5/bin/")
    #     return
    # return parse_dependencies_tree(extract_dep_tree(exec_result.stdout))
    
    


# def extract_dep_tree(output):
#     start_marker = Literal(":tree (default-cli) @") + Word(nums + alphas + ".-") + Literal("---")
#     end_marker = Literal("BUILD SUCCESS")
#     content_parser = SkipTo(start_marker) + SkipTo(end_marker)("content") + end_marker
#     return content_parser.parseString(output)["content"].replace("[INFO] ", "")


# def parse_dependencies_tree(output: str):
#     # 去除--- dependency:2.10:tree (default-cli) @ netty-all ---
#     output = "\n".join(output.split("\n")[1:])
#     print("parse_dependencies_tree", output)
#     prefix = pyparsing.Optional(Word("|\ +-"))
#     group = Word(nums + alphas + ".-")
#     artifact = Word(nums + alphas + ".-")
#     version = Word(nums + alphas + ".-")
#     scope = Word(alphas)
#     dependency = prefix("prefix") + group("group") + Literal(":") + artifact("artifact") + Literal(":jar:") + version(
#         "version") + pyparsing.Optional(Literal(":")) + pyparsing.Optional(scope("scope"))

#     results = [
#         DepTreeNode(
#             int(len(x["prefix"]) / 3) if "prefix" in x else 0,
#             DependencyInfo(x["group"], x["artifact"], x["version"], x["scope"] if "scope" in x else None),
#             [],
#         ) for x in dependency.searchString(output)
#     ]

#     def transform(data: List[DepTreeNode]):
#         result = []
#         stack: List[DepTreeNode] = list()
#         for item in data:
#             while stack and stack[-1].level >= item.level:
#                 stack.pop()
#             if stack:
#                 stack[-1].sub_nodes.append(item)
#             else:
#                 result.append(item)
#             stack.append(item)
#         return result[0]

#     # f = transform(results)
#     # def walk(sn: List[DepTreeNode], d: int):
#     #     for s in sn:
#     #         print("|  "*d,s.dep_info.group_id, s.dep_info.arch_id, d)
#     #         if s.sub_nodes:
#     #             walk(s.sub_nodes, d+1)
#     #
#     # walk(f.sub_nodes, 0)

#     return transform(results)

def mvn_tree(path_to_folder:str, relative_path_to_module:str):
    """execute mvn dependency:tree"""
    command = f"cd {path_to_folder} && mvn dependency:tree -pl {relative_path_to_module} -am -Dverbose -fae"
    result = subprocess.run(command, shell=True, text=True, capture_output=True)
    if result.returncode != 0:
        # cann't generate dependency graph
        return None
    return result.stdout

def tree_to_json(tree_path:str, path_to_cloned_folder:str, relative_path_to_module:str, whether_update:bool):
    """parse verbose_tree.txt to get the dependency graph and store it in the json file
    return the path to the json file
    """
    if whether_update:
        # 需要更新后的树
        json_path = os.path.join(DATA_DIR,'goblinUpdater', \
            os.path.basename(path_to_cloned_folder), relative_path_to_module, 'current_version.json')
    else:
        json_path = os.path.join(DATA_DIR, 'goblinUpdater',\
            os.path.basename(path_to_cloned_folder), relative_path_to_module, 'original_version.json')
    # 如果json已经存在，直接读取
    if os.path.exists(json_path):
        return json_path

    if not os.path.exists(tree_path):
        # mvn dependency:tree to generate dependency graph
        tree = mvn_tree(path_to_cloned_folder, relative_path_to_module)
        if tree is None:
            # cannlt generate dependency graph
            return None
        with open(tree_path, 'w', encoding='utf-8') as f:
            f.write(tree)
    else:
        with open(tree_path, 'r', encoding='utf-8') as f:
            tree = f.read()

    res = Restore(path_to_cloned_folder, relative_path_to_module, tree_path,[],[])
    # extract the original dependency graph from verbose_tree.txt
    # inspired by preprocess/Restore.py
    block_pattern = r'\[INFO\] Building .+?\n\[INFO\].+?from (.*?)pom.xml\n\[INFO\] -+?\[ (.+?) \]-+?\n.*?\[INFO\] (\S+?):(\S+?):\S+?:(\S+?)\n(.+?)\[INFO\] -'
    blocks = re.finditer(block_pattern, tree, flags=re.DOTALL)
    deps = None
    for block in blocks:
        if relative_path_to_module == '.':
            flag = (block.group(1) == '')
        elif relative_path_to_module.endswith('/'):
            # the second parameter represents the relative path to the module ends with '/'
            # block.group(1) endswith '/'
            flag = (block.group(1) == relative_path_to_module)
        else :
            flag = (block.group(1) == relative_path_to_module+'/')
        if block.group(2) == 'jar' and flag:
            res.client_groupId = block.group(3)
            res.client_artifactId = block.group(4)
            res.client_version = block.group(5)
            deps = res.parse_all_dep(block.group(6))
            break
    valid_deps, omitted_deps = res.filter_dep(deps)
    res.change_valid_deps(valid_deps)
    res.change_omitted_deps(omitted_deps)
    mappings = [{'GroupId':res.client_groupId, 'ArtifactId':res.client_artifactId,\
            'Original_Version':res.client_version, 'Best_Version':'', 'Type':'',\
                'Depth':0, 'Count':0, 'Dependents':[]}] # add client at first
    num_workers = os.cpu_count()
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = []
        for valid_dep in valid_deps:
            futures.append(executor.submit(res.process_a_valid_dep, valid_dep, omitted_deps))
    for future in futures:
        mappings.append(future.result())

    res.process_omitted_deps(valid_deps, omitted_deps, mappings)
    res.prune_graph(mappings, False)
    mappings = [node for node in mappings if node['Dependents'] or node['Depth'] == 0]
    
    with open(json_path, 'w') as f:
        json.dump(mappings, f, indent=4)
    return json_path

def get_compile_runtime_dependencies(repo_name:str, module_relative_path:str, whether_update:bool) -> Optional[List[DepTreeNode]]:
    """get compile and runtime dependencies"""
    goblinupdater_dir_path = os.path.join(DATA_DIR, 'goblinUpdater', repo_name, module_relative_path)
    if not os.path.exists(goblinupdater_dir_path):
        os.makedirs(goblinupdater_dir_path)
    if whether_update:
        tree_path = os.path.join(goblinupdater_dir_path, 'current_verbose_tree.txt')
    else:
        tree_path = os.path.join(goblinupdater_dir_path, 'original_verbose_tree.txt')
    resulting_json_path = tree_to_json(tree_path, os.path.join("/home1/kaixuan/ray/goblin_dataset/", repo_name),\
        module_relative_path, whether_update)

    if resulting_json_path is None:
        # cann't generate dependency graph
        return None
    
    with open(resulting_json_path, 'r') as f:
        mappings = json.load(f)
    # get compile and runtime dependencies
    compile_runtime_deps = []
    for mapping in mappings:
        if mapping["Type"] in ["compile", "runtime"]:
           compile_runtime_deps.append(DepTreeNode(0, DependencyInfo(group_id=mapping["GroupId"], arch_id=mapping["ArtifactId"], \
               version=mapping["Original_Version"], scope=[]), []))
    return compile_runtime_deps 

def compute_tech_lag(dep_gav_list:list) -> int:
    """compute the tech lag"""
    tech_lag = 0
    for group_id, artifact_id, version in dep_gav_list:
        # print(group_id, artifact_id)
        last_version = get_latest_version(group_id, artifact_id)
        if last_version is None:
            # cann't get the latest version
            continue
        lag = get_version_distance(group_id, artifact_id, version, last_version)
        if lag is None:
            continue
        tech_lag += lag
    return tech_lag


if __name__ == "__main__":
    cfg_path = "/home1/kaixuan/ray/Baselines/goblinUpdater/gUpdaterConfig.yml"
    jar_path = "/home1/kaixuan/ray/Baselines/goblinUpdater/target/goblinUpdater-1.0.0-jar-with-dependencies.jar"
    modules = dataset()
    module_paths = []
    for module in modules:
        repo_name = module[0]
        module_relative_path = module[1]
        module_paths.append((\
            os.path.join("/home1/kaixuan/ray/goblin_dataset", repo_name, module_relative_path), \
                os.path.join("/home1/kaixuan/ray/goblin_dataset", repo_name),\
                    repo_name, module_relative_path\
            ))

    # test one 
    # module_paths=[
    #     ("/home1/kaixuan/ray/goblin_dataset/mall/mall-security", "/home1/kaixuan/ray/goblin_dataset/mall/", \
    #         "mall", "mall-security"),
    # ]
    
    module_data = pd.DataFrame(columns=["path", "group_id", "artifact_id", "version_old", "version_new", "original_tech_lag", "current_tech_lag"])
    compile_data = pd.DataFrame(columns=["path", "compile_success", "test_pass", "original_dep_count", "current_dep_count", "original_tech_lag", "current_tech_lag"])

    # for mod_path, mvn_path, mod_group_id, mod_artifact_id in module_paths:
    pbar = tqdm(total=len(module_paths), \
            desc=f"goblin experiment", position=0, leave=True)
    for mod_path, mvn_path, repo_name, module_relative_path in module_paths:
        try:
            solutions = GoblinUpdaterParser().exec(mod_path, cfg_path, jar_path).parse()
            # print("HELLO__________________")
            # solutions = GoblinUpdaterParser().parse()
            # mall-security报错
            # dep_tree_old = get_maven_dependencies(mod_path)
            # if dep_tree_old is None:
            #     continue
            # selected_node = dep_tree_old.select_node(mod_group_id, mod_artifact_id)
            # dep_filtered_old = selected_node.filter_scope()
            
            # dep_filtered_old是runtime和compile的依赖吗？而且是从tree中读取出来的？yes  -->这个我有笨办法来做
            # parse goblinUpdater的结果需不需要这个dep_filtered_old？筛选runtime和compile会用到 --》也就是说，只要我有办法得到上面这个old，就不影响goblinUpdater的parse?也可以直接不筛选，然后tree上的comp和runtime手动筛选
            
            # 直接采用Dependabot.py的写法，得到runtime、compile的依赖
            dep_filtered_old = get_compile_runtime_dependencies(repo_name, module_relative_path, False)

            # print(dep_filtered_old)

            if dep_filtered_old is None:
                # cann't generate dependency graph
                print(f"Error: cann't generate dependency graph for {mod_path} before updating")
                continue

            dep_ga_list = [(x.dep_info.group_id, x.dep_info.arch_id) for x in dep_filtered_old]
            # dep_gav_list = [(x.dep_info.group_id, x.dep_info.arch_id, x.dep_info.version) for x in dep_filtered_old]
            # print(dep_ga_list)
            # compute the original tech lag
            # total_original_tech_lag = compute_tech_lag(dep_gav_list)

            modifier = PomModifier(rf"{mod_path}/pom.xml")
            modifier.list_dependency()
            # print(len(solutions))
            # print(solutions)
            # solutions是从goblinUpdater中解析出来的结果
            # for solution in solutions:
            #     if len(solution.module) == 0:
            #         continue
            #     group_id, artifact_id = solution.module[0], solution.module[1]
            #     # 筛选非runtime和compile的结果
            #     # if (group_id, artifact_id) not in dep_ga_list:
            #     #     continue
            #     if solution.module == ["ROOT"]:
            #         continue
            #     result = modifier.modify(group_id, artifact_id, solution.new_version)
            #     # result is the old version and new version of the dependency
            #     if result is not None:
            #         # old version, new_version
            #         ov , nv = result[0], result[1]
            #         # latest_version
            #         lv = get_latest_version(group_id, artifact_id)
            #         if lv is not None:
            #             module_data = pd.concat([module_data, pd.DataFrame[{
            #                     "path": mod_path,
            #                     "group_id": solution.module[0],
            #                     "artifact_id": solution.module[1],
            #                     "version_old": ov,
            #                     "version_new": nv,
            #                     "original_tech_lag": get_version_distance(group_id, artifact_id, ov, lv),
            #                     "current_tech_lag": get_version_distance(group_id, artifact_id, nv, lv)
            #                 }]
            #             ])
            
            # print("solutions",solutions)
            for dep in dep_filtered_old:
                group_id, artifact_id = dep.dep_info.group_id, dep.dep_info.arch_id
                lv = get_latest_version(group_id, artifact_id)
                if lv is None:
                    continue
                
                ov = dep.dep_info.version
                nv = dep.dep_info.version
                
                print(f"group_id:{group_id}, artifact_id:{artifact_id}, latest_ver:{lv}, old_ver:{ov}")
                
                for solution in solutions:
                    if len(solution.module) == 0:
                        continue
                    _group_id, _artifact_id = solution.module[0], solution.module[1]
                    if group_id == _group_id and artifact_id == _artifact_id:
                        nv = solution.new_version
                        break
                
                module_data = pd.concat([module_data, pd.DataFrame([{
                        "path": mod_path,
                        "group_id": group_id,
                        "artifact_id": artifact_id,
                        "version_old": ov,
                        "version_new": nv,
                        "original_tech_lag": get_version_distance(group_id, artifact_id, ov, lv),
                        "current_tech_lag": get_version_distance(group_id, artifact_id, nv, lv)
                    }])
                ])
                if nv != ov:
                    modifier.modify(group_id, artifact_id, nv)
            modifier.save()

            # dep_tree_new = get_maven_dependencies(mod_path)
            # selected_node_new = dep_tree_new.select_node(mod_group_id, mod_artifact_id)
            # dep_filtered_new = selected_node_new.filter_scope()
            dep_filtered_new = get_compile_runtime_dependencies(repo_name, module_relative_path, True)
            
            # print(dep_filtered_new)
            
            if dep_filtered_old is None:
                # cann't generate dependency graph
                print(f"Error: cann't generate dependency graph for {mod_path} after updating")
                continue

            # compile_success = mvn_compile(mod_path)
            # test_success = mvn_test(mod_path)
            compile_success = mvn_compile(mvn_path, module_relative_path)
            test_success = mvn_test(mvn_path, module_relative_path)
            # # 最后的dep个数，只依赖于dep_filtered_new以及dep_filtered_old
            # compile_data.append({
            #     "path": mod_path,
            #     "compile_success:": compile_success,
            #     "test_pass": test_success,
            #     "original_dep": len(dep_filtered_old),
            #     "current_dep_count": len(dep_filtered_new),
            #     "original_tech_lag": 0,
            #     "current_tech_lag": 0,
            # })
            compile_data = pd.concat([compile_data, pd.DataFrame([{
                "path": mod_path,
                "compile_success": compile_success,
                "test_pass": test_success,
                "original_dep_count": len(dep_filtered_old),
                "current_dep_count": len(dep_filtered_new),
                "original_tech_lag": module_data[module_data["path"] == mod_path]["original_tech_lag"].sum(),
                "current_tech_lag": module_data[module_data["path"] == mod_path]["current_tech_lag"].sum(),
            }])])
            compile_data["reduced_tech_lag"] = compile_data["original_tech_lag"] - compile_data["current_tech_lag"]
            compile_data["reduced_dep_count"] = compile_data["original_dep_count"] - compile_data["current_dep_count"]
            csv_dir = os.path.join("data", "goblin_csvs")
            if not os.path.exists(csv_dir):
                os.makedirs(csv_dir)
            
            module_data.to_csv(os.path.join(csv_dir, "module_data.csv"), mode='w')
            compile_data.to_csv(os.path.join(csv_dir, "compile_data.csv"), mode='w')

            modifier.rollback()
            # 在mvn_path中执行git add . && git stash && git stash clear
            command = f"cd {mvn_path} && git add . && git stash && git stash clear"
            result = subprocess.run(command, shell=True, text=True, capture_output=True)
            if result.returncode != 0:
                print(f"Error: {result.stderr}")
            pbar.update(1)
        except Exception as e:
            print(f"Error: {e}")
            pbar.update(1)
    pbar.close()
    # df_module = pd.DataFrame(module_data)
    # df_compile = pd.DataFrame(compile_data)
    # df_module = module_data
    # df_compile = compile_data

    # # for mod_path in module_paths:
    # #     compile_mask = df_compile["path"] == mod_path
    # #     module_mask = df_module["path"] == mod_path
    # #     df_compile.loc[compile_mask, "original_tech_lag"] = df_module[module_mask]["original_tech_lag"].sum()
    # #     df_compile.loc[compile_mask, "current_tech_lag"] = df_module[module_mask]["current_tech_lag"].sum()

    # pd.set_option('display.width',None)
    # df_compile["reduced_tech_lag"] =  df_compile["original_tech_lag"] - df_compile["current_tech_lag"]
    # df_compile["reduced_dep_count"] =  df_compile["original_dep"] - df_compile["current_dep_count"]

    # print("_"*30)
    # print(df_compile)
    # print("_"*30)
    # print(df_module)
    # print("_"*30)

    # timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    # csv_dir = "goblin_csvs"
    # if not os.path.exists(csv_dir):
    #     os.makedirs(csv_dir)
    # df_module.to_csv(f"./goblin_csvs/module_data_{timestamp}.csv")
    # df_compile.to_csv(f"./goblin_csvs/compile_data_{timestamp}.csv")