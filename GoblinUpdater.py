'''
    execute GoblinUpdater for RQ1
    GoblinWeaver should be executed firstly
'''
import os
import subprocess
from constants import MainProcess_pwd

def main():
    '''execute GoblinUpdater to count dep and tech lag'''
    modules = dataset()
    for root, module in modules:
        execute(root, module)

def dataset():
    '''set modules in the dataset'''
    modules = [
        # dataset in SRC
        ('mall','mall-common'),
        ('mall','mall-security'),
        ('guava','guava-testlib'),
        ('dubbo','dubbo-test/dubbo-test-common'),
        ('dubbo','dubbo-test/dubbo-test-modules'),
        ('dubbo','dubbo-serialization/dubbo-serialization-fastjson2'),
        ('dubbo','dubbo-serialization/dubbo-serialization-hessian2'),
        ('dubbo','dubbo-spring-boot/dubbo-spring-boot-3-autoconfigure'),
        ('dubbo','dubbo-metrics/dubbo-metrics-api'),
        ('dubbo','dubbo-metrics/dubbo-metrics-event'),
        ('dubbo','dubbo-metrics/dubbo-metrics-config-center'),
        ('dubbo','dubbo-metrics/dubbo-metrics-default'),
        ('dubbo','dubbo-metrics/dubbo-metrics-netty'),
        ('dubbo','dubbo-metrics/dubbo-tracing'),
        ('dubbo','dubbo-plugin/dubbo-auth'),
        ('dubbo','dubbo-plugin/dubbo-filter-validation'),
        ('dubbo','dubbo-plugin/dubbo-spring-security'),
        ('dubbo','dubbo-plugin/dubbo-compiler'),
        ('dubbo','dubbo-plugin/dubbo-filter-cache'),
        ('dubbo','dubbo-remoting/dubbo-remoting-api'),
        ('dubbo','dubbo-remoting/dubbo-remoting-zookeeper-curator5'),
        ('dubbo','dubbo-cluster'),
        ('dubbo','dubbo-rpc/dubbo-rpc-api'),
        ('dubbo','dubbo-rpc/dubbo-rpc-injvm'),
        ('dubbo','dubbo-demo/dubbo-demo-interface'),
        ('dubbo','dubbo-demo/dubbo-demo-spring-boot/dubbo-demo-spring-boot-interface'),
        ('netty','buffer'),
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
        ('java-design-patterns', 'metadata-mapping'),
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
        # extended dataset
        # ......
    ]
    return modules

def execute(root:str, module:str):
    '''
        execute GoblinUpdater
    '''
    ret_dir = os.path.join(MainProcess_pwd, 'data', 'result', 'goblinUpdater')
    if not os.path.exists(ret_dir):
        os.makedirs(ret_dir)

    user_path = os.path.expanduser('~')
    path_to_module = os.path.join(user_path, 'ray', 'SRC_dataset', root, module)
    path_to_ret_file = os.path.join(ret_dir, f'{root}_{module}.txt')
    config_file_path = os.path.join(MainProcess_pwd, 'utils', 'gUpdaterConfig.yml')
    jar_file_path = os.path.join(MainProcess_pwd, 'utils', 'goblinUpdater-1.0.0-jar-with-dependencies.jar')
    try:
        # execute GoblinUpdater
        subprocess.run(['java', '-DweaverUrl="http://localhost:8080"', f'-DprojectPath="{path_to_module}"',\
            f'-DconfFile="{config_file_path}"',\
            '-jar', f'{jar_file_path}', '>', path_to_ret_file
        ], text=True, timeout=4800)
    except subprocess.TimeoutExpired:
        print(f'GoblinUpdater for {path_to_module} is timeout')
        with open(path_to_ret_file, 'a') as f:
            f.write('~~timeout~~, so considered as unsolved')

if __name__ == '__main__':
    main()