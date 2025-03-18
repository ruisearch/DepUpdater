"""compute time-based lag for Dependabot and snyk in RQ1~2"""
import os
import pandas as pd
from tqdm import tqdm
import json
from constants import DATA_DIR
from database.query import query_versions_from_mongo 

def get_time_lag_of_a_dep(gid:str, aid:str, version:str)->int:
    """get the time lag of a dependency version"""
    try:
        all_versions = query_versions_from_mongo(gid, aid)
        all_versions.sort(key=lambda x: x['date'], reverse=True)
        latest_time = all_versions[0]['date']
        # print(f"latest_time: {latest_time}")
        # print(f"last version: {all_versions[0]['version']}")
        current_time = None
        for v in all_versions:
            if v['version'] == version:
                current_time = v['date']
                break
        if current_time is None:
            # the version is not in the database
            return 0
        lag = (int(latest_time) - int(current_time)) // 86400000 # days
        return lag
    except Exception as e:
        print(f"Fail to handle {gid}:{aid}, reason:{e}")
        return 0
    
    
# print(get_time_lag_of_a_dep("software.amazon.awssdk", "regions", "2.7.0"))
def dataset():
    modules = [
        # 227 modules
        ('mall','mall-common'),
        ('mall','mall-security'),
        ('dubbo','dubbo-test/dubbo-test-common'),
        ('dubbo','dubbo-test/dubbo-test-modules'),
        ('dubbo','dubbo-serialization/dubbo-serialization-hessian2'),
        ('dubbo','dubbo-spring-boot/dubbo-spring-boot-3-autoconfigure'),
        ('dubbo','dubbo-metrics/dubbo-metrics-event'),
        ('dubbo','dubbo-metrics/dubbo-metrics-config-center'),
        ('dubbo','dubbo-metrics/dubbo-metrics-netty'),
        ('dubbo','dubbo-plugin/dubbo-auth'),
        ('dubbo','dubbo-plugin/dubbo-compiler'),
        ('dubbo','dubbo-plugin/dubbo-filter-cache'),
        ('dubbo','dubbo-remoting/dubbo-remoting-api'),
        ('dubbo','dubbo-cluster'),
        ('dubbo','dubbo-rpc/dubbo-rpc-api'),
        ('dubbo','dubbo-rpc/dubbo-rpc-injvm'),
        ('dubbo','dubbo-demo/dubbo-demo-spring-boot/dubbo-demo-spring-boot-interface'),
        ('netty','testsuite-autobahn'),
        ('netty','testsuite-http2'),
        ('netty','codec-dns'),
        ('netty','codec-haproxy'),
        ('netty','codec-memcache'),
        ('netty','codec-mqtt'),
        ('netty','codec-redis'),
        ('netty','codec-smtp'),
        ('netty','codec-stomp'),
        ('netty','codec-socks'),
        ('netty','codec-xml'),
        ('netty','transport-rxtx'),
        ('netty','transport-udt'),
        ('netty','example'),
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
        ('java-design-patterns', 'servant'),
        ('java-design-patterns', 'visitor'),
        ('java-design-patterns', 'null-object'),
        ('java-design-patterns', 'fluent-interface'),
        ('java-design-patterns', 'event-sourcing'),
        ('java-design-patterns', 'reactor'),
        ('java-design-patterns', 'fanout-fanin'),
        ('java-design-patterns', 'client-session'),
        ('java-design-patterns', 'half-sync-half-async'),
        ('java-design-patterns', 'marker-interface'),
        ('java-design-patterns', 'function-composition'),
        ('java-design-patterns', 'promise'),
        ('java-design-patterns', 'saga'),
        ('java-design-patterns', 'microservices-log-aggregation'),
        ('java-design-patterns', 'transaction-script'),
        ('java-design-patterns', 'poison-pill'),
        ('java-design-patterns', 'data-transfer-object'),
        ('java-design-patterns', 'data-mapper'),
        ('java-design-patterns', 'builder'),
        ('java-design-patterns', 'health-check'),
        ('java-design-patterns', 'specification'),
        ('java-design-patterns', 'strangler'),
        ('java-design-patterns', 'queue-based-load-leveling'),
        ('java-design-patterns', 'converter'),
        ('java-design-patterns', 'collecting-parameter'),
        ('java-design-patterns', 'proxy'),
        ('java-design-patterns', 'serialized-entity'),
        ('java-design-patterns', 'business-delegate'),
        ('java-design-patterns', 'combinator'),
        ('java-design-patterns', 'layered-architecture'),
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
        ('java-design-patterns', 'event-aggregator'),
        ('java-design-patterns', 'leader-followers'),
        ('java-design-patterns', 'partial-response'),
        ('java-design-patterns', 'update-method'),
        ('java-design-patterns', 'private-class-data'),
        ('java-design-patterns', 'prototype'),
        ('java-design-patterns', 'serialized-lob'),
        ('java-design-patterns', 'retry'),
        ('java-design-patterns', 'mute-idiom'),
        ('java-design-patterns', 'role-object'),
        ('java-design-patterns', 'event-based-asynchronous'),
        ('java-design-patterns', 'curiously-recurring-template-pattern'),
        ('java-design-patterns', 'adapter'),
        ('java-design-patterns', 'pipeline'),
        ('java-design-patterns', 'circuit-breaker'),
        ('java-design-patterns', 'factory-kit'),
        ('java-design-patterns', 'monitor'),
        ('java-design-patterns', 'double-dispatch'),
        ('java-design-patterns', 'single-table-inheritance'),
        ('java-design-patterns', 'unit-of-work'),
        ('java-design-patterns', 'event-queue'),
        ('java-design-patterns', 'factory'),
        ('java-design-patterns', 'execute-around'),
        ('java-design-patterns', 'command'),
        ('java-design-patterns', 'spatial-partition'),
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
        ('nacos', 'plugin/environment'),
        ('nacos', 'plugin/trace'),
        ('nacos', 'plugin/datasource'),
        ('nacos', 'plugin/encryption'),
        ('nacos', 'plugin/config'),
        ('nacos', 'plugin/control'),
        ('nacos', 'plugin/auth'),
        ('nacos', 'common'),
        ('nacos', 'client'),
        ('nacos', 'logger-adapter-impl/log4j2-adapter'),
        ('nacos', 'logger-adapter-impl/logback-adapter-12'),
        ('nacos', 'consistency'),
        ('nacos', 'plugin-default-impl/nacos-default-control-plugin'),
        ('WxJava', 'weixin-java-cp'),
        ('WxJava', 'weixin-graal'),
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
    ]
    return modules

def get_deps_from_json(json_path:str)->list:
    """get dependencies from json"""
    with open(json_path, 'r') as f:
        deps = json.load(f)
    ret_deps = []
    for dep in deps:
        if dep['Dependents']:
            # consider the deps that are in graph actually
            # note: the deps that are in graph but has no best version all have classifier
            ret_deps.append(dep)
    return ret_deps

def compute_time_lag(dep:dict)->int:
    try:
        gid = dep["GroupId"]
        aid = dep["ArtifactId"]
        version = dep["Original_Version"]
        best_lag = get_time_lag_of_a_dep(gid, aid, version)
        return best_lag
    except Exception as e:
        print(f"Fail to handle {gid}:{aid}, reason:{e}")
        return 0

def main():
    modules = dataset()
    # data_dir = os.path.join(DATA_DIR, 'Lagease_result')
    # data_dir = os.path.join(DATA_DIR, 'debloating_only_result')
    # data_dir = os.path.join(DATA_DIR, 'com_only_result')
    # data_dir = os.path.join(DATA_DIR, 'snyk')
    data_dir = os.path.join(DATA_DIR, 'dependabot')

    # csv_path = os.path.join(DATA_DIR, 'lagease_time_lag.csv')
    # csv_path = os.path.join(DATA_DIR, 'debloating_only_time_lag.csv')
    # csv_path = os.path.join(DATA_DIR, 'com_only_time_lag.csv')
    # csv_path = os.path.join(DATA_DIR, 'snyk_time_lag.csv')
    csv_path = os.path.join(DATA_DIR, 'dependabot_time_lag.csv')
    dataset_df = pd.DataFrame(columns=['repo_name', 'module_name', 'best_lag'])
    dataset_df.to_csv(csv_path, index=False)

    with tqdm(total=len(modules)) as pbar:
        for module in modules:
            best_lag = 0
            repo_name, module_name = module
            print(f"Processing {repo_name}/{module_name}")
            json_path = os.path.join(data_dir, repo_name, module_name, 'current_version.json')
            if os.path.exists(json_path) == False:
                pbar.update(1)
                continue
            deps = get_deps_from_json(json_path)
            for dep in deps:
                b = compute_time_lag(dep)
                best_lag += b
            
            new_row = pd.DataFrame([[repo_name, module_name, best_lag]], \
                columns=['repo_name', 'module_name', 'best_lag'])
            numeric_columns = ['best_lag']
            for col in numeric_columns:
                new_row[col] = pd.to_numeric(new_row[col], errors='coerce')
            new_row.to_csv(csv_path, mode='a', header=False, index=False)
            pbar.update(1)

main()