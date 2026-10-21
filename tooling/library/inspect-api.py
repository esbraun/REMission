"""Bounded selected-release API inspection; not statistical acceptance."""
import importlib.metadata as md
import inspect
import json
import platform
import urllib.request

import arviz
import arviz_base
import arviz_stats
import coba.evaluators
import pymc
import pytensor
import stochtree
from packaging.version import Version

print(platform.platform(), platform.python_version(), pytensor.config.floatX, pytensor.config.cxx)
print("PRE_RELEASES", [(d.metadata["Name"], d.version) for d in md.distributions() if Version(d.version).is_prerelease])
for distribution in md.distributions():
    if Version(distribution.version).is_prerelease:
        data = json.load(urllib.request.urlopen(f"https://pypi.org/pypi/{distribution.metadata['Name']}/json"))
        stable = max(Version(v) for v, files in data["releases"].items() if files and not Version(v).is_prerelease)
        print("STABLE_CANDIDATE", distribution.metadata["Name"], str(stable))
print("SAMPLE", inspect.signature(pymc.sample))
print("ARVIZ", [n for n in dir(arviz) if not n.startswith("_")])
print("ARVIZ_STATS", [n for n in dir(arviz_stats) if not n.startswith("_")])
print("ARVIZ_BASE", [n for n in dir(arviz_base) if not n.startswith("_")])
print("BCF_SAMPLE", inspect.signature(stochtree.BCFModel.sample))
print("BCF_PREDICT", inspect.signature(stochtree.BCFModel.predict))
print("COBA_EVALUATORS", [n for n in dir(coba.evaluators) if not n.startswith("_")])
print("DISTRIBUTIONS", json.dumps({d.metadata["Name"]: d.version for d in md.distributions()}, sort_keys=True))
