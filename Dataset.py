import subprocess
import os
import logging
import re
import csv
from tqdm import tqdm
from constants import DATA_DIR, RET_DIR


def main():
    """main function"""
    log_path = os.path.join(DATA_DIR, 'DATASET.log')
    # clear log
    if os.path.exists(log_path):
        os.remove(log_path)
    # clear csv
    csv_path = os.path.join(DATA_DIR, 'dataset.csv')
    if os.path.exists(csv_path):
        os.remove(csv_path)
    # add head
    with open(csv_path,'a') as f:
        writer = csv.writer(f)
        writer.writerow(['repo','module','compile success','test pass','original tech lag','current tech lag','reduced tech lag'])
    # set log
    logging.basicConfig(filename=log_path,level=logging.INFO,format='%(asctime)s - %(message)s')
    # set module
    modules = dataset()
    with tqdm(total=len(modules)) as pbar:
        for module in modules:
            print(module)
            result = execute_tool(module)
            repo_name = os.path.basename(module[0])
            if result.returncode != 0:
                logging.info(f"{repo_name} : {module[1]} crashes")
                store_ret_in_csv(repo_name, module[1], result.stdout)
                pbar.update(1)
                continue
            logging.info(f"{repo_name} : {module[1]} done")
            repo_name = os.path.basename(module[0])
            store_ret_in_csv(repo_name, module[1], result.stdout)
            pbar.update(1)

def dataset():
    """set modules in the dataset"""
    modules = [
        # ('~/Tool/SRC_dataset/mall','mall-common'),
        # ('~/Tool/SRC_dataset/mall','mall-admin'),
        # ('~/Tool/SRC_dataset/mall','mall-security'),
        # ('~/Tool/SRC_dataset/mall','mall-demo'),
        # ('~/Tool/SRC_dataset/guava','guava'),
        # ('~/Tool/SRC_dataset/guava','android/guava'),
        # ('~/Tool/SRC_dataset/guava','android/guava-testlib'),
        # ('~/Tool/SRC_dataset/guava','guava-testlib'),
        # ('~/Tool/SRC_dataset/dubbo','dubbo-test/dubbo-test-common'),
        # ('~/Tool/SRC_dataset/dubbo','dubbo-test/dubbo-test-spring'),
        # ('~/Tool/SRC_dataset/dubbo','dubbo-test/dubbo-test-spring'),
        # ('~/Tool/SRC_dataset/dubbo','dubbo-test/dubbo-test-check'),
        # ('~/Tool/SRC_dataset/dubbo','dubbo-test/dubbo-test-modules'),
        # ('~/Tool/SRC_dataset/dubbo','dubbo-distribution/dubbo-apache-release'),
        # ('~/Tool/SRC_dataset/dubbo','dubbo-demo/dubbo-demo-annotation/dubbo-demo-annotation-consumer'),
        # ('~/Tool/SRC_dataset/dubbo','dubbo-demo/dubbo-demo-annotation/dubbo-demo-annotation-provider'),
        # ('~/Tool/SRC_dataset/dubbo','dubbo-demo/dubbo-demo-interface'),
        # ('~/Tool/SRC_dataset/dubbo','dubbo-demo-xml/dubbo-demo-spring-mvc-rest-consumer'),
        # ('~/Tool/SRC_dataset/dubbo','dubbo-demo/dubbo-demo-api/dubbo-demo-api-consumer'),
        # ('~/Tool/SRC_dataset/dubbo','dubbo-demo/dubbo-demo-native/dubbo-demo-native-consumer'),
        # ('~/Tool/SRC_dataset/dubbo','dubbo-demo/dubbo-demo-native/dubbo-demo-native-provider'),
        # ('~/Tool/SRC_dataset/dubbo','dubbo-demo/dubbo-demo-spring-boot/dubbo-demo-spring-boot-consumer'),
        # ('~/Tool/SRC_dataset/dubbo','dubbo-demo/dubbo-demo-spring-boot/dubbo-demo-spring-boot-interface'),
        
        ('mall','mall-common'),
        ('mall','mall-admin'),
        ('mall','mall-security'),
        ('mall','mall-demo'),
        ('mall','mall-portal'),
        ('mall','mall-search'),
        ('mall','mall-mbq'),
        ('guava','guava'),
        ('guava','android/guava'),
        ('guava','android/guava-testlib'),
        ('guava','guava-testlib'),
        ('dubbo','dubbo-test/dubbo-test-common'),
        ('dubbo','dubbo-test/dubbo-test-spring'),
        ('dubbo','dubbo-test/dubbo-test-check'),
        ('dubbo','dubbo-test/dubbo-test-modules'),
        ('dubbo','dubbo-serialization/dubbo-serialization-api'),
        ('dubbo','dubbo-serialization/dubbo-serialization-fastjson2'),
        ('dubbo','dubbo-serialization/dubbo-serialization-hessian2'),
        ('dubbo','dubbo-compatible'),
        ('dubbo','dubbo-maven-plugin'),
        ('dubbo','dubbo-spring-boot/dubbo-spring-boot-3-autoconfigure'),
        ('dubbo','dubbo-spring-boot/dubbo-spring-boot-actuator'),
        ('dubbo','dubbo-spring-boot/dubbo-spring-boot-interceptor'),
        ('dubbo','dubbo-spring-boot/dubbo-spring-boot-autoconfigure'),
        ('dubbo','dubbo-config/dubbo-config-api'),
        ('dubbo','dubbo-config/dubbo-config-spring'),
        ('dubbo','dubbo-config/dubbo-config-spring6'),
        ('dubbo','dubbo-metadata/dubbo-metadata-api'),
        ('dubbo','dubbo-metadata/dubbo-metadata-processor'),
        ('dubbo','dubbo-metadata/dubbo-metadata-report-zookeeper'),
        ('dubbo','dubbo-metadata/dubbo-metadata-definition-protobuf'),
        ('dubbo','dubbo-metadata/dubbo-metadata-report-nacos'),
        ('dubbo','dubbo-configcenter/dubbo-configcenter-apollo'),
        ('dubbo','dubbo-configcenter/dubbo-configcenter-nacos'),
        ('dubbo','dubbo-configcenter/dubbo-configcenter-file'),
        ('dubbo','dubbo-configcenter/dubbo-configcenter-zookeeper'),
        ('dubbo','dubbo-metrics/dubbo-metrics-api'),
        ('dubbo','dubbo-metrics/dubbo-metrics-event'),
        ('dubbo','dubbo-metrics/dubbo-metrics-prometheus'),
        ('dubbo','dubbo-metrics/dubbo-metrics-config-center'),
        ('dubbo','dubbo-metrics/dubbo-metrics-metadata'),
        ('dubbo','dubbo-metrics/dubbo-metrics-registry'),
        ('dubbo','dubbo-metrics/dubbo-metrics-default'),
        ('dubbo','dubbo-metrics/dubbo-metrics-netty'),
        ('dubbo','dubbo-metrics/dubbo-tracing'),
        ('dubbo','dubbo-plugin/dubbo-auth'),
        ('dubbo','dubbo-plugin/dubbo-filter-validation'),
        ('dubbo','dubbo-plugin/dubbo-qos'),
        ('dubbo','dubbo-plugin/dubbo-rest-jaxrs'),
        ('dubbo','dubbo-plugin/dubbo-spring-security'),
        ('dubbo','dubbo-plugin/dubbo-compiler'),
        ('dubbo','dubbo-plugin/dubbo-native'),
        ('dubbo','dubbo-plugin/dubbo-qos-api'),
        ('dubbo','dubbo-plugin/dubbo-rest-spring'),
        ('dubbo','dubbo-plugin/dubbo-filter-cache'),
        ('dubbo','dubbo-plugin/dubbo-plugin-loom'),
        ('dubbo','dubbo-plugin/dubbo-reactive'),
        ('dubbo','dubbo-plugin/dubbo-security'),
        ('dubbo','dubbo-registry/dubbo-registry-api'),
        ('dubbo','dubbo-registry/dubbo-registry-multiple'),
        ('dubbo','dubbo-registry/dubbo-registry-zookeeper'),
        ('dubbo','dubbo-registry/dubbo-registry-multicast'),
        ('dubbo','dubbo-registry/dubbo-registry-nacos'),
        ('dubbo','dubbo-remoting/dubbo-remoting-api'),
        ('dubbo','dubbo-remoting/dubbo-remoting-http3'),
        ('dubbo','dubbo-remoting/dubbo-remoting-netty4'),
        ('dubbo','dubbo-remoting/dubbo-remoting-http12'),
        ('dubbo','dubbo-remoting/dubbo-remoting-netty'),
        ('dubbo','dubbo-remoting/dubbo-remoting-zookeeper-curator5'),
        ('dubbo','dubbo-cluster'),
        ('dubbo','dubbo-rpc/dubbo-rpc-api'),
        ('dubbo','dubbo-rpc/dubbo-rpc-dubbo'),
        ('dubbo','dubbo-rpc/dubbo-rpc-injvm'),
        ('dubbo','dubbo-rpc/dubbo-rpc-triple'),
        ('dubbo','dubbo-distribution/dubbo-apache-release'),
        ('dubbo','dubbo-demo/dubbo-demo-annotation/dubbo-demo-annotation-consumer'),
        ('dubbo','dubbo-demo/dubbo-demo-annotation/dubbo-demo-annotation-provider'),
        ('dubbo','dubbo-demo/dubbo-demo-interface'),
        ('dubbo','dubbo-demo/dubbo-demo-xml/dubbo-demo-spring-mvc-rest-consumer'),
        ('dubbo','dubbo-demo/dubbo-demo-api/dubbo-demo-api-consumer'),
        ('dubbo','dubbo-demo/dubbo-demo-native/dubbo-demo-native-consumer'),
        ('dubbo','dubbo-demo/dubbo-demo-native/dubbo-demo-native-provider'),
        ('dubbo','dubbo-demo/dubbo-demo-spring-boot/dubbo-demo-spring-boot-consumer'),
        ('dubbo','dubbo-demo/dubbo-demo-spring-boot/dubbo-demo-spring-boot-interface'),
        ('netty','buffer'),
        ('netty','handler'),
        ('netty','testsuite'),
        ('netty','handler-proxy'),
        ('netty','testsuite-autobahn'),
        ('netty','handler-ssl-ocsp'),
        ('netty','testsuite-http2'),
        ('netty','codec'),
        ('netty','codec-dns'),
        ('netty','codec-haproxy'),
        ('netty','codec-memcache'),
        ('netty','codec-mqtt'),
        ('netty','codec-redis'),
        ('netty','codec-smtp'),
        ('netty','codec-stomp'),
        ('netty','codec-socks'),
        ('netty','codec-xml'),
        ('netty','common'),
        ('netty','transport'),
        ('netty','transport-rxtx'),
        ('netty','transport-sctp'),
        ('netty','transport-udt'),
        ('netty','example'),
        ('netty','dev-tools'),
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
        # ('java-design-patterns', 'command-query-responsibility-segregation'),
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
        # ('java-design-patterns', 'microservices-aggregrator'),
        # ('java-design-patterns', 'servant'),
        # ('java-design-patterns', 'visitor'),
        # ('java-design-patterns', 'null-object'),
        # ('java-design-patterns', 'page-object'),
        # ('java-design-patterns', 'fluent-interface'),
        # ('java-design-patterns', 'event-sourcing'),
        # ('java-design-patterns', 'reactor'),
        # ('java-design-patterns', 'fanout-fanin'),
        # ('java-design-patterns', 'client-session'),
        # ('java-design-patterns', 'half-sync-half-async'),
        # ('java-design-patterns', 'marker-interface'),
        # ('java-design-patterns', 'function-composition'),
        # ('java-design-patterns', 'promise'),
        # ('java-design-patterns', 'naked-objects'),
        # ('java-design-patterns', 'saga'),
        # ('java-design-patterns', 'localization'),
        # ('java-design-patterns', 'microservices-log-aggregation'),
        # ('java-design-patterns', 'transaction-script'),
        # ('java-design-patterns', 'poison-pill'),
        # ('java-design-patterns', 'service-layer'),
        # ('java-design-patterns', 'data-transfer-object'),
        # ('java-design-patterns', 'data-mapper'),
        # ('java-design-patterns', 'builder'),
        # ('java-design-patterns', 'health-check'),
        # ('java-design-patterns', 'specification'),
        # ('java-design-patterns', 'strangler'),
        # ('java-design-patterns', 'queue-based-load-leveling'),
        # ('java-design-patterns', 'converter'),
        # ('java-design-patterns', 'collecting-parameter'),
        # ('java-design-patterns', 'model-view-presenter'),
        # ('java-design-patterns', 'proxy'),
        # ('java-design-patterns', 'serialized-entity'),
        # ('java-design-patterns', 'business-delegate'),
        # ('java-design-patterns', 'combinator'),
        # ('java-design-patterns', 'etc'),
        # ('java-design-patterns', 'layered-architecture'),
        # ('java-design-patterns', 'intercepting-filter'),
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
        # ('java-design-patterns', 'hexagonal-architecture'),
        # ('java-design-patterns', 'front-controller'),
        # ('java-design-patterns', 'model-view-intent'),
        # ('java-design-patterns', 'type-object'),
        # ('java-design-patterns', 'decorator'),
        # ('java-design-patterns', 'service-locator'),
        # ('java-design-patterns', 'composite'),
        # ('java-design-patterns', 'strategy'),
        # ('java-design-patterns', 'flyweight'),
        # ('java-design-patterns', 'server-session'),
        # ('java-design-patterns', 'subclass-sandbox'),
        # ('java-design-patterns', 'dirty-flag'),
        # ('java-design-patterns', 'twin'),
        # ('java-design-patterns', 'active-object'),
        # ('java-design-patterns', 'double-buffer'),
        # ('java-design-patterns', 'game-loop'),
        # ('java-design-patterns', 'context-object'),
        # ('java-design-patterns', 'template-method'),
        # ('java-design-patterns', 'separated-interface'),
        # ('java-design-patterns', 'commander'),
        # ('java-design-patterns', 'step-builder'),
        # ('java-design-patterns', 'state'),
        # ('java-design-patterns', 'tolerant-reader'),
        # ('java-design-patterns', 'guarded-suspension'),
        # ('java-design-patterns', 'sharding'),
        # ('java-design-patterns', 'property'),
        # ('java-design-patterns', 'balking'),
        # ('java-design-patterns', 'currying'),
        # ('java-design-patterns', 'microservices-distributed-tracing'),
        # ('java-design-patterns', 'event-aggregator'),
        # ('java-design-patterns', 'leader-followers'),
        # ('java-design-patterns', 'partial-response'),
        # ('java-design-patterns', 'update-method'),
        # ('java-design-patterns', 'private-class-data'),
        # ('java-design-patterns', 'metadata-mapping'),
        # ('java-design-patterns', 'prototype'),
        # ('java-design-patterns', 'serialized-lob'),
        # ('java-design-patterns', 'retry'),
        # ('java-design-patterns', 'mute-idiom'),
        # ('java-design-patterns', 'role-object'),
        # ('java-design-patterns', 'model-view-viewmodel'),
        # ('java-design-patterns', 'event-based-asynchronous'),
        # ('java-design-patterns', 'curiously-recurring-template-pattern'),
        # ('java-design-patterns', 'adapter'),
        # ('java-design-patterns', 'pipeline'),
        # ('java-design-patterns', 'presentation-model'),
        # ('java-design-patterns', 'circuit-breaker'),
        # ('java-design-patterns', 'factory-kit'),
        # ('java-design-patterns', 'monitor'),
        # ('java-design-patterns', 'double-dispatch'),
        # ('java-design-patterns', 'single-table-inheritance'),
        # ('java-design-patterns', 'unit-of-work'),
        # ('java-design-patterns', 'event-queue'),
        # ('java-design-patterns', 'factory'),
        # ('java-design-patterns', 'dependency-injection'),
        # ('java-design-patterns', 'execute-around'),
        # ('java-design-patterns', 'command'),
        # ('java-design-patterns', 'spatial-partition'),
        # ('java-design-patterns', 'microservices-api-gateway'),
        # ('java-design-patterns', 'feature-toggle'),
        # ('java-design-patterns', 'composite-view'),
        # ('java-design-patterns', 'parameter-object'),
        # ('java-design-patterns', 'arrange-act-assert'),
        # ('java-design-patterns', 'iterator'),
        # ('java-design-patterns', 'lazy-loading')
    ]
    return modules

def execute_tool(module: tuple):
    """method to execute the tool on one module"""
    dataset_root = "/home/ray/SRC_dataset"
    root_dir = os.path.join(dataset_root, module[0])
    # repo_name = os.path.basename(module[0])
    # logging.info(f"{repo_name} : {module[1]} start")
    logging.info(f"{module[0]} : {module[1]} start")
    if len(module) == 2:
        # command = f"python3 ./MainProcess.py -r {module[0]} -m {module[1]}"
        command = f"python3 ./MainProcess.py -r {root_dir} -m {module[1]}"
    elif len(module) == 3:
        # command = f"python3 ./MainProcess.py -r {module[0]} -m {module[1]} -j {module[2]}"
        command = f"python3 ./MainProcess.py -r {root_dir} -m {module[1]} -j {module[2]}"
    result = subprocess.run(command,shell=True,text=True,\
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    # store_log(repo_name, module[1], result.stdout)
    store_log(module[0], module[1], result.stdout)
    return result

def store_log(repo_name: str, relative_path_to_module: str, log:str):
    """store the log"""
    log_folder = os.path.join(RET_DIR,repo_name,relative_path_to_module)
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)
    log_path = os.path.join(log_folder,'stdout.txt')
    with open(log_path,'w',encoding='utf-8') as f:
        f.write(log)

def store_ret_in_csv(repo_name: str, relative_path_to_module: str, ret:str):
    """store the ret in csv"""
    csv_path = os.path.join(DATA_DIR, 'dataset.csv')
    compile_flag = parse_ret(ret,'compile success:')
    test_flag = parse_ret(ret,'test pass:')
    original_tech_lag = parse_ret(ret,'original technical lag:')
    current_tech_lag = parse_ret(ret,'current technical lag:')
    reduced_tech_lag = parse_ret(ret,'reduced technical lag:')
    with open(csv_path,'a') as f:
        writer = csv.writer(f)
        writer.writerow([repo_name, relative_path_to_module, compile_flag, test_flag, original_tech_lag, current_tech_lag, reduced_tech_lag])

def parse_ret(ret:str, prefix:str):
    """get ret starts with prefix"""
    pattern = rf'{prefix} (.*)'
    match = re.search(pattern,ret)
    if match:
        return match.group(1)
    else:
        return '?'

if __name__ == "__main__":
    main()
