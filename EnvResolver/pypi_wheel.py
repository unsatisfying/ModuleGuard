import sys
import collections
import math
# from packaging.requirements import Requirement
from packaging.utils import canonicalize_name, NormalizedName
# from packaging.version import InvalidVersion, Version
from typing import (
    TYPE_CHECKING,
    Dict,
    Iterable,
    Iterator,
    Mapping,
    Sequence,
    TypeVar,
    Union,
    cast,
)
from pip._vendor.resolvelib.structs import DirectedGraph
from resolvelib import BaseReporter, Resolver
import resolvelib
from .extras_provider import ExtrasProvider
from .sqlclass import *
from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.version import Version, LegacyVersion
from pip._internal.req.req_install import InstallRequirement
from platform import python_version
from pip._vendor.packaging.markers import MARKER_EXPR, Marker
from operator import attrgetter
import functools
import math
import copy
PYTHON_VERSION = str(Version(python_version()))


def _has_route_to_root(criteria, key, all_keys, connected):
    if key in connected:
        return True
    if key not in criteria:
        return False
    for p in criteria[key].iter_parent():
        try:
            pkey = all_keys[id(p)]
        except KeyError:
            continue
        if pkey in connected:
            connected.add(key)
            return True
        if _has_route_to_root(criteria, pkey, all_keys, connected):
            connected.add(key)
            return True
    return False

Result = collections.namedtuple("Result", "mapping graph criteria")


def _build_result(state):
    mapping = state.mapping
    all_keys = {id(v): k for k, v in mapping.items()}
    all_keys[id(None)] = None

    graph = DirectedGraph()
    graph.add(None)  # Sentinel as root dependencies' parent.

    connected = {None}
    for key, criterion in state.criteria.items():
        if not _has_route_to_root(state.criteria, key, all_keys, connected):
            continue
        if key not in graph:
            graph.add(key)
        for p in criterion.iter_parent():
            try:
                pkey = all_keys[id(p)]
            except KeyError:
                continue
            if pkey not in graph:
                graph.add(pkey)
            graph.connect(pkey, key)

    return graph

class Candidate:
    def __init__(self, name, spec_version, dependency=[], yanked=False, extras=None):
        self.name = canonicalize_name(name)
        self.spec_version = spec_version
        try:
            self.version = Version(spec_version)
        except:
            self.version = LegacyVersion(spec_version)
        # self.metadata = metadata
        self.extras = extras
        self.dependency = dependency
        self._dependencies = []
        self.parsed = False
        self.yanked = yanked

        # if self.extras:
        #     formatted_extras = ",".join(sorted(self.extras))
        #     self.extra_name = self.name + f"[{formatted_extras}]"
        # else:
        #     self.extra_name = self.name

    def __repr__(self):
        if not self.extras:
            return f"<{self.name}=={self.version}>"
        return f"<{self.name}[{','.join(self.extras)}]=={self.version}>"

    # @property
    # def metadata(self):
    #     if self._metadata is None:
    #         self._metadata = get_metadata_for_wheel(self.url)
    #     return self._metadata

    # @property
    # def requires_python(self):
    #     return self.metadata.get("Requires-Python")

    # def _get_dependencies(self):
    #     # deps = self.metadata.get_all("Requires-Dist", [])
    #     extras = self.extras if self.extras else [""]

    #     for r in self.dependency:
    #         if r.marker is None:
    #             yield r
    #         else:
    #             for e in extras:
    #                 if r.marker.evaluate({"extra": e}):
    #                     yield r

    @property
    def dependencies(self):
        if self.parsed == False:
            self.parsed = True
            for a in self.dependency:
                # if len(a.extras) != 0:
                #     a.extras.clear()
                try:
                    req_instance = Requirement(a)
                    req_instance.name = canonicalize_name(req_instance.name)
                    # req_instance.extras={}
                    # if req_instance.marker != None and "extra" in str(req_instance.marker._markers):
                    #     continue
                except:
                    continue
                if req_instance.marker is None:
                    # if len(a.extras) == 0:
                    self._dependencies.append(req_instance)
                else:
                    for extra in self.extras:
                        if req_instance.marker.evaluate({"extra": extra, "python_version": PYTHON_VERSION}):
                            self._dependencies.append(req_instance)
                            continue
                    if req_instance.marker.evaluate({"extra": "MC_checknomal_None", "python_version": PYTHON_VERSION}):
                        self._dependencies.append(req_instance)

        # if self._dependencies is None:
        #     self._dependencies = list(self._get_dependencies())

        return self._dependencies


# def get_metadata_for_wheel(url):
#     data = requests.get(url).content
#     with ZipFile(BytesIO(data)) as z:
#         for n in z.namelist():
#             if n.endswith(".dist-info/METADATA"):
#                 p = BytesParser()
#                 return p.parse(z.open(n), headersonly=True)

#     # If we didn't find the metadata, return an empty dict
#     return EmailMessage()


class PyPIProvider(ExtrasProvider):
    def __init__(self, user_requested):
        self._user_requested = user_requested
        self._known_depths: Dict[str, float] = collections.defaultdict(
            lambda: math.inf)

    def identify(self, requirement_or_candidate):
        if isinstance(requirement_or_candidate, Requirement):
            if requirement_or_candidate.extras:
                formatted_extras = ",".join(set(requirement_or_candidate.extras))
                ret_name = requirement_or_candidate.name + f"[{formatted_extras}]"
                return ret_name
        return canonicalize_name(requirement_or_candidate.name)

    def get_extras_for(self, requirement_or_candidate):
        # Extras is a set, which is not hashable
        return tuple(sorted(requirement_or_candidate.extras))

    def get_base_requirement(self, candidate: Candidate):
        return Requirement("{}=={}".format(candidate.name, candidate.version))

    def get_preference(self, identifier, resolutions, candidates, information, backtrack_causes):
        criterion = list(information[identifier])

    #     * Prefer if any of the known requirements is "direct", e.g. points to an
    #       explicit URL.
    #     * If equal, prefer if any requirement is "pinned", i.e. contains
    #       operator ``===`` or ``==``.
    #     * If equal, calculate an approximate "depth" and resolve requirements
    #       closer to the user-specified requirements first.
    #     * Order user-specified requirements by the order they are specified.
    #     * If equal, prefers "non-free" requirements, i.e. contains at least one
    #       operator, such as ``>=`` or ``<``.
    #     * If equal, order alphabetically for consistency (helps debuggability).
    #     """

        candidate, ireqs = (None, [a.requirement for a in criterion])
        operators = [
            specifier.operator
            for specifier_set in (ireq.specifier for ireq in ireqs if ireq)
            for specifier in specifier_set
        ]

        direct = candidate is not None
        pinned = any(op[:2] == "==" for op in operators)
        unfree = bool(operators)

        try:
            requested_order: Union[int,
                                   float] = self._user_requested[identifier]
        except KeyError:
            requested_order = math.inf
            parent_depths = (
                self._known_depths[parent.name] if parent is not None else 0.0
                for _, parent in information[identifier]
            )
            inferred_depth = min(d for d in parent_depths) + 1.0
        else:
            inferred_depth = 1.0
        self._known_depths[identifier] = inferred_depth

        requested_order = self._user_requested.get(identifier, math.inf)
        delay_this = identifier == "setuptools"

        return (
            delay_this,
            not direct,
            not pinned,
            inferred_depth,
            requested_order,
            not unfree,
            identifier,
        )

    def find_matches(self, identifier, requirements, incompatibilities):
        requirements = set(requirements[identifier])
        # assert not any(
        #     r.extras for r in requirements
        # ), "extras not supported in this example"
        extras_set = set()
        for r in requirements:
            project_name = canonicalize_name(r.name)
            for a in r.extras:
                extras_set.add(a)

        bad_versions = {c.version for c in incompatibilities[identifier]}

        # Need to pass the extras to the search, so they
        # are added to the candidate at creation - we
        # treat candidates as immutable once created.
        candidates = [
            candidate
            for candidate in self.get_project_from_pypi(project_name, extras_set)
            if candidate.version not in bad_versions
        ]

        allowed_candidates = []
        for ReqObj in requirements:
            if ReqObj.specifier == SpecifierSet(""):
                for candidate in candidates:
                    if candidate.version.is_prerelease == False:
                        allowed_candidates.append(candidate)
                if len(allowed_candidates) == 0:
                    continue
                candidates = allowed_candidates[:]
                allowed_candidates = []
            prereleases = False
            for spec in ReqObj.specifier:
                prereleases |= spec.prereleases if spec.prereleases != None else False
            for spec in ReqObj.specifier:
                for candidate in candidates:
                    if spec.contains(candidate.version, prereleases=prereleases):
                        allowed_candidates.append(candidate)
                candidates = allowed_candidates[:]
                allowed_candidates = []
        allowed_candidates = []
        for candidate in candidates:
            if candidate.yanked:
                for ReqObj in requirements:
                    for spec in ReqObj.specifier:
                        if spec.operator == "==":
                            allowed_candidates.append(candidate)
            else:
                allowed_candidates.append(candidate)
        candidates = allowed_candidates[:]
        return sorted(candidates, key=attrgetter("version"), reverse=True)
    
    def is_satisfied_by(self, requirement, candidate):
        if canonicalize_name(requirement.name) != canonicalize_name(candidate.name):
            return False
        # ret_val = True
        # for spec in requirement.specifier:
        #     operator_callable = spec._get_operator(spec.operator)
        #     ret_val = ret_val and operator_callable(
        #         candidate.version, spec.version)
        # return ret_val
        spec = requirement.specifier
        return spec.contains(candidate.version, prereleases=True)

    def get_dependencies(self, candidate):
        return candidate.dependencies

    def get_project_from_pypi(self, project, extras):
        sql = "select {} from {} where name = '{}' order by version collate en_natural desc;".format(
            "name, version, dependency, yanked", "projects_metadata", canonicalize_name(project))
        q = database.execute_sql(sql)
        all_candidate = []
        for a in q:
            try:
                requirements = []
                if a[2] is not None:
                    requirements = eval(a[2])
            except:
                continue
            all_candidate.append(
                Candidate(a[0], a[1], requirements, a[3], extras=extras))
        return all_candidate


def display_resolution(result):
    
    graph = _build_result(result)
    vnode: set = copy.deepcopy(result.graph._vertices)
    vedge: dict = copy.deepcopy(result.graph._forwards)
    vpin = {}
    if '<Python from Requires-Python>' in graph._vertices:
        graph.remove('<Python from Requires-Python>')
    for node in graph._vertices:
        if node != None:
            vpin[node] = str(result.mapping[node].version)
        else:
            vpin[node] = ''
    for key in result.graph._vertices:
        if key == None:
            continue
        if canonicalize_name(key) != key:
            vpin[canonicalize_name(key)] = vpin[key]
            vpin.pop(key)
    for key, value in result.graph._forwards.items():
        if key == None:
            continue
        if canonicalize_name(key) != key:
            vedge[canonicalize_name(key)] = vedge[key]
            vedge.pop(key)
    
    for key, value in vedge.items():
        for dep in value:
            if canonicalize_name(dep) != dep:
                vedge[canonicalize_name(key)].add(canonicalize_name(dep))
                vedge[canonicalize_name(key)].remove(dep)   
    for key, value in vedge.items(): 
        if key != None and "[" in key:
            xlist = key.split("[")
            xlist_name = xlist[0]
            vedge[key].add(xlist_name)
    for tmp in vedge[None]:
        rootnode = tmp

    # print("{}\n".format(vpin))
    # print("{}\n".format(vedge))

    return vpin, vedge


class dep_parser:
    def __init__(self, reqs: list):
        self.reqs = reqs
        self.requirements = []
        for req in reqs:            
            try:
                if req.startswith('#'):
                    continue
                if '#' in req:
                    req = req.split('#', 1)[0]
                req_instance = Requirement(req)
                if self.get_project_from_pypi(req_instance) == []:
                    continue
                if req_instance.marker is None:
                    # if len(a.extras) == 0:
                    self.requirements.append(req_instance)
                else:
                    if req_instance.marker.evaluate({"extra": "MC_checknomal_None"}):
                        self.requirements.append(req_instance)
            except Exception as e:
                pass

        i = 0
        self.user_requested = {}
        for a in self.requirements:
            self.user_requested[a.name] = i
            i += 1

        self.provider = PyPIProvider(self.user_requested)
        self.reporter = BaseReporter()
        self.resolver = Resolver(self.provider, self.reporter)

    def resolve(self, max_round):
        return self.resolver.resolve(self.requirements, max_round)

    def get_project_from_pypi(self, requirement:Requirement):
        sql = "select {} from {} where name = '{}' order by version collate en_natural desc;".format(
            "name, version", "projects_metadata", canonicalize_name(requirement.name))
        q = database.execute_sql(sql)
        all_candidate = []
        for a in q:
            spec = requirement.specifier
            candidate = Candidate(a[0], a[1])
            if spec.contains(candidate.version, prereleases=True):
                all_candidate.append(candidate)    
        return all_candidate
def main():
    """Resolve requirements as project names on PyPI.
    The requirements are taken as command-line arguments
    and the resolution result will be printed to stdout.
    """
    if len(sys.argv) == 1:
        print("Usage:", sys.argv[0], "<PyPI project name(s)>")
        return
    # Things I want to resolve.
    reqs = sys.argv[1:]
    requirements = [Requirement(r) for r in reqs]
    i = 0
    user_requested = {}
    for a in requirements:
        user_requested[a.name] = i
        i += 1
    # Create the (reusable) resolver.
    provider = PyPIProvider(user_requested)
    reporter = BaseReporter()
    resolver = Resolver(provider, reporter)

    # Kick off the resolution process, and get the final result.
    print("Resolving", ", ".join(reqs))
    result = resolver.resolve(requirements)
    vpin, vedge = display_resolution(result)

    print("{}\n".format(vpin))
    print("{}\n".format(vedge))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()

