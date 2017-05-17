import re

def name2snake(name):
    ret = re.sub(r"\W+", "_", name)
    if ret and ret.startswith("_"):
        ret = ret[1:]
    return ret
