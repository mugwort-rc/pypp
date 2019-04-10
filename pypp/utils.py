import re

import clang.cindex

from .constants import (
    UNARY_OPERATOR_MAP,
    BINARY_OPERATOR_MAP,
    OTHER_OPERATOR_MAP,
    PYTHON_RESERVED,
)

def name2snake(name):
    ret = re.sub(r"\W+", "_", name)
    if ret and ret.startswith("_"):
        ret = ret[1:]
    return ret


def is_unary_operator(node):
    if node.spelling not in UNARY_OPERATOR_MAP:
        return False
    args = list(node.get_arguments())
    if len(args) > 0:
        return False
    return True

def is_binary_operator(node):
    if node.spelling in UNARY_OPERATOR_MAP:
        if is_unary_operator(node):
            return False
    if node.spelling not in BINARY_OPERATOR_MAP:
        return False
    return True

def is_other_operator(node):
    if node.spelling not in OTHER_OPERATOR_MAP:
        return False
    return True

def is_convertible_operator(node):
    return is_convertible_operator_name(node.spelling)

def is_convertible_operator_name(name):
    return name in BINARY_OPERATOR_MAP or name in UNARY_OPERATOR_MAP or name in OTHER_OPERATOR_MAP


def check_reserved(word):
    if word in PYTHON_RESERVED:
        return "{}_".format(word)
    return word

def is_copy_method(func):
    args = list(func.get_arguments())
    return len(args) == 1 and args[0].type.kind == clang.cindex.TypeKind.LVALUEREFERENCE


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
