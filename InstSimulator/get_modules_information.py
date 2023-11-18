import requests
import tempfile
import os
import rarfile
import tarfile
import zipfile
from packaging.utils import canonicalize_name
from file_node_struct import Tree, Node
from setup_parse_path import DepsVisitor
import configparser
import toml
import sys
import argparse
from pip._internal.models.wheel import Wheel

# file format parser
def _get_archive(fqn):
    if not os.path.exists(fqn):
        raise ValueError('No such file: %s' % fqn)

    if zipfile.is_zipfile(fqn):
        archive = zipfile.ZipFile(fqn)
        names = archive.namelist()

        def read_file(name):
            return archive.read(name)

        def extract_file(path):
            return archive.extractall(path=path)
    elif tarfile.is_tarfile(fqn):
        archive = tarfile.TarFile.open(fqn)
        names = archive.getnames()

        def read_file(name):
            return archive.extractfile(name).read()

        def extract_file(path):
            return archive.extractall(path=path)
    elif rarfile.is_rarfile(fqn):
        archive = rarfile.RarFile(fqn)
        names = archive.namelist()

        def read_file(name):
            return archive.read(name)

        def extract_file(path):
            return archive.extractall(path=path)

    else:
        raise ValueError('Not a known archive format: %s' % fqn)

    return archive, names, read_file, extract_file

#parse setup.py
def parse_setup_file(setup_file_path):
    try:
        ast_parse_setup = DepsVisitor(setup_file_path)

        tdpes = ast_parse_setup.end_dataflow
        for key in tdpes:
            if key.from_ == "packages":
                ast_parse_setup.packages.append(key.to_)
            elif key.from_ == "namespace_packages":
                ast_parse_setup.namespace_packages.append(key.to_)
            elif key.from_ == "py_modules":
                ast_parse_setup.py_modules.append(key.to_)
            elif key.from_ == "package_dir":
                ast_parse_setup.package_dir[key.extra_info.value] = key.to_
        return {
                "packages": ast_parse_setup.packages, 
                "namespace_packages": ast_parse_setup.namespace_packages, 
                "py_modules": ast_parse_setup.py_modules, 
                "package_dir": ast_parse_setup.package_dir,
                "packages_arg": ast_parse_setup.packages_arg,
                "namespace_packages_arg": ast_parse_setup.namespace_packages_arg,
                }
    except:
        return {}

# parse setup.cfg
# refference https://setuptools.pypa.io/en/latest/userguide/declarative_config.html
def parse_setup_cfg_file(content):
    packages_arg = {}
    namespace_packages_arg = {}
    try:
        config = configparser.ConfigParser()
        config.read_string(content)
        packages = config.get("options", "packages", fallback="")
        namespace_packages = config.get("options", "namespace_packages", fallback="")
        py_modules = config.get("options", "py_modules", fallback="")

        if packages == "find:" or packages == "find_namespace:":
            packages = packages.split(":")[0]+"_packages"
            where = config.get("options.packages.find", "where", fallback="")
            include = config.get("options.packages.find", "include", fallback="").strip().split("\n")
            exclude = config.get("options.packages.find", "exclude", fallback="").strip().split("\n")
            
            if where != '':
                packages_arg["where"] = where
            if include != ['']:
                packages_arg["include"] = include
            if exclude != ['']:
                packages_arg["exclude"] = exclude
        elif packages != '':
            packages = packages.split()
        else:
            packages = []



        if namespace_packages!= []:
            namespace_packages = namespace_packages.split()
        else:
            namespace_packages = []
        
        if py_modules != '':
            py_modules = py_modules.split()
        else:
            py_modules = []

        package_dir = config.get("options", "package_dir", fallback="")
        package_dir_dict = {}
        for line in package_dir.split('\n'):
            if line.strip() != '':
                key, value = line.split("=")
                package_dir_dict[key.strip()] = value.strip()
        return {
            "packages": packages if packages!="" else [],
            "namespace_packages": namespace_packages if namespace_packages!="" else [],
            "package_dir": package_dir_dict if package_dir_dict!="" else {},
            "py_modules": py_modules if py_modules != "" else [],
            "packages_arg": packages_arg,
            "namespace_packages_arg": namespace_packages_arg
        }
    except:
        return {}

# parse pyproject.toml 
# refference https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html
def parse_pyproject_toml_file(content):
    packages_arg = {}
    namespace_packages_arg = {}
    try:
        data = toml.loads(content)
        tool = data.get("tool", {})
        setuptools = tool.get("setuptools", {})
        packages = setuptools.get("packages", "")
        namespace_packages = setuptools.get("namespace_packages", "")
        if isinstance(packages, dict) and "find" in packages:
            # if "namespace" in packages["find"]:
            packages_dict = packages["find"]
            for key in ["where", "include", "exclude"]:
                if key in packages_dict:
                    if "namespace" in packages_dict and packages_dict["namespace"]:
                        namespace_packages_arg[key] = packages_dict[key]
                        packages = "find_namespace_packages"
                    else:
                        packages_arg[key] = packages_dict[key]  
                        packages = "find_packages"

        if isinstance(namespace_packages, dict) and "find" in namespace_packages:
            namespace_packages_dict = namespace_packages["find"]
            for key in ["include", "exclude", "where"]:
                if key in namespace_packages_dict:
                    if "namespace" in namespace_packages_dict and namespace_packages_dict["namespace"]:
                        namespace_packages_arg[key] = namespace_packages_dict[key]
                        namespace_packages = "find_namespace_packages"
                    else:
                        namespace_packages_arg[key] = namespace_packages_dict[key]  
                        namespace_packages = "find_packages"
        package_dir = setuptools.get("package_dir", "")
        py_modules = setuptools.get("py_modules", "")
        return {
            "packages": packages if packages!="" else [],
            "namespace_packages": namespace_packages if namespace_packages!="" else [],
            "package_dir": package_dir if package_dir!="" else {},
            "py_modules": py_modules if py_modules != "" else [],
            "packages_arg": packages_arg,
            "namespace_packages_arg": namespace_packages_arg
        }
    except:
        return {}
    
def get_modules_information_from_name_version(package_name, version):
    # Get json information from pypi
    url = f"https://pypi.org/pypi/{package_name}/{version}/json"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to get package information for {package_name} {version}")
        return
    
    package_json_info = response.json()
    package_name = package_json_info["info"]["name"]
    files_urls = package_json_info["urls"]
    files = []
    
    for item in files_urls:
        if item['packagetype'] in ["bdist_wheel", "bdist_egg", "sdist"]:
            files.append(item['url'])
    if len(files) == 0:
        print(f"Failed to find any files for {package_name} {version}")
        return
    # 按照bdist_wheel, bdist_egg, sdist的顺序进行排序
    def get_suffix_order(file_name):
        if file_name.endswith(".whl"):
            return 1
        elif file_name.endswith(".egg"):
            return 2
        elif file_name.endswith(".tar.gz"):
            return 3
        elif file_name.endswith(".zip"):
            return 4
        else:
            return 5
    def get_pyvers(file_name):
        try:
            wheel_meta = Wheel(file_name)
        except:
            return 3
        if wheel_meta.pyversions == ['py2.py3'] or wheel_meta.pyversions == ['py3'] or wheel_meta.pyversions == ['any']:
            return 1
        else:
            return 2
    def get_platform(file_name):
        try:
            wheel_meta = Wheel(file_name)
        except:
            return 3
        if 'any' in wheel_meta.plats or 'linux_x86_64' in wheel_meta.plats:
            return 1
        else:
            return 2
    files.sort(key=lambda x: (get_suffix_order(x), get_pyvers(x), get_platform(x)))

    # 下载并分析第一个文件
    res = []
    for url in files:
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                file_path = os.path.join(temp_dir, url.split("/")[-1])
                with open(file_path, "wb") as f:
                    f.write(requests.get(url).content)
                res =  get_modules_information_from_package(file_path)
                if res != []:
                    return res
        except:
            continue
    return res

        


def get_modules_information_from_package(file_path):
        if not file_path.endswith((".zip", ".tar.gz", ".whl", ".egg")):
            raise Exception(f"Unsupported file type: {file_path}")
            return

        file_name = file_path.split("/")[-1]
        for ext in [".whl", ".tar.gz", ".egg", ".zip"]:
            if file_name.endswith(ext):
                new_file_name = file_name[:-len(ext)]
        if file_path.endswith(".whl"):
            meta = Wheel(file_name)
            file_package_version = meta.version
            file_package_name = meta.name
        else:
            file_package_version = new_file_name.split("-")[-1]
            file_package_name = new_file_name[:-len(file_package_version)-1]

        archive, names, read_file, extract_file = _get_archive(file_path)    
    # analysis all_paths and top_level
        all_path = []
        top_level = []
        namespace_packages = []
        
        if file_name.endswith((".whl", ".egg")):
            flag_top_level = 0
            if file_name.endswith(".whl"):
                for name in names:
                    # all_path
                    if name.endswith("{}-{}.dist-info/RECORD".format(canonicalize_name(file_package_name).replace("-", "_"), file_package_version.replace("-", "_"))) \
                        or name.endswith("{}-{}.dist-info/RECORD".format(file_package_name.replace("-", "_"), file_package_version.replace("-", "_"))):
                        all_path = str(read_file(name),
                                encoding="utf-8", errors="ignore").strip("\n").split("\n")
                        real_path = []
                        # strip hash value
                        for mod in all_path:
                            mod = mod.split(",")[0]
                            if mod.endswith(".py"):
                                real_path.append(mod)
                        all_path = real_path
                        break
                for name in names:
                    # all_path
                    if name.endswith("{}-{}.dist-info/top_level.txt".format(canonicalize_name(file_package_name).replace("-", "_"), file_package_version.replace("-", "_"))) \
                        or name.endswith("{}-{}.dist-info/top_level.txt".format(file_package_name.replace("-", "_"), file_package_version.replace("-", "_"))):
                        top_level = str(read_file(name),
                                encoding="utf-8", errors="ignore").strip("\n").split("\n")
                        flag_top_level = 1
                        break
            elif file_name.endswith(".egg"):
                for name in names:
                    if "EGG-INFO/SOURCES.txt" == name \
                        or name.endswith("{}.egg-info/SOURCES.txt".format(file_package_name.replace("-", "_"))):
                        all_path = str(read_file(name),
                                    encoding="utf-8", errors="ignore").strip("\n").split("\n")
                        break
                for name in names:
                    if "EGG-INFO/top_level.txt" == name \
                        or name.endswith("{}.egg-info/top_level.txt".format(file_package_name.replace("-", "_"))):
                        top_level = str(read_file(name),
                                encoding="utf-8", errors="ignore").strip("\n").split("\n")
                        flag_top_level = 1
                        break
            #   analysis modules from whl metadata files, first construct a Tree
            if all_path != [] and top_level != []:
                root_tree = Tree(all_path)
                implicate_root = root_tree.get_node("{}-{}".format(canonicalize_name(file_package_name).replace("-", "_"), file_package_version.replace("-", "_")))
                if not implicate_root:
                    implicate_root = root_tree.get_node("{}-{}".format(file_package_name.replace("-", "_"), file_package_version.replace("-", "_")))

                if implicate_root:
                    root_tree.update_root(implicate_root)
                    root_tree.root.name = "."           
                new_root_child = []
                for child in root_tree.root.children:
                    if child.name in top_level:
                        new_root_child.append(child)
                root_tree.root.children = new_root_child
                return root_tree.get_tree_path()
            elif all_path != [] and top_level == [] and flag_top_level == 0:
                root_tree = Tree(all_path)
                return root_tree.get_tree_path()
            else:
                # print(f"No Metadata File: {file_path}")
                return []

        
        # analysis with setup.py setup.cfg pyproject.toml
        elif file_name.endswith((".zip", ".tar.gz")):
            ast_parse_setup = None
            parsed_args = {}
            for name in names:
                if parsed_args != {} and parsed_args != {'packages': [], 'namespace_packages': [], 'package_dir': {}, 'py_modules': [], 'packages_arg': {}, 'namespace_packages_arg': {}}:
                    break
                if name.endswith("{}-{}/setup.py".format(file_package_name, file_package_version)):
                    with tempfile.TemporaryDirectory() as temp_dir:
                        setup_file_path = os.path.join(temp_dir, "setup.py")
                        with open(setup_file_path, "wb") as f:
                            f.write(read_file(name))
                        try:
                            parsed_args = parse_setup_file(setup_file_path)
                        except:
                            parsed_args = {}

                elif name.endswith("{}-{}/setup.cfg".format(file_package_name, file_package_version)):
                    try:
                        parsed_args = parse_setup_cfg_file(read_file(name).decode("utf-8", errors="ignore"))
                    except:
                        parsed_args = {}

                elif name.endswith("{}-{}/pyproject.toml".format(file_package_name, file_package_version)):
                    try:
                        parsed_args = parse_pyproject_toml_file(read_file(name).decode("utf-8", errors="ignore"))
                    except:
                        parsed_args = {}
            # get all modules
            if parsed_args == {} or parsed_args == {'packages': [], 'namespace_packages': [], 'package_dir': {}, 'py_modules': [], 'packages_arg': {}, 'namespace_packages_arg': {}}:
                flag_top_level = 0
                for name in names:
                    if "EGG-INFO/SOURCES.txt" == name \
                        or name.endswith("{}.egg-info/SOURCES.txt".format(file_package_name.replace("-", "_"))):
                        all_path = str(read_file(name),
                                    encoding="utf-8", errors="ignore").strip("\n").split("\n")
                        break
                for name in names:
                    if "EGG-INFO/top_level.txt" == name \
                        or name.endswith("{}.egg-info/top_level.txt".format(file_package_name.replace("-", "_"))):
                        top_level = str(read_file(name),
                                encoding="utf-8", errors="ignore").strip("\n").split("\n")
                        flag_top_level = 1
                        break
                for name in names:
                    if "EGG-INFO/namespace_packages.txt" == name \
                        or name.endswith("{}.egg-info/namespace_packages.txt".format(file_package_name.replace("-", "_"))):
                        namespace_packages = str(read_file(name),
                                encoding="utf-8", errors="ignore").strip("\n").split("\n")
                        break
            #   analysis modules from metadata files, first construct a Tree
                if all_path != [] and top_level != []:
                    root_tree = Tree(all_path)
                    for path in all_path:
                        if "EGG-INFO/SOURCES.txt" == path \
                            or path.endswith("{}.egg-info/SOURCES.txt".format(file_package_name.replace("-", "_"))):
                            implicate_dir = os.path.dirname(os.path.dirname(path))
                    if implicate_dir:
                        implicate_root = root_tree.get_node_from_absstr(implicate_dir)
                        if implicate_root:
                            root_tree.update_root(implicate_root)
                            root_tree.root.name = "."
                        new_root_child = []
                    for child in root_tree.root.children:
                        if child.name in top_level:
                            new_root_child.append(child)
                    root_tree.root.children = new_root_child
                    for namespace in namespace_packages:
                        namespace_node = root_tree.get_node_from_absstr_leaf("{}/__init__".format(namespace))
                        if namespace_node:
                            namespace_node.parent.remove_child(namespace_node)
                    return root_tree.get_tree_path()
                elif all_path != [] and top_level == [] and flag_top_level == 0:
                    root_tree = Tree(all_path)
                    for namespace in namespace_packages:
                        namespace_node = root_tree.get_node_from_absstr_leaf("{}/__init__".format(namespace))
                        if namespace_node:
                            namespace_node.parent.remove_child(namespace_node)
                
                    return root_tree.get_tree_path()
                else:
                    # print(f"No Metadata File: {file_path}")
                    return []

            root_tree = Tree(names)
            implicate_root = root_tree.get_node("{}-{}".format(canonicalize_name(file_package_name).replace("-", "_"), file_package_version))
            if implicate_root == None:
                implicate_root = root_tree.get_node("{}-{}".format(canonicalize_name(file_package_name), file_package_version))
            if implicate_root == None:
                implicate_root = root_tree.get_node("{}-{}".format(file_package_name.replace("-", "_"), file_package_version))
            if implicate_root:
                root_tree.update_root(implicate_root)
                root_tree.root.name = "."
            
            # if parsed_args["packages_dir"] != {}:
            #     root_tree.update_packages_dir(parsed_args["packages_dir"])
            
            root_child = []
            # print(parsed_args)
            # solve packages
            where = None
            exclude = None
            include = None
            if parsed_args["packages"] == "find_packages":
                find_packages_args = parsed_args["packages_arg"]
                if 'where' in find_packages_args:
                    where = find_packages_args['where']
                if 'exclude' in find_packages_args:
                    exclude = find_packages_args['exclude']
                if 'include' in find_packages_args:
                    include = find_packages_args['include']
                root_child += root_tree.find_packages(where, include, exclude)
    
            elif parsed_args["packages"] == "find_namespace_packages":
                find__namespace_packages_args = parsed_args["namespace_packages_arg"]
                if 'where' in find__namespace_packages_args:
                    where = find__namespace_packages_args['where']
                if 'exclude' in find__namespace_packages_args:
                    exclude = find__namespace_packages_args['exclude']
                if 'include' in find__namespace_packages_args:
                    include = find__namespace_packages_args['include']
                root_child += root_tree.find_namespace_packages(where, include, exclude)

            elif isinstance(parsed_args["packages"], list):
                root_child += root_tree.get_packages(parsed_args["package_dir"], parsed_args["packages"])

            # solve py_modules

            root_child += root_tree.get_py_modules(parsed_args["package_dir"], parsed_args["py_modules"])

            # solve namespace_packages
            root_tree.root.children = root_child

            for namespace in parsed_args["namespace_packages"]:
                namespace_node = root_tree.get_node_from_absstr_leaf("{}/__init__".format(namespace))
                if namespace_node:
                    namespace_node.parent.remove_child(namespace_node)
            
            res = root_tree.get_tree_path()
            
            if res != []:
                return res
            
            implicate_dir = None
            flag_top_level = 0
            for name in names:
                if "EGG-INFO/SOURCES.txt" == name \
                    or name.endswith("{}.egg-info/SOURCES.txt".format(file_package_name.replace("-", "_"))):
                    all_path = str(read_file(name),
                                encoding="utf-8", errors="ignore").strip("\n").split("\n")
                    break
            for name in names:
                if "EGG-INFO/top_level.txt" == name \
                    or name.endswith("{}.egg-info/top_level.txt".format(file_package_name.replace("-", "_"))):
                    top_level = str(read_file(name),
                            encoding="utf-8", errors="ignore").strip("\n").split("\n")
                    flag_top_level == 1
                    break
            for name in names:
                if "EGG-INFO/namespace_packages.txt" == name \
                    or name.endswith("{}.egg-info/namespace_packages.txt".format(file_package_name.replace("-", "_"))):
                    namespace_packages = str(read_file(name),
                            encoding="utf-8", errors="ignore").strip("\n").split("\n")
                    break
        #   analysis modules from metadata files, first construct a Tree
            if all_path != [] and top_level != []:
                root_tree = Tree(all_path)
                for path in all_path:
                    if "EGG-INFO/SOURCES.txt" == path \
                        or path.endswith("{}.egg-info/SOURCES.txt".format(file_package_name.replace("-", "_"))):
                        implicate_dir = os.path.dirname(os.path.dirname(path))
                if implicate_dir:
                    implicate_root = root_tree.get_node_from_absstr(implicate_dir)
                    if implicate_root:
                        root_tree.update_root(implicate_root)
                        root_tree.root.name = "."
                new_root_child = []
                for child in root_tree.root.children:
                    if child.name in top_level:
                        new_root_child.append(child)
                root_tree.root.children = new_root_child
                for namespace in namespace_packages:
                        namespace_node = root_tree.get_node_from_absstr_leaf("{}/__init__".format(namespace))
                        if namespace_node:
                            namespace_node.parent.remove_child(namespace_node)
                return root_tree.get_tree_path()
            elif all_path != [] and top_level == [] and flag_top_level == 0:
                root_tree = Tree(all_path)
                for namespace in namespace_packages:
                        namespace_node = root_tree.get_node_from_absstr_leaf("{}/__init__".format(namespace))
                        if namespace_node:
                            namespace_node.parent.remove_child(namespace_node)
                return root_tree.get_tree_path()
            else:
                # print(f"No Metadata File: {file_path}")
                return []
        else:
            print(f"Unsupported file type: {file_name}")
            return

def main(args):
    if args.local:
        path = args.local
        if os.path.exists(path):
            print(get_modules_information_from_package(path))

    elif args.remote:
        package = args.remote
        package_version = package.split("==")
        print(get_modules_information_from_name_version(package_version[0], package_version[1]))

    else:
        print("Please specify a local path or a remote package name.")

    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze PyPI package from local path or remote address.")

    # 添加一个互斥组，包含两个选项，-l或--local，-r或--remote
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-l", "--local", help="local path of requests package")
    group.add_argument("-r", "--remote", help="remote package name of requests")

    # 解析命令行参数，传入main函数
    args = parser.parse_args()
    main(args)
