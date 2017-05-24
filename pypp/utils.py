import re

def name2snake(name):
    ret = re.sub(r"\W+", "_", name)
    if ret and ret.startswith("_"):
        ret = ret[1:]
    return ret


class CodeBlock(list):

    indent_base = " " * 4

    def to_code(self, indent=0):
        tmp = []
        for x in self:
            if x is None:
                print("debug: skip block")
            elif isinstance(x, CodeBlock):
                tmp.extend(x.to_code(indent+1))
            else:
                if x:
                    tmp.append(self.indent_base*indent + x)
                # empty case
                else:
                    tmp.append(x)
        return tmp
