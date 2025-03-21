# DepUpdater

`DepUpdater` is a dependency management tool that upgrades the outdated dependencies of Maven projects while preventing introducing compatibility issues or bloated dependencies.  To achieve this, `DepUpdater` first constructs a dependency graph that reflects the actual dependency relationships, derived from the dependency tree provided by Maven. It then traverses this dependency graph, and for each node encountered, filters out versions that violate the compatibility or debloating constraints. From the remaining versions, the latest one is selected to minimize the technical lag of the module. After processing each node, `DepUpdater` also updates the dependency graph in real time to keep the contextual information accurate and up to date.
![image](https://github.com/ruisearch/com_tool/blob/artifact/img/overview.png)

## Usage

### Requirements

**1.** JDK 17

**2.** Maven 3.9.5

**3.** python 3.10.12

**4.** Ubuntu 2020

**5.** Necessary python packages :

* Install a virtual environment

```shell
python -m venv .venv
```

* Active the virtual environment

```bash
source .venv/bin/activate
```

* Install the required packages

```shell
pip install -r requirements.txt
```

**6.** A MongoDB docker container :

* Download `maven_deps.zip`  from https://anonymfile.com/kWjEg/maven-deps.zip, then unzip it to get `maven_deps.bson`.
* Download `maven.zip` from https://anonymfile.com/r1ke0/maven.zip , then unzip it to get `maven.bson`.
* Place `maven_deps.bson` and `maven.bson` at the root directory of this repository.
* Activate a MongoDB docker container named `maven_mongodb`.

```shell
docker-compose -f docker-compose.yml up -d
```

* Restore two collections of the MongoDB :

restore the `maven` collection

```shell
docker exec maven_mongodb mongorestore --db maven --collection maven /data/maven.bson
```

retore the `maven_deps` collection

```shell
docker exec maven_mongodb mongorestore --db maven --collection maven_deps /data/maven_deps.bson
```

* Create indexes on the two collections 

Add two compound indexes to the `maven` collection: (`group`, `artifact`) and (`group`, `artifact`, `version`).

Add one compound index to the `maven_deps` collection: `parent`.

**7.** A `Sqlite`  database :

* Download `reusable_data.zip` from https://anonymfile.com/mkyRb/reusable-data.zip, then unzip it to get `reusable_data.sqlite`.
* Place `reusable_data.sqlite` at the root directory of this repository.



### Run `DepUpdater`

Execute the MainProcess.py:

```
python MainProcess.py -h
usage: MainProcess.py [-h] [-r ROOT] [-m MODULE] [-j JAR] [-l LOCAL_DEP_JAR [LOCAL_DEP_JAR ...]]

options:
  -h, --help            show this help message and exit
  -r ROOT, --root ROOT  the path to the cloned folder
  -m MODULE, --module MODULE
                        the relative path to the module
  -j JAR, --jar JAR     the relative path to the client jar
  -l LOCAL_DEP_JAR [LOCAL_DEP_JAR ...], --local_dep_jar LOCAL_DEP_JAR [LOCAL_DEP_JAR ...]
                        the relative paths to the local module jar depended by client
```

the `ROOT` and `MODULE` parameters are necessary, while `JAR` and `LOCAL_DEP_JAR` parameters are optional.

An example usage:

```shell
python MainProcess.py -r /home/test/mall -m mall-common
```

the `mall` repository is cloned from https://github.com/macrozheng/mall.git, and mall-common is a module of this repository.
`/home/test/mall` is the local location of the cloned repository, and `mall-common` is the relative path of the mall-common module.

## Source code structure

The structure of this repository is as follows:

```
.
├── computation # upgrade a dependency
├── constants.py # constants
├── database # query and update the Mongodb and sqlite
├── docker-compose-mongodb.yml # docker file
├── evaluation # compute reduced tech lag and dep count
├── logger # generate log
├── MainProcess.py # main function
├── maven.bson # maven collection
├── maven_deps.bson # maven_deps collection
├── preprocess # restore the dependency graph
├── README.md
├── requirements.txt # necessary pagckages
├── reusable_data.sqlite # splite file
├── RQs_data # data of RQs
├── traverse # traverse the dependency graph
└── update # update the database as well as the graph
```

## Data for RQs

Data for RQs is in the `RQs_data` folder, the structure of this folder is as follows:

```
.
├── RQ1
│   ├── RQ1_Dependabot.csv # Dependabot in RQ1
│   ├── RQ1_DepUpdater.csv # DepUpdater in RQ1
│   └── RQ1_Snyk.csv # Snyk in RQ1
├── RQ2
│   ├── RQ2_Compatibility_Only.csv # Compatibility only in RQ1
│   ├── RQ2_Debloating_Only.csv # Debloating only in RQ1
│   └── RQ2_Naive.csv # Naive in RQ1
└── RQ3
    ├── RQ3_API_Distribution.csv # Distribution of client-impacting API
    └── RQ3_Client_Distribution.csv # Distribution of Broken-Client
```

