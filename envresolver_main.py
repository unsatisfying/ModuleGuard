import os
import argparse
from EnvResolver.get_dep_information import get_dep_information_from_package, get_dep_information_from_name_version
from EnvResolver.get_dep_information import parse_setup_file, parse_setup_cfg_file, parse_pyproject_toml_file
from EnvResolver.pypi_wheel import dep_parser, display_resolution
def main(args):
    deps = []
    if args.local:
        path = args.local
        if os.path.exists(path):
            deps = get_dep_information_from_package(path)

    elif args.remote:
        package = args.remote
        if "==" not in package:
            print("Please specify a package name with version: package==version")
            return
        package_version = package.split("==")
        deps = get_dep_information_from_name_version(package_version[0], package_version[1])
    elif args.file:
        path = args.file
        if path.endswith("setup.py"):
            deps = parse_setup_file(path)
        elif path.endswith("setup.cfg"):
            deps =parse_setup_cfg_file(path)
        elif path.endswith("pyproject.toml"):
            deps =parse_pyproject_toml_file(path)

    else:
        print("Please specify a local path or a remote package name.")
        return
    if args.graph:
        my_resolve = dep_parser(list(deps))
        try:
            result = my_resolve.resolve(2000)
            vpin, vedge = display_resolution(result)
            print("\n****************************Dependency Graph Node**************************\n")
            print("DG node: {}".format(vpin))

            print("\n****************************Dependency Graph Edge**************************\n")
            print("DG edge: {}".format(vedge))
        except Exception as e:
            print(e)
        
    else:
        print("All direct dependency: {}".format(deps))

    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze dependency for local packages or remote packages.")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("-l", "--local", help="local path of package")
    group.add_argument("-r", "--remote", help="remote package name and version, e.g., requests==2.25.1")
    group.add_argument("-f", "--file", help="configuration file, only support setup.py, setup.cfg, pyproject.toml")
    parser.add_argument("-g", "--graph", help="get dependency graph", action="store_true")
    
    args = parser.parse_args()
    main(args)

