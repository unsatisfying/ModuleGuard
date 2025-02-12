from collections import deque
import fnmatch
import copy

class Node:
    def __init__(self, name):
        self.name = name
        self.children = []
        self.parent = None
        self.isleaf = False #.py

    def add_child(self, child):
        self.children.append(child)
        child.parent = self
    
    def remove_child(self, child):
        self.children.remove(child)
        child.parent = None

    def get_child(self, name):
        for child in self.children:
            if not child.isleaf and child.name == name:
                return child
        return None
    def get_child_leaf(self, name):
        for child in self.children:
            if child.isleaf and child.name == name:
                return child
        return None

    def __str__(self):
        return self.name

class Tree:
    def __init__(self, paths: list):
        self.root = Node(".")
        self.build_tree(paths)

    def build_tree(self, paths: list):
        root = self.root
        for path in paths:
            if not path.endswith(".py") or path.endswith("/setup.py") or path == "setup.py":
                continue
            path = path[:-3]
            parts = path.split("/")
            current_node = root
            for part in parts[:-1]:
                if part:
                    child_node = current_node.get_child(part)
                    # for child in current_node.children:
                    #     if child.name == part:
                    #         child_node = child
                    #         break
                    if not child_node:
                        child_node = Node(part)
                        current_node.add_child(child_node)
                    current_node = child_node
            if parts[-1]:
                child_node = Node(parts[-1])
                child_node.isleaf = True
                current_node.add_child(child_node)

    def remove_node(self, node):
        if isinstance(node, str):
            node = self.get_node(node)
        if not node:
            return
        parent_node = node.parent
        if not parent_node:
            return
        parent_node.remove_child(node)

    def remove_node_leaf(self, node):
        if isinstance(node, str):
            node = self.get_node_leaf(node)
        if not node:
            return
        parent_node = node.parent
        if not parent_node:
            return
        parent_node.remove_child(node)

    # a/b/c namespace_packages
    def get_node_from_absstr(self, str_name: str):
        if str_name == ".":
            return self.root
        str_name = str_name.replace(".", "/")
        str_name = str_name.split("/")
        now_node = self.root
        for name in str_name:
            sub_node = now_node.get_child(name)
            if sub_node == None:
                return None
            now_node = sub_node
        return now_node
    # a/b/c.py
    def get_node_from_absstr_leaf(self, str_name: str):
        str_name = str_name.split("/")
        now_node = self.root
        for name in str_name[:-1]:
            sub_node = now_node.get_child(name)
            if sub_node == None:
                return None
            now_node = sub_node
        if str_name[-1]:
            sub_node = now_node.get_child_leaf(str_name[-1])
            if sub_node == None:
                return None
            now_node = sub_node
        return now_node
    
    # midle_node
    def get_node(self, name: str):
        queue = deque([self.root])
        while queue:
            node = queue.popleft()
            if not node.isleaf and node.name == name:
                return node
            queue.extend(node.children)
        return None
    
    #leaf_node
    def get_node_leaf(self, name: str):
        queue = deque([self.root])
        while queue:
            node = queue.popleft()
            if node.isleaf and node.name == name:
                return node
            queue.extend(node.children)
        return None

    def update_node(self, name: str, new_name: str):
        node = self.get_node(name)
        if node:
            node.name = new_name

    def update_node_leaf(self, name: str, new_name: str):
        node = self.get_node_leaf(name)
        if node:
            node.name = new_name

    def update_root(self, node: Node):
        self.root = node

    def dfs_traversal(self, node=None, path=""):
        if not node:
            node = self.root
        if node.name:
            path += "/" + node.name
        if not node.children:
            return [path[1:]]
        paths = []
        for child in node.children:
            paths += self.dfs_traversal(child, path)
        return paths

    def get_tree_path(self):
        if self.root.children == []:
            return []
        all_paths = self.dfs_traversal()
        for i in range(len(all_paths)):
            all_paths[i] = (all_paths[i] + ".py").split("/", 1)[1]
        return all_paths
    
    # def update()

    def get_packages(self, package_dir_map, packages):

        if "" in package_dir_map:
            tmp_root = self.get_node(package_dir_map[""]) 
            self.update_root(tmp_root)
        new_packages = []
        for package in packages:
            if package in package_dir_map:
                package_node = self.get_node_from_absstr(package_dir_map[package])
                if package_node:
                    package_node_list = package.split(".")   
                    tmp_root_node = Node(package_node_list[0])
                    now_root_node = tmp_root_node
                    for i in range(len(package_node_list)-1):
                        tmp_node = Node(package_node_list[i+1])
                        now_root_node.add_child(tmp_node)
                        now_root_node = tmp_node

                    now_root_node.children = package_node.children
                    new_packages.append(tmp_root_node)
            else:
                package_node = self.get_node_from_absstr(package)
                if package_node:
                    package_node_list = package.split(".")   
                    tmp_root_node = Node(package_node_list[0])
                    now_root_node = tmp_root_node
                    for i in range(len(package_node_list)-1):
                        tmp_node = Node(package_node_list[i+1])
                        now_root_node.add_child(tmp_node)
                        now_root_node = tmp_node
                    now_root_node.children = package_node.children
                    new_packages.append(tmp_root_node)
        return new_packages

    
    def find_packages(self, where=None, include=(), exclude=() ):
        
        if not where:
            where = "."
        if not include:
            include=()
        if not exclude:
            # exclude=('ci', 'ci.*', 'bin', 'bin.*', 'debian', 'debian.*', 'doc', 'doc.*', 'docs', 'docs.*', 'documentation', 'documentation.*', 'manpages', 'manpages.*', 'news', 'news.*', 'newsfragments', 'newsfragments.*', 'changelog', 'changelog.*', 'test', 'test.*', 'tests', 'tests.*', 'unit_test', 'unit_test.*', 'unit_tests', 'unit_tests.*', 'example', 'example.*', 'examples', 'examples.*', 'scripts', 'scripts.*', 'tools', 'tools.*', 'util', 'util.*', 'utils', 'utils.*', 'python', 'python.*', 'build', 'build.*', 'dist', 'dist.*', 'venv', 'venv.*', 'env', 'env.*', 'requirements', 'requirements.*', 'tasks', 'tasks.*', 'fabfile', 'fabfile.*', 'site_scons', 'site_scons.*', 'benchmark', 'benchmark.*', 'benchmarks', 'benchmarks.*', 'exercise', 'exercise.*', 'exercises', 'exercises.*', 'htmlcov', 'htmlcov.*', '[._]*', '[._]*.*')  
            exclude = ()
        where_node = self.get_node(where)
        if not where_node:
            return None
        
        self.update_root(where_node)
        packages = []
        for child in self.root.children:
            if child.children == []:
                continue
            if (child.get_child_leaf("__init__") \
                and (not include or any(fnmatch.fnmatch(child.name, pattern) for pattern in include)) \
                and (not exclude or not any(fnmatch.fnmatch(child.name, pattern) for pattern in exclude))):
                packages.append(child)
        return packages

    def find_namespace_packages(self, where=None, include=(), exclude=()):
        if not where:
            where = "."
        if not include:
            include=()
        if not exclude:
            # exclude=('ci', 'ci.*', 'bin', 'bin.*', 'debian', 'debian.*', 'doc', 'doc.*', 'docs', 'docs.*', 'documentation', 'documentation.*', 'manpages', 'manpages.*', 'news', 'news.*', 'newsfragments', 'newsfragments.*', 'changelog', 'changelog.*', 'test', 'test.*', 'tests', 'tests.*', 'unit_test', 'unit_test.*', 'unit_tests', 'unit_tests.*', 'example', 'example.*', 'examples', 'examples.*', 'scripts', 'scripts.*', 'tools', 'tools.*', 'util', 'util.*', 'utils', 'utils.*', 'python', 'python.*', 'build', 'build.*', 'dist', 'dist.*', 'venv', 'venv.*', 'env', 'env.*', 'requirements', 'requirements.*', 'tasks', 'tasks.*', 'fabfile', 'fabfile.*', 'site_scons', 'site_scons.*', 'benchmark', 'benchmark.*', 'benchmarks', 'benchmarks.*', 'exercise', 'exercise.*', 'exercises', 'exercises.*', 'htmlcov', 'htmlcov.*', '[._]*', '[._]*.*')  
            exclude = ()
        where_node = self.get_node(where)
        if not where_node:
            return None
        
        self.update_root(where_node)
        packages = []
        for child in self.root.children:
            if child.children == []:
                continue
            if ( (not include or any(fnmatch.fnmatch(child.name, pattern) for pattern in include)) \
                and (not exclude or not any(fnmatch.fnmatch(child.name, pattern) for pattern in exclude))):
                packages.append(child)
        return packages

    def get_py_modules(self, package_dir_map, py_modules):
        if "" in package_dir_map:
            tmp_root = self.get_node(package_dir_map[""])
        else:
            tmp_root = self.root   

        new_py_modules = []
        for py_module in py_modules:
            child = self.get_node_leaf(py_module)
            if child:
                new_py_modules.append(child)
        # py_module_node = tmp_root.children
        # for child in py_module_node:
        #     if child.name in py_modules and child.isleaf:
        #         new_py_modules.append(child)
        return new_py_modules

