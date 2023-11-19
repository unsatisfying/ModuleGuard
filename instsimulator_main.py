import os
import argparse
from InstSimulator.get_modules_information import get_modules_information_from_package, get_modules_information_from_name_version, get_modules_information_from_dirs
def main(args):
    if args.local:
        path = args.local
        if os.path.exists(path):
            print(get_modules_information_from_package(path))

    elif args.remote:
        package = args.remote
        if "==" not in package:
            print("Please specify a package name with version: package==version")
            return
        package_version = package.split("==")
        print(get_modules_information_from_name_version(package_version[0], package_version[1]))

    elif args.dir:
        path = args.dir
        print(get_modules_information_from_dirs(path))
        
    else:
        print("Please specify a local path or a remote package name and version.")

    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze modules local packages or remote packages (i.e., package==version).")

    # 添加一个互斥组，包含两个选项，-l或--local，-r或--remote
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-l", "--local", help="local path of package")
    group.add_argument("-r", "--remote", help="remote package name and version. e.g., requests==2.25.1")
    group.add_argument("-d", "--dir", help="root directory of the project")
    # 解析命令行参数，传入main函数
    args = parser.parse_args()
    main(args)