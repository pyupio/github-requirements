# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
import json
from tqdm import tqdm
from io import StringIO
from collections import Counter
from pkg_resources import parse_version
from pkg_resources._vendor.packaging.specifiers import SpecifierSet
from safety.util import read_requirements as safety_read_requirements
from safety.safety import check as safety_check


def parse_line(line):
    """
    Parses a requirements line
    """
    from pkg_resources import parse_requirements as _parse_requirements
    if line.startswith('-e') or line.startswith('http://') or line.startswith('https://'):
        if "#egg=" in line:
            line = line.split("#egg=")[-1]
    return _parse_requirements(line)


def read_requirements(fh):
    """
    Reads requirements from a file like object.
    :param fh: file like object to read from
    :return: generator
    """

    def iter_lines(fh, lineno=0):
        for line in fh.readlines()[lineno:]:
            yield line

    for num, line in enumerate(iter_lines(fh)):
        line = line.strip()
        if not line:
            # skip empty lines
            continue
        if line.startswith('#') or \
            line.startswith('-i') or \
            line.startswith('--index-url') or \
            line.startswith('--extra-index-url') or \
            line.startswith('-f') or line.startswith('--find-links') or \
            line.startswith('--no-index') or line.startswith('--allow-external') or \
            line.startswith('--allow-unverified') or line.startswith('-Z') or \
            line.startswith('--always-unzip'):
            # skip unsupported lines
            continue
        elif line.startswith('-r') or line.startswith('--requirement'):
            # got a referenced file here, pass
            pass
        else:
            try:
                parseable_line = line
                # multiline requirements are not parseable
                if "\\" in line:
                    parseable_line = line.replace("\\", "")
                    for next_line in iter_lines(fh, num + 1):
                        parseable_line += next_line.strip().replace("\\", "")
                        line += "\n" + next_line
                        if "\\" in next_line:
                            continue
                        break
                req, = parse_line(parseable_line)
                yield req
            except ValueError:
                continue


def create_index():
    """
    reads raw `data.json` and creates a package/spec index in `index.json`
    {
        "django":{
            "": 12,
            "==1.2": 13,
            ">=1.2": 14,
            ...
        }
    }
    """
    requirements = {}

    with open('data.json') as f:
        for line in tqdm(f.readlines()):
            item = json.loads(line)
            if 'C_content' in item:
                reqs = read_requirements(
                    fh=StringIO(item['C_content']),
                )
                for req in reqs:
                    if req.key not in requirements:
                        requirements[req.key] = {}
                    specs = ",".join(["{}{}".format(i,k) for i,k in req.specs])
                    if specs not in requirements[req.key]:
                        requirements[req.key][specs] = 0
                    requirements[req.key][specs] += 1

    with open('index.json', 'w') as f:
        f.write(json.dumps(requirements, indent=2))


def popular_packages():
    counter = Counter()
    with open('index.json') as f:
        data = json.loads(f.read())
        for pkg, specs in data.items():
            counter.update({pkg: sum([n for _, n in specs.items()])})
    return counter


def package_data(name):
    """
    Creates detailed package data, see django.json
    :param name: package name
    """
    with open('index.json') as f:
        item = json.loads(f.read()).get(name, {})

    data = {
         "count": sum([n for _, n in item.items()]),
         "specs": {
            "unpinned": 0,
            "range": 0,
            "pinned": 0,
            "compatible": 0,
            "unknown": 0
         },
         "releases": {
             "unknown": 0
         },
         "major_releases": {},
         "security": {
             "secure": 0,
             "insecure": 0,
             "unknown": 0
         }
    }

    # calculate specs
    for spec, count in item.items():
        if spec == "":
            data['specs']['unpinned'] += count
        elif spec.startswith("=="):
            data['specs']['pinned'] += count
        elif spec.startswith("~="):
            data['specs']['compatible'] += count
        else:
            is_range_spec = False
            for range_spec in ('<', ">", "!="):
                if spec.startswith(range_spec):
                    data['specs']['range'] += count
                    is_range_spec = True
                    break
            if not is_range_spec:
                data['specs']['unknown'] += count

    # releases
    import requests
    r = requests.get(f"https://pypi.python.org/pypi/{name}/json")
    releases = sorted(r.json()["releases"].keys(), key=lambda v: parse_version(v), reverse=True)

    for spec, count in item.items():
        if not spec.startswith("=="):
            data['releases']['unknown'] += count
            continue
        spec_set = SpecifierSet(spec)
        candidates = []
        for release in releases:
            if spec_set.contains(release, prereleases=True):
                candidates.append(release)
        candidates = sorted(candidates, key=lambda v: parse_version(v), reverse=True)
        if len(candidates) > 0:
            key = str(candidates[0])
            if key not in data['releases']:
                data['releases'][key] = 0
            data['releases'][key] += count
        else:
            data['releases']['unknown'] += count

    from collections import OrderedDict
    data['releases'] = OrderedDict(sorted(data['releases'].items(), key=lambda v: parse_version(v[0]), reverse=True))

    # major releases
    for release, count in data['releases'].items():
        major_release = ".".join(release.split(".")[:2])
        if major_release not in data["major_releases"]:
            data["major_releases"][major_release] = 0
        data["major_releases"][major_release] += count
    data['major_releases'] = OrderedDict(sorted(data['major_releases'].items(), key=lambda v: parse_version(v[0]), reverse=True))

    # security
    for release, count in data['releases'].items():
        if release == 'unknown':
            data['security']['unknown'] = count
            continue
        vulns = safety_check(
            packages=safety_read_requirements(StringIO(f"{name}=={release}")),
            key="",
            db_mirror="",
            cached=True,
            ignore_ids=[]
        )
        if len(vulns) > 0:
            data['security']['insecure'] += count
        else:
            data['security']['secure'] += count

    return data