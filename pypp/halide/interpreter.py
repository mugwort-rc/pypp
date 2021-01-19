from ast import iter_fields
import re
from collections import OrderedDict

import clang.cindex

from ..constants import (
    UNARY_OPERATOR_MAP,
    BINARY_OPERATOR_MAP,
    OTHER_OPERATOR_MAP,
    NOT_DEFAULT_ARG_KINDS,
)
from ..abstract import NodeVisitor
from ..parser import AstNode
from .. import utils


class Function:
    def __init__(self, name, ast=None):
        self.name = name
        self.ast = ast
        self.vars = OrderedDict()
        self.defs = OrderedDict()
        self.source_cache = {}

    def add_decl(self, name, depends, ast=None):
        self.vars[name] = depends
        self.defs[name] = ast

    def get_depends(self, name):
        if name not in self.vars:
            return []
        return self.vars[name].depends()

    def get_recursive_depends(self, name, ctx=None):
        if ctx is None:
            ctx = []
        result = []
        depends = self.get_depends(name)
        result.extend(depends)
        for child in depends:
            if child in ctx:
                continue
            result += self.get_recursive_depends(child, result)
        return result

    def get_var_definitions(self, name):
        depends = self.get_recursive_depends(name)
        proceed = set()
        result = []
        for dep in depends:
            if dep in proceed:
                continue
            result.append(self.get_source(self.defs[dep]))
            proceed.add(dep)
        return reversed(result)

    def get_source(self, node):
        filename = node.ptr.location.file.name
        if filename not in self.source_cache:
            with open(filename) as fp:
                source = fp.read()
            self.source_cache[filename] = source
        source = self.source_cache[filename]
        extent = node.ptr.extent
        return source[extent.start.offset:extent.end.offset]

    def dump_var_definitions(self, name, fileobj=None):
        kwargs = {}
        if fileobj is not None:
            kwargs["file"] = fileobj
        print("\n".join(self.get_var_definitions(name)), **kwargs)


class Nullptr:
    def __init__(self):
        pass

    def as_cpp(self):
        return "nullptr"

    def as_python(self):
        return "None"

    def depends(self):
        return []


class Parenthesis:
    def __init__(self, child):
        self.child = child

    def as_cpp(self):
        return "({})".format(self.child.as_cpp())

    def as_python(self):
        return "({})".format(self.child.as_python())

    def depends(self):
        return self.child.depends()


class CStyleCastExpr(Parenthesis):
    def __init__(self, type, child):
        super().__init__(child)
        self.type = type


class InitializerListExpr:
    def __init__(self, exprs):
        self.exprs = exprs

    def depends(self):
        result = []
        for child in self.exprs:
            result += child.depends()
        return result


class DeclRef:
    def __init__(self, name):
        self.name = name

    def as_cpp(self):
        return self.name

    def as_python(self):
        return self.name

    def depends(self):
        return [self.name]


class IntegerLiteral:
    def __init__(self, child):
        self.child = child

    def as_cpp(self):
        # TODO:
        return "0/*TODO*/"

    def as_python(self):
        return "0"  # TODO: read from child.ptr.extent

    def depends(self):
        return []


class StringLiteral:
    def __init__(self, value):
        self.value = value

    def depends(self):
        return []


class BinaryOperator:
    def __init__(self, op, lhs, rhs):
        self.op = op
        self.lhs = lhs
        self.rhs = rhs

    def as_cpp(self):
        # TODO:
        return "{} {} {}".format(self.lhs.as_cpp(), self.op, self.rhs.as_cpp())

    def as_python(self):
        return "{} {} {}".format(self.lhs.as_python(), self.op, self.rhs.as_python())

    def depends(self):
        return self.lhs.depends() + self.rhs.depends()


class CallExpr:
    def __init__(self, args):
        self.args = args

    def depends(self):
        return []
        # TODO: evaluate _halide_buffer_get_min(...) etc...
        """
        result = []
        for arg in self.args:
            if arg is None:
                continue
            result += arg.depends()
        return result
        """


class Interpreter(NodeVisitor):
    def __init__(self):
        super().__init__()
        self.functions = OrderedDict()
        self.function_queue = []  # queue
        self.unnamed_hint = {}
        self.in_var_decl = False

    def evaluate(self, node):
        assert isinstance(node, AstNode)
        for child in self.find_halide_generated_block(node):
            self.visit(child)

    def find_halide_generated_block(self, node):
        for child in node:
            if child.ptr.kind != clang.cindex.CursorKind.UNEXPOSED_DECL:
                continue
            for grand_child in child:
                if grand_child.ptr.kind != clang.cindex.CursorKind.FUNCTION_DECL:
                    continue
                if grand_child.ptr.spelling.startswith("halide_"):
                    continue
                args = [x.type.spelling for x in grand_child.ptr.get_arguments()]
                if "struct halide_buffer_t *" not in args:
                    continue
                yield grand_child

    def full_namespace(self, ptr, name=None):
        if ptr.hash in self.unnamed_hint:
            return self.unnamed_hint[ptr.hash]
        if name is None:
            if ptr.spelling == "":
                # unnamed typedef special case
                return []
            name = ptr.spelling
        return self.full_namespace(ptr.semantic_parent) + [name]

    def scope_id(self, ptr, name=None):
        return ".".join(self.full_namespace(ptr, name=name))

    def full_declaration(self, ptr):
        return "::".join(self.full_namespace(ptr))

    def namespaces(self, ptr):
        return self.full_namespace(ptr.semantic_parent)

    def visit_TRANSLATION_UNIT(self, node):
        for child in node:
            self.visit(child)

    def visit_UNEXPOSED_DECL(self, node):
        # extern "C" {}
        for child in node:
            self.visit(child)

    def visit_FUNCTION_DECL(self, node):
        function_name = node.ptr.spelling
        func_id = self.build_func_id(node)
        assert func_id not in self.functions
        func = Function(function_name)
        self.functions[func_id] = func
        self.function_queue.append(func)
        for child in node:
            if child.ptr.kind == clang.cindex.CursorKind.PARM_DECL:
                continue
            self.visit(child)
        self.function_queue.pop()

    def build_func_id(self, node):
        name = node.ptr.spelling
        args = [x.type.spelling for x in node.ptr.get_arguments()]
        return "{}({})".format(name, ", ".join(args))

    def visit_DECL_STMT(self, node):
        for child in node:
            self.visit(child)

    def visit_VAR_DECL(self, node):
        name = node.ptr.spelling
        assert len(self.function_queue) > 0
        func = self.function_queue[-1]
        self.in_var_decl = True
        children = list(node)
        count = len(children)
        child = None
        if count == 1:
            child = children[0]
        elif count == 2:
            # skip type of var : children[0]
            child = children[1]
        elif count == 3:
            # array
            child = children[2]
        else:
            assert False, "{!r}".format([x.ptr.kind for x in children])
        tree = self.visit(child)
        func.add_decl(name, tree, node)
        self.in_var_decl = False

    def visit_UNEXPOSED_EXPR(self, node):
        children = list(node)
        assert len(children) == 1
        return self.visit(children[0])

    def visit_CXX_NULL_PTR_LITERAL_EXPR(self, node):
        return Nullptr()

    def visit_PAREN_EXPR(self, node):
        children = list(node)
        assert len(children) == 1
        child = self.visit(children[0])
        return Parenthesis(child)

    def visit_CSTYLE_CAST_EXPR(self, node):
        children = list(node)
        count = len(children)
        if count == 1:
            child = self.visit(children[0])
            return CStyleCastExpr(None, child)
        elif count == 2:
            type = children[0].ptr.type.spelling
            child = self.visit(children[1])
            return CStyleCastExpr(type, child)
        else:
            assert False, "{!r}".format([x.ptr.kind] for x in children)

    def visit_INIT_LIST_EXPR(self, node):
        exprs = []
        for child in node:
            exprs.append(self.visit(child))
        return InitializerListExpr(exprs)

    def visit_DECL_REF_EXPR(self, node):
        return DeclRef(node.ptr.spelling)

    def visit_INTEGER_LITERAL(self, node):
        return IntegerLiteral(node)

    def visit_STRING_LITERAL(self, node):
        return StringLiteral(node)

    def visit_BINARY_OPERATOR(self, node):
        children = list(node)
        assert len(children) == 2
        lhs = self.visit(children[0])
        rhs = self.visit(children[1])
        op = "TODO_BINOP"
        return BinaryOperator(op, lhs, rhs)

    def visit_CALL_EXPR(self, node):
        args = []
        for child in node:
            ret = self.visit(child)
            if ret is not None:
                args.append(ret)
            else:
                # TODO: warning
                args.append(None)
        return CallExpr(args)

    def visit_COMPOUND_STMT(self, node):
        for child in node:
            self.visit(child)

    def visit_IF_STMT(self, node):
        children = list(node)
        assert len(children) == 2
        # skip if condition : node[0]
        self.visit(children[1])

    def visit_FOR_STMT(self, node):
        children = list(node)
        count = len(children)
        # TODO: C++11 range-based-for
        for child in children:
            self.visit(child)

    # unused nodes

    def visit_RETURN_STMT(self, node):
        pass

    def visit_NAMESPACE(self, node):
        pass

    def visit_CLASS_DECL(self, node, name=None):
        pass

    def visit_STRUCT_DECL(self, node, name=None):
        pass

    def visit_CONSTRUCTOR(self, node):
        pass

    def visit_DESTRUCTOR(self, node):
        pass

    def visit_CXX_METHOD(self, node):
        pass

    def visit_FIELD_DECL(self, node):
        pass

    def visit_ENUM_DECL(self, node, name=None):
        pass

    def visit_TYPEDEF_DECL(self, node):
        """
        for typedef with unnamed definition

        ENUM_DECL :
            ENUM_CONSTANT_DECL : Item1
            ENUM_CONSTANT_DECL : Item2
        TYPEDEF : EnumName
            ENUM_DECL :
                ENUM_CONSTANT_DECL : Item1
                ENUM_CONSTANT_DECL : Item2
        """
        for child in node:
            if child.ptr.spelling:
                continue
            self.unnamed_hint[child.ptr.hash] = self.full_namespace(node.ptr)
            if child.ptr.kind == clang.cindex.CursorKind.ENUM_DECL:
                self.visit_ENUM_DECL(child, name=node.ptr.spelling)
            elif child.ptr.kind == clang.cindex.CursorKind.CLASS_DECL:
                self.visit_CLASS_DECL(child, name=node.ptr.spelling)
            elif child.ptr.kind == clang.cindex.CursorKind.STRUCT_DECL:
                self.visit_STRUCT_DECL(child, name=node.ptr.spelling)
