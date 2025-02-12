import requests
import tempfile
import os
import rarfile
import tarfile
import zipfile
from packaging.utils import canonicalize_name
from .setup_parse_dep import DepsVisitor
import configparser
import toml
from pip._internal.models.wheel import Wheel
from pkginfo import Wheel as Wheel_pkginfo
from pkginfo import SDist as SDist_pkginfo
from pkginfo import BDist as BDist_pkginfo
from pkg_resources import split_sections
from wheel.metadata import *
# from pip._vendor.packaging.requirements import Requirement
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
        alldeps = []
        for key in tdpes:
            if key.from_ == "install_requires":
                alldeps.append(key.to_)
            if key.from_ == "extras_require":
                alldeps.append("{} ; extra == '{}'".format(key.to_, key.extra_info.value))
        return alldeps
    except:
        return []

# parse setup.cfg
# refference https://setuptools.pypa.io/en/latest/userguide/declarative_config.html
def parse_setup_cfg_file(setupcfg_file_path):
    with open(setupcfg_file_path, "r") as f:
        setup_cfg = f.read()
    alldeps = []
    config = configparser.ConfigParser()
    config.read_string(setup_cfg)
    if 'options' in config:
        if 'install_requires' in config['options']:
            deps = config['options']['install_requires'].strip().split("\n")
            for dep in deps:
                alldeps.append(dep)
        elif 'options.install_requires' in config:
            deps = config['options.install_requires'].strip().split("\n")
            for dep in deps:
                alldeps.append(dep)
        if 'extras_require' in config['options']:
            for key, value in config['options']['extra_requires'].items():
                if isinstance(value, list):
                    for dep in value:
                        alldeps.append("{} ; extra == '{}'".format(dep, key))
                elif isinstance(value, str):
                    alldeps.append("{} ; extra == '{}'".format(value, key))
        elif 'options.extras_require' in config:
            for key, value in config['options.extras_require'].items():
                if isinstance(value, list):
                    for dep in value:
                        alldeps.append("{} ; extra == '{}'".format(dep, key))
                elif isinstance(value, str):
                    alldeps.append("{} ; extra == '{}'".format(value, key))
    return alldeps

# parse pyproject.toml 
# refference https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html
def parse_pyproject_toml_file(pyproject_toml_file_path):
    alldeps = []
    with open(pyproject_toml_file_path, "r") as f:
        pyproject_toml = f.read()
    config = toml.loads(pyproject_toml)
    if 'project' in config:
        if 'dependencies' in config['project']:
            for dep in config['project']['dependencies']:
                alldeps.append(dep)
        if 'optional-dependencies' in config['project']:
            for key, value in config['project']['optional-dependencies'].items():
                if isinstance(value, list):
                    for dep in value:
                        alldeps.append("{} ; extra == '{}'".format(dep, key))
                elif isinstance(value, str):
                    alldeps.append("{} ; extra == '{}'".format(value, key))
        
    elif 'tool' in config and 'poetry' in config['tool']:
        if 'dependencies' in config['tool']['poetry']:
            for key, value in config['tool']['poetry']['dependencies'].items():
                if key == 'python':
                    continue
                if isinstance(value, str):
                    dep = "{}{}".format(key, value.replace("^", "~=").replace("*", ""))
                    if "*" != value and '.' not in value:
                        dep = "{}.0".format(dep)
                    alldeps.append(dep)
                elif isinstance(value, dict):
                    dep = key
                    if 'version' in value:
                        dep = "{}{}".format(dep, value['version'].replace("^", "~=").replace("*", ""))
                        if value['version'] and "*" != value['version'] and '.' not in value['version']:
                            dep = "{}.0".format(dep)
                        if 'optional' in value and value['optional'] == True:
                            try:
                                for extra_key, extra_value in config['tool']['poetry']['extras'].items():
                                    for extra_dep in extra_value:
                                        if extra_dep == key:
                                            dep = "{} ; extra == '{}'".format(dep, extra_key)
                            except:
                                pass
                        alldeps.append(dep)
    return alldeps

def parse_requirements_txt_file(requirements_txt_file_path):
    alldeps = []
    with open(requirements_txt_file_path, "r") as f:
        requirements_txt = f.readlines()
        for req in requirements_txt:
            if req.startswith("#"):
                continue
            req = req.split("# ")[0].strip()
            alldeps.append(req)
    return alldeps

def get_dep_information_from_name_version(package_name, version):
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
    # bdist_wheel, bdist_egg, sdist order
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

    # download file
    res = []
    for url in files:
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                file_path = os.path.join(temp_dir, url.split("/")[-1])
                with open(file_path, "wb") as f:
                    f.write(requests.get(url).content)
                res =  get_dep_information_from_package(file_path)
                if res != []:
                    return res
        except:
            continue
    return res

        


def get_dep_information_from_package(file_path):
        if not file_path.endswith((".zip", ".tar.gz", ".whl", ".egg")):
            raise Exception(f"Unsupported file type: {file_path}")
            

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
        alldeps = []
        
        if file_name.endswith((".whl", ".egg")):
            flag_top_level = 0
            if file_name.endswith(".whl"):
                pkgmetadata = Wheel_pkginfo(file_path)
            elif file_path.endswith(".egg"):
                pkgmetadata = BDist_pkginfo(file_path)
            if len(pkgmetadata.requires_dist) != 0:
                return list(pkgmetadata.requires_dist)
            
            for name in names:
                if "EGG-INFO/requires.txt" == name \
                    or name.endswith("{}.egg-info/requires.txt".format(file_package_name.replace("-", "_"))):
                    requires = str(
                        read_file(name), encoding="utf-8").strip("\n")
                
                    parsed_requirements = sorted(split_sections(requires), key=lambda x: x[0] or "")
                    for extra, reqs in parsed_requirements:
                        for key, value in generate_requirements({extra: reqs}):
                            if key == 'Requires-Dist':
                                alldeps.append(value)
                    return alldeps

        
        # analysis with setup.py setup.cfg pyproject.toml
        elif file_name.endswith((".zip", ".tar.gz")):

            for name in names:
                if "EGG-INFO/requires.txt" == name \
                    or name.endswith("{}.egg-info/requires.txt".format(file_package_name.replace("-", "_"))):
                    requires = str(
                        read_file(name), encoding="utf-8").strip("\n")
                
                    parsed_requirements = sorted(split_sections(requires), key=lambda x: x[0] or "")
                    for extra, reqs in parsed_requirements:
                        for key, value in generate_requirements({extra: reqs}):
                            if key == 'Requires-Dist':
                                alldeps.append(value)
                    return alldeps

            for name in names:
                if name.endswith("{}-{}/setup.py".format(file_package_name, file_package_version)):
                    with tempfile.TemporaryDirectory() as temp_dir:
                        setup_file_path = os.path.join(temp_dir, "setup.py")
                        with open(setup_file_path, "wb") as f:
                            f.write(read_file(name))
                        try:
                            alldeps += parse_setup_file(setup_file_path)
                        except:
                            pass

                elif name.endswith("{}-{}/setup.cfg".format(file_package_name, file_package_version)):
                    with tempfile.TemporaryDirectory() as temp_dir:
                        setup_file_path = os.path.join(temp_dir, "setup.cfg")
                        with open(setup_file_path, "wb") as f:
                            f.write(read_file(name))
                        try:
                            alldeps += parse_setup_cfg_file(read_file(name).decode("utf-8", errors="ignore"))
                        except:
                            pass

                elif name.endswith("{}-{}/pyproject.toml".format(file_package_name, file_package_version)):
                    
                    with tempfile.TemporaryDirectory() as temp_dir:
                        setup_file_path = os.path.join(temp_dir, "pyproject.toml")
                        with open(setup_file_path, "wb") as f:
                            f.write(read_file(name))
                        try:
                            alldeps += parse_pyproject_toml_file(read_file(name).decode("utf-8", errors="ignore"))
                        except:
                            pass

            return alldeps        
            
        else:
            print(f"Unsupported file type: {file_name}")
            return

