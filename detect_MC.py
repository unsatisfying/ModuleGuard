import os
import argparse
from EnvResolver.get_dep_information import parse_setup_file, parse_setup_cfg_file, parse_pyproject_toml_file, parse_requirements_txt_file, get_dep_information_from_name_version, get_dep_information_from_package
from InstSimulator.get_modules_information import parse_setup_file_path, parse_setup_cfg_file_path, parse_pyproject_toml_file_path, get_modules_information_from_name_version, get_modules_information_from_package, get_modules_information_from_dirs
from EnvResolver.sql import ProjectsMetadata, database
from EnvResolver.pypi_wheel import dep_parser, display_resolution
from packaging.utils import canonicalize_name

def detect_module_to_tpl(modules, name):
    return {}
    res = {}
    for module in modules:
        q = ProjectsMetadata.select(ProjectsMetadata.name, ProjectsMetadata.version).where(ProjectsMetadata.module_path.contains("'{}'".format(module)))
        if len(q) > 0:
            for a in q:
                if name !="" and a.name == name:
                    continue
                if module not in res:
                    res[module] = []
                res[module].append("{}=={}".format(a.name, a.version))
    return res

def detect_module_to_lib(modules):
    res = {}
    with open("builtin-libs", "r") as f:
        builtin_libs = [a.strip() for a in f.readlines()]
    for module in modules:
        module_name = os.path.basename(module)[:-3]
        if module_name in builtin_libs:
            res[module] = "module_name"
    return res

def check_dependency(pinned_versions):
    all_path = {}
    try:
        for key, value in pinned_versions.items():
            if key == None:
                continue
            q = ProjectsMetadata.select(ProjectsMetadata.module_path).where(
                ProjectsMetadata.name == canonicalize_name(key), ProjectsMetadata.version == value)
            if len(q) == 0:
                q = ProjectsMetadata.select(ProjectsMetadata.module_path).where(
                    ProjectsMetadata.name == canonicalize_name(key), ProjectsMetadata.version_struct == value)
            if len(q) != 0 and q[0].module_path != None:
                subpath = set(
                    [a for a in eval(q[0].module_path) if a.endswith(".py")])
            else:
                subpath = set()

            for a in subpath:
                if a not in all_path:
                    all_path[a] = set()
                all_path[a].add("{}=={}".format(key, value))
        conflict_path = {}
        for key, value in all_path.items():
            if len(value) > 1:
                conflict_path[key] = value
        if conflict_path != {}:
            return conflict_path
        else:
            return None
    except:
        return None
    
def detect_module_in_dep(deps):
    my_resolve = dep_parser(list(deps))
    try:
        result = my_resolve.resolve(2000)
        vpin, vedge = display_resolution(result)
        conflict_path = check_dependency(vpin)
        return conflict_path
    except Exception as e:
        print(e)
        return {}
    

def detect_all_mc(modules, deps , name="", version=""):
    res = {"module_to_tpl": {}, "module_to_lib": {}, "module_in_dep": {}}
    
    res["module_to_tpl"] = detect_module_to_tpl(modules, name)

    res["module_to_lib"] = detect_module_to_lib(modules)

    res["module_in_dep"]= detect_module_in_dep(deps)

    return res


def main(args):
    if args.file:
        file_path = args.file
        root_dirs = os.path.dirname(file_path)
        all_modules = get_modules_information_from_dirs(root_dirs)
        if file_path.endswith("setup.py"):
            alldeps = parse_setup_file(file_path)
        elif file_path.endswith("setup.cfg"):
            alldeps = parse_setup_cfg_file(file_path)
        elif file_path.endswith("pyproject.toml"):
            alldeps = parse_pyproject_toml_file(file_path)
        elif file_path.endswith("requirements.txt"):
            alldeps = parse_requirements_txt_file(file_path)
        print(detect_all_mc(modules = all_modules, deps = alldeps))

    elif args.path:
        root_dirs = args.path
        all_modules = get_modules_information_from_dirs(root_dirs)

        files = ["setup.py", "setup.cfg", "pyproject.toml", "requirements.txt"]
        alldeps = []
        for i in range(len(files)):
            conf_file = os.path.join(root_dirs, files[i])
            if not os.path.exists(conf_file):
                continue

            if files[i] == "setup.py":
                alldeps += parse_setup_file(conf_file)
            elif files[i] == "setup.cfg":
                alldeps += parse_setup_cfg_file(conf_file)
            elif files[i] == "pyproject.toml":
                alldeps += parse_pyproject_toml_file(conf_file)
            elif files[i] == "requirements.txt":
                alldeps += parse_requirements_txt_file(conf_file)
   
        print(detect_all_mc(all_modules, alldeps))
    elif args.remote:
        package_version = args.remote
        package= package_version.split("==")[0]
        version = package_version.split("==")[1]

        all_modules = get_modules_information_from_name_version(package, version)
        all_deps = get_dep_information_from_name_version(package, version)
        print(detect_all_mc(all_modules, all_deps, name = package, version = version))

    else:
        print("Please specify a local path or a remote package name.")

    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="detect module conflict for the projects.")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("-f", "--file", help="give an path of configuration file. e.g., setup.py, setup.cfg, pyproject.toml")
    group.add_argument("-p", "--path", help="give an local path of projects")
    group.add_argument("-r", "--remote", help="give an remote package and version. e.g., requests==2.25.1")


    args = parser.parse_args()
    main(args)

