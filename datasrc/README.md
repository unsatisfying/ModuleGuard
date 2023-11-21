# ModuleGuard data sources
This folder provides all the data for RQs in xml format, and this document records the meaning of the different fields in each data file.

## RQ2_module_to_TPL_conflict
This file records all module paths for the latest version of all packages as of March 2023, as well as information about packages containing that module path.

The file content is based on the assumption that the detected conflicting packages will all be installed at the same time. And since python allows only one version of a project to exist at the same time, we assume that all installed packages are the latest version of that package. 
* module: Conflicting module paths
* distnum: The number of `packages` containing the conflicting module path. Note that `packages` here refer to the latest version of the package as of March 2023.
* packages: The names and versions of `packages` containing the conflicting module path. 

## RQ2_module_to_Lib_conflict
This file records all standard library names and all PyPI containing the standard library name as of March 2023.

The contents of the file are based on the assumption that all standard library names recorded in the user's local cache when Python interpreter is running.

* stdlib: Python built-in standard library name
* distnum: The number of `packages` using the built-in standard library names as its module names. Note that `packages` here refer to the all version of the package as of March 2023 (4.2 million).
* packages: The names and versions of packages using the built-in standard library names as its module names.

## RQ2_module_in_Dep_conflict
This file records the names and versions of module-in-dep conflicts in all PyPI packages, the conflicting module paths, and the dependencies that contain the conflicting module paths.

* name: The project name.
* version: The version of a project name that has module-in-Dep conflict.
* conflict_path: This field is a List where each element records a conflicting path owned by part of dependencies (more than 2).
* conflict_map: This field is a dictionary, where the key of the dictionary records each conflicting path, and the value of the dictionary records the name and version information of the dependency packages that have the conflicting module path.

## RQ2_module_in_Dep_conflict_diff_content
This file content is a subset of `RQ2_module_in_Dep_conflict`. The difference between two tables is that this file counts the hashes of the contents of the conflicting module files in different packages. Those `module-in-dep` conflicts that contain the same hash are removed.

* name: The project name.
* version: The version of a project name that has module-in-Dep conflict.
* conflict_path: This field is a List where each element records a conflicting path owned by part of dependencies (more than 2).
* conflict_map: This field is a dictionary, where the key of the dictionary records each conflicting path, and the value of the dictionary is also a Dict, which records the name and version information of the dependency packages that have the conflicting module path and the hashes of the conflicting module files.