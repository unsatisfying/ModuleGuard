# ModuleGuard
This project provides a tool to detect module conflicts, which consists of two parts: InstSimulator and EnvResolver.
* **InstSimulator**: It is a tool to statically analyze the module path of a third-party package installed. Its core idea is to use a file tree to simulator the execution of Python configuration code.

* **EnvResolver**: It is a tool for analyzing direct dependencies and dependency graphs. It uses the pip parsing framework `resolvelib`` and is optimized for speedup. Therefore, the accuracy and the efficiency are higher than other tools.

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

## Manual of the project
