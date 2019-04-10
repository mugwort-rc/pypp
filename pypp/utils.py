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


RE_VECTOR = re.compile(r"^(const\s+)?std::vector\<(?P<T>.+?), std::allocator\<(?P=T)\s*\>\s*\>(\s*&)?")
RE_STD_BASIC = re.compile(r"std(?:::__cxx11)?::basic_(\w+)\<(char|wchar_t)\>")
def std_basic_repl(m):
    w = "w" if m.group(2) == "wchar_t" else ""
    return "std::" + w + m.group(1)

STD_SIZE_T = "unsigned long"  # libclang 32bit

def type_simplify(type_str):
    type_str = RE_STD_BASIC.sub(std_basic_repl, type_str)
    if "std::vector" in type_str:
        m = RE_VECTOR.match(type_str)
        if m:
            # std::vector default allocator
            const = m.group(1) or ""
            ref = m.group(3) or ""
            return const + "std::vector<{}>".format(m.group(2)) + ref
    return type_str

def canonical_type(type):
    spelling = type.spelling
    simple = type_simplify(type.get_canonical().spelling)
    if "std::size_t" in spelling:
        simple = simple.replace(STD_SIZE_T, "std::size_t")
    return simple
