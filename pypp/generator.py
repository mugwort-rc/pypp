from __future__ import print_function

from ast import iter_fields
import re
from collections import OrderedDict

import clang.cindex

from .constants import (
    UNARY_OPERATOR_MAP,
    BINARY_OPERATOR_MAP,
    OTHER_OPERATOR_MAP,
    NOT_DEFAULT_ARG_KINDS,
)
from .parser import AstNode
from . import utils


FUNCTION_POINTER_RE = re.compile(r"\w+\s*\(\*\)\([^\)]*\)")


class NodeVisitor(object):
    def visit(self, node):
        """Visit a node."""
        if not isinstance(node, AstNode):
            return super(NodeVisitor, self).visit(node)
        method = 'visit_' + node.ptr.kind.name
        #print("// [debug]:", method)
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        """Called if no explicit visitor function exists for a node."""
        for field, value in iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, AstNode):
                        self.visit(item)
            elif isinstance(value, AstNode):
                self.visit(value)
#class NodeVisitor


class Generator(NodeVisitor):
    def generate(self, node):
        raise NotImplementedError
#class Generator


class FunctionEntity(object):
    def __init__(self, definition, node):
        self.definition = definition
        self.func = node

    def result_type(self):
        return Function.result_type(self.func)

    def arg_types(self):
        return Function.arg_types(self.func)

    def has_function_pointer(self):
        return Function.has_function_pointer(self.func)

    def has_pointer_arg_ret(self):
        return Function.has_pointer_arg_ret(self.func)


class Function(object):
    def __init__(self, name, namespaces=[]):
        self.name = name
        self.namespaces = namespaces
        self.functions = []
        self.decls = utils.CodeBlock([])
        self.overload_decls = []
        self.return_values = []

    def add_function(self, node):
        assert node.spelling == self.name
        self.functions.append(node)

        self.register_overloads(node)
        self.register_return_value(node)

    def has_decl_code(self):
        return bool(self.decls)

    def decl_code(self, opt):
        return self.decls

    def to_code_block(self, opt):
        return opt.function.make(self)

    @classmethod
    def is_std_type(cls, type):
        return type.spelling.startswith("std::") or re.match(r"^const\s+std::", type.spelling)

    @classmethod
    def result_type(cls, node):
        return utils.canonical_type(node.result_type)

    @classmethod
    def arg_types(cls, node):
        args = []
        for arg in node.get_arguments():
            args.append(utils.canonical_type(arg.type))
        return args

    @classmethod
    def has_function_pointer(cls, node):
        if cls.is_function_pointer(node.result_type):
            return True
        return any([cls.is_function_pointer(x.type) for x in node.get_arguments()])

    @classmethod
    def is_function_pointer(cls, type):
        assert isinstance(type, clang.cindex.Type)
        ctype = type.get_canonical()
        if ctype.kind == clang.cindex.TypeKind.POINTER:
            if FUNCTION_POINTER_RE.match(ctype.spelling):
                return True
        return False

    @classmethod
    def has_pointer_arg_ret(cls, node):
        if "*" in cls.result_type(node):
            return True
        for type in cls.arg_types(node):
            if "*" in type:
                return True
        return False

    @classmethod
    def has_default_value(cls, arg):
        childs = [x for x in arg.get_children() if x.kind not in NOT_DEFAULT_ARG_KINDS]
        return len(childs) > 0

    def boost_python_overloads(self, node):
        return "BOOST_PYTHON_FUNCTION_OVERLOADS"

    def register_overloads(self, node):
        suffix, minarg, maxarg = self._overload_info(node)

        if minarg == 0 or minarg == maxarg:
            # no overload
            self.overload_decls.append("")
            return

        self.decls.append("{pp}({func}Overloads{suffix}, {decl}, {min}, {max})".format(
            pp=self.boost_python_overloads(node),
            func=self.name,
            decl=self.cpp_name,
            suffix=suffix,
            min=minarg,
            max=maxarg,
        ))
        # TODO: arg names; XXXOverloads(boost::python::args("x", "y", "z"))
        self.overload_decls.append("{func}Overloads{suffix}()".format(
            func=self.name,
            suffix=suffix,
        ))

    def _overload_info(self, node):
        suffix = len(self.functions) - 1
        n = 0
        args = list(node.get_arguments())
        for i, arg in enumerate(args, 1):
            if self.has_default_value(arg):
                break
            n = i
        return suffix, n, len(args)

    def option(self, suffix, opt):
        overload = self.overload_decls[suffix]
        policy = opt.option.make(FunctionEntity(self, self.functions[suffix]))
        if overload or policy:
            if overload and policy:
                return ", {}[{}]".format(overload, policy)
            return ", {}".format(overload or policy)
        return ""

    def register_return_value(self, node):
        self.return_values.append(self.result_type(node))

    @property
    def cpp_name(self):
        return "::".join(self.namespaces + [self.name])
#class Function


class Method(Function):
    def __init__(self, parent, name, namespaces=[]):
        super().__init__(name, namespaces=namespaces)
        self.parent = parent

    def to_code_block(self, opt, class_name=None):
        return opt.method.make(self, class_name)

    def boost_python_overloads(self, node):
        if node.is_static_method():
            return "BOOST_PYTHON_FUNCTION_OVERLOADS"
        return "BOOST_PYTHON_MEMBER_FUNCTION_OVERLOADS"

    def register_overloads(self, node):
        class_name = node.semantic_parent.spelling
        class_decl = self.parent.full_declaration
        suffix, minarg, maxarg = self._overload_info(node)

        if minarg == 0 or minarg == maxarg:
            # no overload
            self.overload_decls.append("")
            return

        self.decls.append("{base}({cls}{func}Overloads{suffix}, {cls_decl}::{func}, {min}, {max})".format(
            base=self.boost_python_overloads(node),
            cls=class_name,
            cls_decl=class_decl,
            func=self.name,
            suffix=suffix,
            min=minarg,
            max=maxarg,
        ))
        # TODO: arg names; XXXOverloads(boost::python::args("x", "y", "z"))
        self.overload_decls.append("{cls}{func}Overloads{suffix}()".format(
            cls=class_name,
            func=self.name,
            suffix=suffix,
        ))

    def pyname(self):
        if self.name in BINARY_OPERATOR_MAP and self.name not in UNARY_OPERATOR_MAP:
            return BINARY_OPERATOR_MAP[self.name]
        return utils.check_reserved(self.name)

    @classmethod
    def resolve_operator_map(cls, node):
        assert utils.is_convertible_operator_name(node.spelling)
        if utils.is_binary_operator(node):
            return BINARY_OPERATOR_MAP[node.spelling]
        elif utils.is_unary_operator(node):
            return UNARY_OPERATOR_MAP[node.spelling]
        elif utils.is_other_operator(node):
            return OTHER_OPERATOR_MAP[node.spelling]

    def is_escape_all(self):
        return all(map(self.has_function_pointer, self.functions))

    def has_static_method(self):
        return any(map(lambda x: x.is_static_method(), self.functions))

    def method_type_count(self):
        member = 0
        static = 0
        for func in self.functions:
            if func.is_static_method():
                static += 1
            else:
                member += 1
        return member, static

    def is_static_mixed(self):
        member, static = self.method_type_count()
        return static > 0 and member > 0
#class Method


class ProtectedMethod(Method):
    def pyname(self):
        if not self.name.startswith("_"):
            return utils.check_reserved("_" + self.name)
        return super(ProtectedMethod, self).pyname()
#class ProtectedMethod


class Class(object):
    def __init__(self, name, decl=None, full_declaration=None, enable_defvisitor=False, enable_protected=False, enable_scope=False, namespaces=[]):
        self.name = name
        self.decl = decl if decl else name
        self.full_declaration = full_declaration or name
        self.bases = []
        self.methods = OrderedDict()
        self.protected_methods = OrderedDict()
        self.properties = OrderedDict()
        self.static_methods = []
        self.virtual_methods = []
        self.constructors = []
        self.private_methods = []
        self.dropped_methods = []
        self.noncopyable = False
        self.enable_defvisitor = enable_defvisitor
        self.enable_protected = enable_protected
        self.enable_scope = enable_scope

    @property
    def defvisitor_name(self):
        return self.decl.replace("::", "_") + "DefVisitor"

    def add_bases(self, node):
        assert node.kind == clang.cindex.CursorKind.CXX_BASE_SPECIFIER
        self.bases.append(node)

    def add_method(self, node):
        # skip implement part
        if not self.is_declaration_part(node):
            return
        assert node.semantic_parent.spelling == self.name
        if node.kind == clang.cindex.CursorKind.CONSTRUCTOR:
            # skip move constructor
            if Function.arg_types(node) == ["{} &&".format(self.decl)]:
                self.dropped_methods.append(node)
                return
            self.constructors.append(node)
            return
        elif node.kind == clang.cindex.CursorKind.DESTRUCTOR:
            assert node.is_pure_virtual_method()
            self.virtual_methods.append(node)
            self.set_noncopyable(True)
            return
        if node.access_specifier == clang.cindex.AccessSpecifier.PRIVATE:
            self.private_methods.append(node)
        elif node.access_specifier == clang.cindex.AccessSpecifier.PROTECTED:
            # init if it is not added
            if node.spelling not in self.protected_methods:
                self.protected_methods[node.spelling] = ProtectedMethod(self, node.spelling)
            self.protected_methods[node.spelling].add_function(node)
        elif node.access_specifier == clang.cindex.AccessSpecifier.PUBLIC:
            # init if it is not added
            if node.spelling not in self.methods:
                self.methods[node.spelling] = Method(self, node.spelling)
            self.methods[node.spelling].add_function(node)
            if node.is_static_method():
                if node.spelling not in self.static_methods:
                    self.static_methods.append(node.spelling)
        if node.is_virtual_method():
            self.virtual_methods.append(node)

    def add_property(self, node):
        # skip implement part
        if not self.is_declaration_part(node):
            return
        semantic_parent_name = node.semantic_parent.spelling
        assert semantic_parent_name == self.name or semantic_parent_name == ""
        if node.access_specifier == clang.cindex.AccessSpecifier.PUBLIC:
            # init if it is not added
            if node.spelling not in self.properties:
                self.properties[node.spelling] = node

    def set_noncopyable(self, b):
        self.noncopyable = self.noncopyable or b

    def set_enable_scope(self, enable):
        self.enable_scope = enable

    @property
    def copy_disabled(self):
        # TODO: check boost::noncopyable in bases
        flag = 0b00
        for init in self.constructors:
            if utils.is_copy_method(init):
                if init.access_specifier != clang.cindex.AccessSpecifier.PRIVATE:
                    flag |= 0b10
                    break
        for node in self.private_methods:
            if utils.is_copy_method(node):
                flag |= 0b01
                break
        return flag == 0b11

    @classmethod
    def is_declaration_part(cls, node):
        return node.lexical_parent.kind in [clang.cindex.CursorKind.CLASS_DECL,
                                            clang.cindex.CursorKind.STRUCT_DECL]

    def has_virtual_method(self):
        return bool(self.virtual_methods)

    def has_pure_virtual_method(self):
        return any([x.is_pure_virtual_method() for x in self.virtual_methods])

    def has_protected_method(self):
        if not self.enable_protected:
            return False
        return bool(self.protected_methods)

    def has_wrapper(self):
        return self.has_virtual_method() or self.has_protected_method()

    def has_decl_code(self):
        if self.virtual_methods:
            return True
        if self.enable_protected and self.protected_methods:
            return True
        for item in self.methods.values():
            if item.decls:
                return True
        return False

    def decl_code(self, opt):
        result = utils.CodeBlock([])
        # wrapper
        if self.has_wrapper():
            result += opt.class_.class_wrapper(self)
        # function overloads
        for item in self.methods.values():
            if item.decls:
                result += item.decls
        return result

    def to_code_block(self, opt):
        return opt.class_.make(self)
#class Class


class Enum(object):
    def __init__(self, name, scoped_enum=False, scope=None):
        self.name = name
        self.scoped_enum = scoped_enum
        self.scope = scope
        self.values = []

    def add_value(self, node):
        self.values.append(node.spelling)

    def to_code_block(self, opt):
        return opt.enum.make(self)
#class Enum


class Generator(Generator):
    def __init__(self, enable_defvisitor=False, enable_protected=False):
        self.classes = OrderedDict()
        self.class_forward_declarations = []
        self.functions = OrderedDict()
        self.enums = OrderedDict()
        self.enable_defvisitor = enable_defvisitor
        self.enable_protected = enable_protected
        self.unnamed_hint = {}

    def generate(self, node, opt):
        assert isinstance(node, AstNode)
        self.visit(node)
        block = utils.CodeBlock([])
        for value in self.classes.values():
            block += value.to_code_block(opt)
        for value in self.functions.values():
            block += value.to_code_block(opt)
        for value in self.enums.values():
            block += value.to_code_block(opt)
        return "\n".join(block.to_code(indent=1))

    def has_decl_code(self):
        # overloads or virtual methods
        for value in self.classes.values():
            if value.has_decl_code():
                return True
        # overloads
        for value in self.functions.values():
            if value.has_decl_code():
                return True
        return False

    def decl_code(self, opt):
        block = utils.CodeBlock([])
        # overloads or virtual methods
        for value in self.classes.values():
            if value.has_decl_code():
                block += value.decl_code(opt)
        # overloads
        for value in self.functions.values():
            if value.has_decl_code():
                block += value.decl_code(opt)
        return "\n".join(block.to_code())

    def def_visitors(self):
        result = []
        for class_ in self.classes.values():
            if class_.enable_defvisitor:
                result.append(class_.defvisitor_name)
        return result

    def full_namespace(self, ptr, name=None):
        if ptr.hash in self.unnamed_hint:
            return self.unnamed_hint[ptr.hash]
        if ptr is None or ptr.kind in [clang.cindex.CursorKind.TRANSLATION_UNIT, clang.cindex.CursorKind.UNEXPOSED_DECL]:
            return []
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

    def visit_NAMESPACE(self, node):
        for child in node:
            self.visit(child)

    def visit_FUNCTION_DECL(self, node):
        function_name = node.ptr.spelling
        func_id = self.scope_id(node.ptr)
        if func_id not in self.functions:
            self.functions[func_id] = Function(function_name, namespaces=self.namespaces(node.ptr))
        self.functions[func_id].add_function(node.ptr)

    def visit_CLASS_DECL(self, node, name=None):
        self._class_decl(node, name=name)

    def visit_STRUCT_DECL(self, node, name=None):
        self._class_decl(node, name=name, struct=True)

    def _class_decl(self, node, name=None, struct=False):
        # unnamed special case
        if name is None:
            # pure class/struct definition
            if not node.ptr.spelling:
                # typedef with unnamed definition
                # STRUCT_DECL :  <- now!
                #     FIELD_DECL : ...
                #     ...
                # TYPEDEF_DECL : typedef_name
                #     STRUCT_DECL : <- name=typedef_name (see visit_TYPEDEF_DECL)
                return
            # pure named class/struct definition
            name = node.ptr.spelling
        class_id = self.scope_id(node.ptr, name=name)
        assert class_id not in self.classes, "{!r} already stored {!r}".format(class_id, self.classes.keys())
        self.classes[class_id] = Class(
            name,
            decl=node.ptr.type.spelling,
            full_declaration=self.full_declaration(node.ptr),
            enable_defvisitor=self.enable_defvisitor,
            enable_protected=self.enable_protected
        )
        pure_virtual_destructor = False
        disable_copy_constructor = False
        disable_copy_operator = False
        i = -1
        for i, child in enumerate(node):
            if child.ptr.access_specifier == clang.cindex.AccessSpecifier.INVALID:
                i = -1
                continue

            if child.ptr.kind == clang.cindex.CursorKind.CXX_ACCESS_SPEC_DECL:
                continue
            elif child.ptr.kind == clang.cindex.CursorKind.CXX_BASE_SPECIFIER:
                self.classes[class_id].add_bases(child.ptr)
                continue
            elif child.ptr.kind == clang.cindex.CursorKind.DESTRUCTOR:
                if not child.ptr.is_pure_virtual_method():
                    continue
                pure_virtual_destructor = True
            if child.ptr.access_specifier == clang.cindex.AccessSpecifier.PRIVATE:
                # check lvalue constructor
                if child.ptr.kind == clang.cindex.CursorKind.CONSTRUCTOR:
                    if utils.is_copy_method(child.ptr):
                        disable_copy_constructor = True
                # check lvalue operator
                elif child.ptr.spelling == "operator=":
                    if utils.is_copy_method(child.ptr):
                        disable_copy_operator = True
            if child.ptr.access_specifier == clang.cindex.AccessSpecifier.PRIVATE:
                continue
            self.visit(child)

        # check force noncopyable
        self.classes[class_id].set_noncopyable(
            # has pure virtual method case
            pure_virtual_destructor
            or
            # ignored copy method case
            (disable_copy_constructor and disable_copy_operator)
        )
        # remove forward declaration
        if i < 0:
            del self.classes[class_id]
            self.class_forward_declarations.append(name)
        else:
            if class_id in self.class_forward_declarations:
                self.class_forward_declarations.remove(class_id)

    def visit_CONSTRUCTOR(self, node):
        class_name = node.ptr.semantic_parent.spelling
        class_id = self.scope_id(node.ptr.semantic_parent)
        assert class_id in self.classes
        self.classes[class_id].add_method(node.ptr)

    def visit_DESTRUCTOR(self, node):
        if not node.ptr.is_pure_virtual_method():
            return
        class_name = node.ptr.semantic_parent.spelling
        class_id = self.scope_id(node.ptr.semantic_parent)
        assert class_id in self.classes
        self.classes[class_id].add_method(node.ptr)

    def visit_CXX_METHOD(self, node):
        class_name = node.ptr.semantic_parent.spelling
        class_id = self.scope_id(node.ptr.semantic_parent)
        if class_id not in self.classes:
            # outside decl
            return
        self.classes[class_id].add_method(node.ptr)

    def visit_FIELD_DECL(self, node):
        class_name = node.ptr.semantic_parent.spelling
        class_id = self.scope_id(node.ptr.semantic_parent)
        assert class_id in self.classes, "{!r} not in {!r}".format(class_id, self.classes.keys())
        self.classes[class_id].add_property(node.ptr)

    def visit_ENUM_DECL(self, node, name=None):
        # unnamed special case
        if name is None:
            if not node.ptr.spelling:
                return
            name = node.ptr.spelling
        scope = None
        if node.ptr.semantic_parent.kind == clang.cindex.CursorKind.CLASS_DECL:
            scope = self.scope_id(node.ptr.semantic_parent)
            self.classes[scope].set_enable_scope(True)
        # TODO: namespace wrapped case; e.g. namespace ns { enum en { a, b, c }; }
        self.enums[name] = Enum(name, scoped_enum=node.ptr.is_scoped_enum(), scope="::".join(self.namespaces(node.ptr)))
        for child in node:
            if child.ptr.kind == clang.cindex.CursorKind.UNEXPOSED_ATTR:
                continue
            assert child.ptr.kind == clang.cindex.CursorKind.ENUM_CONSTANT_DECL, "{!r}".format(child.ptr.kind)
            self.enums[name].add_value(child.ptr)

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
#class Generator
