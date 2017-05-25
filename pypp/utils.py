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

    @classmethod
    def wrap_inline_comment(cls, block):
        result = CodeBlock([])
        for line in block:
            if isinstance(line, CodeBlock):
                result.append(cls.wrap_inline_comment(line))
            else:
                result.append("//"+line)
        return result

    @classmethod
    def wrap_block_comment(cls, block):
        if cls.check_block_comment(block):
            log.warning("WARNING: wrap block comment in the block comment")
        return CodeBlock(["/*"]) + block + CodeBlock(["*/"])

    @classmethod
    def check_block_comment(cls, block):
        for line in block:
            if isinstnce(line, str):
                if line == "*/":
                    return True
            else:
                if cls.check_block_comment(line):
                    return True
        return False
