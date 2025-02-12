# ModuleGuard
This project provides a tool to detect module conflicts, which consists of two parts: InstSimulator and EnvResolver.
* **InstSimulator**: It is a tool to statically analyze the module path of a third-party package installed. Its core idea is to use a file tree to simulator the execution of Python configuration code.

* **EnvResolver**: It is a tool for analyzing direct dependencies and dependency graphs. It uses the pip parsing framework `resolvelib` and is optimized for speedup. Therefore, the accuracy and the efficiency are higher than other tools.

## Project Struct
```bash
.
├── builtin-libs  # file for built-in libraries
├── datasrc     # paper's data 
├── detect_MC.py # detect module conflict module
├── EnvResolver
│   ├── extras_provider.py
│   ├── get_dep_information.py 
│   ├── __init__.py
│   ├── __pycache__
│   ├── pypi_wheel.py  # dependency resolution
│   ├── setup_parse_dep.py   # parse setup.py modified from PyCD tool
│   ├── sqlclass.py 
│   └── sql.py
├── envresolver_main.py # test function of EnvResolver
├── evaluation
├── InstSimulator
│   ├── file_node_struct.py # file_tree struct
│   ├── get_modules_information.py
│   ├── __init__.py
│   ├── __pycache__
│   └── setup_parse_path.py # parse setup.py modified from PyCD 
├── instsimulator_main.py # test function of InstSimulator
├── README.md
├── requirements.txt # dependency of the projects
└── testfile  
```

## Run From Docker
We have provided a docker image containing the database and code for this project, which can be pulled directly from docker hub. Since the database in the image contains the data of the entire PyPI ecosystem, the mirror is large and it is recommended to add a proxy when download.

Hash of zhuzhuzhuzai/moduleguard:latest:
```
DIGEST:sha256:afc812aac4dde0ab8ee755c3b345a72f44e708ad6a19e885f212b4fbf7ed189e
```

You can run the command in your terminal.
```
docker run -p 61111:5432 -it zhuzhuzhuzai/moduleguard /bin/bash
```

Then you'll get into bash that interacts with the container. Type the following command in bash to start the postgresql service.
```
service postgresql start 
```

## Run With Source Code in Ubuntu 22.04

### Configure postgresql
* get the base knowledge data from google. [link](https://drive.google.com/file/d/1ovUj2MekkE8M5IdwA55EfQeX74OnYDjq/view?usp=sharing)
* install the postgresql.
    ```bash
    $ sudo apt-get install postgresql
    ```
* update the sql user,  password and authentication.
    ```bash
    # get into sql service with the user `postgres`
    $ sudo -u postgres psql
    postgres=# 

    # change the default password. Add ';' in the end.
    $ postgres=# ALTER USER postgres WITH PASSWORD 'password';

    # create database `moduleguard`. Add ';' in the end.
    $ postgres=# CREATE database moduleguard;

    # exit psql
    $ postgres=# \q

    # Alter authentication and modify configuration file pg_hba.conf. 
    $ vim /etc/postgresql/x.x/main/pg_hba.conf # x.x is a number.
    # Then find
    local   all          postgres         peer
    # change to
    local   all          postgres          md5

    # restart postgresql service
    $ service postgresql restart
    
    ```
* restore the database.
    ```bash
    $ pg_restore -U postgres -W -d moduleguard moduleguard_sql 
    ```
* download the project.
    ```bash
    $ git clone https://github.com/unsatisfying/ModuleGuard.git # download moduleguard
    $ cd ModuleGuard
    $ pip install -r requirements.txt
    ```
* configure the project.
    ```bash
    # change EnvResolver/sql.py and EnvResolver/sqlclass.py
    database = PostgresqlDatabase('SQLNAME', **{'host': 'localhost', 'user': 'XXX', 'password': 'XXX'})
    # change to, so was the EnvResolver/sqlclass.py.
    database = PostgresqlDatabase('moduleguard', **{'host': 'localhost', 'user': 'postgres', 'password': 'postgres'})
    ```
## Manual of the project
### instsimulator_main
This module provides the main functionality of instsimulator. It can statically resolve the module path after the package is installed in an installation-free way.

This module can take the following arguments.
| Argument | Description |
| ------- | --------------- |
| -l, --local | Given the path of a local package. Currently only `tar.gz`, `whl`, `egg`, `zip` packages are supported.       |
| -r, --remote| Given a package name and version, instsimulator will go to PyPI to download the package and extract modules after installation. This argument's value must be in the format `package_name`==`package_version`. e.g., requests==2.28.1        |
| -d, --dir| Given a particular directory that contains at least one configuration file. Currently, only three formats are supported: `setup.py`, `setup.cfg`, `pyproject.toml`.        |

For example, you can use the following command to test the `instsimulator_main.py`. The `InstSimulator/testfile` contains packages for testing.

```bash
# command
python3 instsimulator_main.py -l InstSimulator/testfile/requests-2.31.0-py3-none-any.whl

# result
root@xxx:/ModuleGuard# python3 instsimulator_main.py -l InstSimulator/testfile/requests-2.31.0-py3-none-any.whl
['requests/__init__.py', 'requests/__version__.py', 'requests/_internal_utils.py', 'requests/adapters.py', 'requests/api.py', 'requests/auth.py', 'requests/certs.py', 'requests/compat.py', 'requests/cookies.py', 'requests/exceptions.py', 'requests/help.py', 'requests/hooks.py', 'requests/models.py', 'requests/packages.py', 'requests/sessions.py', 'requests/status_codes.py', 'requests/structures.py', 'requests/utils.py']
```

```bash
# command
python3 instsimulator_main.py -r requests==2.28.2

# result
root@c344d148d2e5:/xxx# python3 instsimulator_main.py -r requests==2.28.2
['requests/__init__.py', 'requests/__version__.py', 'requests/_internal_utils.py', 'requests/adapters.py', 'requests/api.py', 'requests/auth.py', 'requests/certs.py', 'requests/compat.py', 'requests/cookies.py', 'requests/exceptions.py', 'requests/help.py', 'requests/hooks.py', 'requests/models.py', 'requests/packages.py', 'requests/sessions.py', 'requests/status_codes.py', 'requests/structures.py', 'requests/utils.py']
```

```bash
# command
python3 instsimulator_main.py -d InstSimulator/testfile/requests-2.31.0

# result
root@xxx:/ModuleGuard# python3 instsimulator_main.py -d InstSimulator/testfile/requests-2.31.0
['requests/exceptions.py', 'requests/sessions.py', 'requests/cookies.py', 'requests/structures.py', 'requests/compat.py', 'requests/certs.py', 'requests/hooks.py', 'requests/status_codes.py', 'requests/packages.py', 'requests/utils.py', 'requests/_internal_utils.py', 'requests/help.py', 'requests/adapters.py', 'requests/models.py', 'requests/__version__.py', 'requests/api.py', 'requests/__init__.py', 'requests/auth.py']
```


### envresolver_main
This module contains the core functionality of EnvResolver, including the extraction of direct dependency information from configuration files and the resolution of dependency graphs with a local knowledge base.

This module can take the following arguments.
| Argument | Description |
| ------- | --------------- |
| -l, --local | Given the path of a local package. Currently only `tar.gz`, `whl`, `egg`, `zip` packages are supported.       |
| -r, --remote| Given a package name and version, envresolver will go to PyPI to download the package and resolve the dependencies. This argument's value must be in the format `package_name`==`package_version`. e.g., requests==2.28.1        |
| -f, --file| Given a particular configuration file, envresolver resolves the dependencies declared in the configuration file. Currently, only three formats are supported: `setup.py`, `setup.cfg`, `pyproject.toml`.        |
| -g, --graph| If the `-g` or `--graph` argument is given, the dependency graph is resolved and printed instead of only direct dependencies.

For example, you can use the following command to test the `envresolver_main.py`. The `EnvResolver/testfile` contains packages for testing.

```bash
# command
python3 envresolver_main.py -l EnvResolver/testfile/requests-2.31.0-py3-none-any.whl

# result
root@xxx:/ModuleGuard# python3 envresolver_main.py -l EnvResolver/testfile/requests-2.31.0-py3-none-any.whl
All direct dependency: ['charset-normalizer (<4,>=2)', 'idna (<4,>=2.5)', 'urllib3 (<3,>=1.21.1)', 'certifi (>=2017.4.17)', "PySocks (!=1.5.7,>=1.5.6) ; extra == 'socks'", "chardet (<6,>=3.0.2) ; extra == 'use_chardet_on_py3'"]
```

```bash
# command
python3 envresolver_main.py -f EnvResolver/testfile/setup.py

# result
root@xxx:/ModuleGuard# python3 envresolver_main.py -f EnvResolver/testfile/setup.py
All direct dependency: ["PySocks>=1.5.6, !=1.5.7 ; extra == 'socks'", "chardet>=3.0.2,<6 ; extra == 'use_chardet_on_py3'", 'charset_normalizer>=2,<4', 'idna>=2.5,<4', 'urllib3>=1.21.1,<3', 'certifi>=2017.4.17']
```

```bash
# command
python3 envresolver_main.py -r twine==4.0.1

# result
root@xxx:/ModuleGuard# python3 envresolver_main.py -r twine==4.0.1
All direct dependency: ['pkginfo (>=1.8.1)', 'readme-renderer (>=35.0)', 'requests (>=2.20)', 'requests-toolbelt (!=0.9.0,>=0.8.0)', 'urllib3 (>=1.26.0)', 'importlib-metadata (>=3.6)', 'keyring (>=15.1)', 'rfc3986 (>=1.4.0)', 'rich (>=12.0.0)']
```

```bash
# command
python3 envresolver_main.py -g -l EnvResolver/testfile/requests-2.31.0-py3-none-any.whl

# result
root@xxx:/ModuleGuard# python3 envresolver_main.py -g -l EnvResolver/testfile/requests-2.31.0-py3-none-any.whl

****************************Dependency Graph Node**************************

DG node: {'urllib3': '1.26.14', 'certifi': '2022.12.7', 'charset-normalizer': '3.1.0', 'idna': '3.4', None: ''}

****************************Dependency Graph Edge**************************

DG edge: {None: {'urllib3', 'idna', 'certifi', 'charset-normalizer'}, 'charset-normalizer': set(), 'idna': set(), 'urllib3': set(), 'certifi': set()}
```

### detect_MC
This module is used to help projects detect module conflicts. Since we do not have access to the local environment information of the user, we currently support the analysis of `module-to-lib` and `module-in-dep` conflicts. The result of `module-to-tpl` conflicts is slower to resolve, so it can be uncommented and used if necessary. In addition, we assume that the user has 200 built-in libraries, that are recorded in the file `builtin-libs`.

This module can take the following arguments.
| Argument | Description |
| ------- | --------------- |
| -f, --file |Given a particular configuration file, moduleguard will analysis the dependencies and raw module data from configuration file. Moreover, moduleguard take the directory where the configuration file in as the root path. Then based on raw module data, it parse the module information from the root path.  Currently, only three formats are supported: `setup.py`, `setup.cfg`, `pyproject.toml`      |
| -p, --path| Given the root directory of the project, the root directory must contain one of `setup.py`, `setup.cfg`, `pyproject.toml`, `requirements.txt` to resolve the dependency, One of the first three must be included to resolve the module information.|
| -r, --remote| Given a package name and version, moduleguard will go to PyPI to download the package and resolve the dependencies and module information. This argument's value must be in the format `package_name`==`package_version`. e.g., requests==2.28.1    |

 
