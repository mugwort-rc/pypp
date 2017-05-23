from __future__ import print_function

from ast import iter_fields
from collections import OrderedDict

import clang.cindex

from parser import AstNode


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



class Generator(NodeVisitor):
    def generate(self, node):
        raise NotImplementedError


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
                tmp.append(self.indent_base*indent + x)
        return tmp


class BoostPythonFunction(object):
    def __init__(self, name):
        self.name = name
        self.functions = []
        self.decls = CodeBlock([])
        self.overload_decls = []

    def add_function(self, node):
        assert node.spelling == self.name
        self.functions.append(node)
        # check overloads
        suffix = len(self.functions) - 1
        n = 0
        args = list(node.get_arguments())
        for i, arg in enumerate(args, 1):
            if len(list(arg.get_children())) > 0:
                break
            n = i
        if n == 0 or n == len(args):
            self.overload_decls.append("")
        else:
            self.decls.append("BOOST_PYTHON_FUNCTION_OVERLOADS({0}Overloads{1}, {0}, {2}, {3})".format(
                self.name,
                suffix,
                n,
                len(args),
            ))
            self.overload_decls.append("{0}Overloads{1}".format(self.name, suffix))

    def has_decl_code(self):
        return bool(self.decls)

    def decl_code(self):
        return self.decls

    def to_code_block(self):
        if len(self.functions) == 1:
            overloads = self.overloads(0)
            return CodeBlock([
                'boost::python::def("{0}", &{0}{1});'.format(self.name, overloads),
            ])
        else:
            result = CodeBlock([])
            for i, func in enumerate(self.functions):
                overloads = self.overloads(i)
                result.append(
                    'boost::python::def("{0}", static_cast<{1}(*)({2})>(&{0}){3});'.format(
                        self.name,
                        self.result_type(func),
                        ", ".join(self.arg_types(func)),
                        overloads,
                    )
                )
            return result

    def result_type(self, node):
        return node.result_type.spelling

    def arg_types(self, node):
        return [x.type.spelling for x in node.get_arguments()]

    def overloads(self, suffix):
        if self.overload_decls[suffix]:
            return ", {}()".format(self.overload_decls[suffix])
        return ""


class BoostPythonMethod(BoostPythonFunction):
    def to_code_block(self):
        class_name = self.functions[0].semantic_parent.spelling
        if len(self.functions) == 1:
            overloads = self.overloads(self.functions[0])
            return CodeBlock([
                '.def("{1}", &{0}::{1}{2})'.format(class_name, self.name, overloads),
            ])
        else:
            result = CodeBlock([])
            for i, func in enumerate(self.functions, 1):
                overloads = self.overloads(func, i)
                result.append(
                    '.def("{1}", static_cast<{2}({0}::*)({3}){4}>(&{0}::{1}){5});'.format(
                        class_name,
                        self.name,
                        self.result_type(func),
                        ", ".join(self.arg_types(func)),
                        " const" if func.is_const_method() else "",
                        overloads,
                    )
                )
            return result

    def overloads(self, node, suffix=None):
        class_name = node.semantic_parent.spelling
        if suffix is None:
            suffix = ""
        n = 0
        args = list(node.get_arguments())
        for i, arg in enumerate(args, 1):
            if len(list(arg.get_children())) > 0:
                break
            n = i
        if n == 0 or n == len(args):
            return ""
        else:
            self.decls.append("BOOST_PYTHON_MEMBER_FUNCTION_OVERLOADS({0}{1}Overloads{2}, {0}::{1}, {3}, {4})".format(
                class_name,
                self.name,
                suffix,
                n,
                len(args),
            ))
            return ", {}{}Overloads{}".format(class_name, self.name, suffix)


class BoostPythonClass(object):
    def __init__(self, name):
        self.name = name
        self.methods = OrderedDict()
        self.static_methods = []
        self.virtual_methods = []
        self.constructors = []
        self.noncopyable = False

    def add_method(self, node):
        assert node.semantic_parent.spelling == self.name
        # init if not added
        if node.spelling not in self.methods:
            self.methods[node.spelling] = BoostPythonMethod(node.spelling)
        self.methods[node.spelling].add_function(node)
        if node.is_static_method():
            if node.spelling not in self.static_methods:
                self.static_methods.append(node.spelling)
        elif node.is_virtual_method():
            self.virtual_methods.append(node)

    def set_noncopyable(self, b):
        self.noncopyable = b

    def has_virtual_method(self):
        for method in self.virtual_methods:
            if method.kind == clang.cindex.CursorKind.CXX_METHOD:
                return True
        return False

    def has_decl_code(self):
        if self.virtual_methods:
            return True
        for item in self.methods.values():
            if item.decls:
                return True
        return False

    def decl_code(self):
        result = CodeBlock([])
        result += self.class_wrapper()
        return result

    def to_code_block(self):
        code = CodeBlock([])
        defs = CodeBlock([])
        class_ = self.name
        if self.has_virtual_method():
            class_ = "{}Wrapper".format(self.name)
        noncopy = ""
        if self.noncopyable:
            noncopy = ", boost::noncopyable"
        constructor_count = len(self.constructors)
        if constructor_count == 0:
            code.append('boost::python::class_<{0}{2}>("{1}", boost::python::no_init)'.format(class_, self.name, noncopy))
        elif constructor_count == 1:
            init = self.init(self.constructors[0])
            code.append('boost::python::class_<{0}{3}>("{1}"{2})'.format(class_, self.name, init, noncopy))
        else:
            has_default = False
            inits = []
            for node in self.constructors:
                init = self.init(node)
                if init == "":
                    has_default = True
                    continue
                inits.append(init)
            if has_default:
                code.append('boost::python::class_<{0}{2}>("{1}")'.format(class_, self.name, noncopy))
            else:
                init = inits[0]
                inits = inits[1:]
                code.append('boost::python::class_<{0}{3}>("{1}", {2})'.format(class_, self.name, init, noncopy))
            for init in inits:
                defs.append('.def({})'.format(init))
        for item in self.methods.values():
            defs += item.to_code_block()
        if self.static_methods:
            for name in self.static_methods:
                defs.append('.staticmethod("{}")'.format(name))
        defs.append(";")
        code.append(defs)
        return code

    def init(self, node):
        args = list(node.get_arguments())
        if len(args) == 0:
            return ""
        tmp = []
        optional = []
        for arg in args:
            if len(list(arg.get_children())) == 0:
                tmp.append(arg.type.spelling)
            else:
                optional.append(arg.type.spelling)
        if optional:
            tmp.append("boost::python::optional<{}>".format(", ".join(optional)))
        return "boost::python::init<{}>()".format(", ".join(tmp))

    def class_wrapper(self):
        body = CodeBlock()
        for method in self.virtual_methods:
            if method.kind == clang.cindex.CursorKind.DESTRUCTOR:
                # special case for pure virtual destructor
                if method.is_pure_virtual_method():
                    body += CodeBlock([
                        "~{}Wrapper()".format(self.name),
                        "{}",
                    ])
                continue
            # CXX_METHOD
            result_type = method.result_type.spelling
            name = method.spelling
            const_type = ""
            if method.is_const_method():
                const_type = " const"

            # declaration
            args = []
            args_with_type = []
            for i, arg in enumerate(method.get_arguments()):
                args.append(arg.spelling)
                args_with_type.append("{} {}".format(arg.type.spelling, arg.spelling or "_{}".format(i)))
            tmp = CodeBlock([
                "{} {} ({}){} {{".format(
                    result_type,
                    name,
                    ", ".join(args_with_type),
                    const_type
                ),
            ])

            # body
            ret = ""
            if result_type != "void":
                ret = "return "
            if method.is_pure_virtual_method():
                tmp.append(CodeBlock([
                    '{}this->get_override("{}")({});'.format(ret, name, ", ".join(args))
                ]))
            else:
                auto = name
                while auto in args:
                    auto += "_"
                tmp.append(CodeBlock([
                    'if ( auto {0} = this->get_override("{1}") ) {{'.format(auto, name),
                    CodeBlock([
                        "{}{}({});".format(ret, auto, ", ".join(args)),
                    ]),
                    "} else {",
                    CodeBlock([
                        "{}{}::{}({});".format(ret, self.name, name, ", ".join(args)),
                    ]),
                    "}",
                ]))
            tmp.append("}")
            body += tmp

        return CodeBlock([
            "class {} :".format("{}Wrapper".format(self.name)),
            CodeBlock([
                "public {},".format(self.name),
                "public boost::python::wrapper<{}>".format(self.name),
            ]),
            "{",
            "public:",
            body,
            "};",
        ])


class BoostPythonGenerator(Generator):
    def __init__(self):
        self.classes = OrderedDict()
        self.functions = OrderedDict()

    def generate(self, node):
        assert isinstance(node, AstNode)
        self.visit(node)
        block = CodeBlock([])
        for value in self.classes.values():
            block += value.to_code_block()
        for value in self.functions.values():
            block += value.to_code_block()
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

    def decl_code(self):
        block = CodeBlock([])
        # overloads or virtual methods
        for value in self.classes.values():
            if value.has_decl_code():
                block += value.decl_code()
        # overloads
        for value in self.functions.values():
            if value.has_decl_code():
                block += value.decl_code()
        return "\n".join(block.to_code())

    def visit_TRANSLATION_UNIT(self, node):
        for child in node:
            self.visit(child)

    def visit_FUNCTION_DECL(self, node):
        function_name = node.ptr.spelling
        if function_name not in self.functions:
            self.functions[function_name] = BoostPythonFunction(function_name)
        self.functions[function_name].add_function(node.ptr)

    def visit_CLASS_DECL(self, node):
        name = node.ptr.spelling
        assert name not in self.classes
        self.classes[name] = BoostPythonClass(name)
        disable_copy_constructor = False
        disable_copy_operator = False
        for child in node:
            if child.ptr.kind == clang.cindex.CursorKind.DESTRUCTOR:
                continue
            if child.ptr.access_specifier == clang.cindex.AccessSpecifier.PRIVATE:
                # check lvalue constructor
                if child.ptr.kind == clang.cindex.CursorKind.CONSTRUCTOR:
                    args = list(child.ptr.get_arguments())
                    if len(args) == 1 and args[0].type.kind == clang.cindex.TypeKind.LVALUEREFERENCE:
                        disable_copy_constructor = True
                # check lvalue operator
                elif child.ptr.spelling == "operator=":
                    args = list(child.ptr.get_arguments())
                    if len(args) == 1 and args[0].type.kind == clang.cindex.TypeKind.LVALUEREFERENCE:
                        disable_copy_operator = True
            if child.ptr.access_specifier != clang.cindex.AccessSpecifier.PUBLIC:
                continue
            elif child.ptr.kind == clang.cindex.CursorKind.CXX_ACCESS_SPEC_DECL:
                continue
            self.visit(child)

        self.classes[name].set_noncopyable(disable_copy_constructor and disable_copy_operator)

    def visit_CXX_METHOD(self, node):
        ret = CodeBlock()
        class_name = node.ptr.semantic_parent.spelling
        assert class_name in self.classes
        self.classes[class_name].add_method(node.ptr)
