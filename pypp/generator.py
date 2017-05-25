from __future__ import print_function

from ast import iter_fields
from collections import OrderedDict

import clang.cindex

from .parser import AstNode
from .utils import CodeBlock


CPP_OPERATORS = [
    "operator()",
    #"operator \w+()",  # TODO: cast operator
    "operator->",
    "operator[]",
    "operator++",  # TODO: ++(int)
    "operator--",  # TODO: --(int)
    "operator new",
    "operator delete",
    "operator new[]",
    "operator delete[]",
    "operator~",
    "operator!",
    "operator+",  # TODO: +(const T &rhs)
    "operator-",  # TODO: -(const T &rhs)
    "operator&",  # TODO: &(const T &rhs)
    "operator*",  # TODO: *(const T &rhs)
    "operator->*",
    "operator/",
    "operator<<",
    "operator>>",
    "operator<",
    "operator<=",
    "operator>",
    "operator>=",
    "operator==",
    "operator!=",
    "operator^",
    "operator|",
    "operator&&",
    "operator||",
    "operator=",
    "operator*=",
    "operator/=",
    "operator%=",
    "operator+=",
    "operator-=",
    "operator<<=",
    "operator>>=",
    "operator&=",
    "operator^=",
    "operator|=",
    "operator,",
]

NOT_DEFAULT_ARG_KINDS = [
    clang.cindex.CursorKind.TYPE_REF,
    clang.cindex.CursorKind.TEMPLATE_REF,
    clang.cindex.CursorKind.NAMESPACE_REF,
]


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


class BoostPythonFunction(object):
    def __init__(self, name):
        self.name = name
        self.functions = []
        self.decls = CodeBlock([])
        self.overload_decls = []
        self.value_policies = []

    def add_function(self, node):
        assert node.spelling == self.name
        self.functions.append(node)

        self.register_overloads(node)
        self.register_return_value_policy(node)

    def has_decl_code(self):
        return bool(self.decls)

    def decl_code(self):
        return self.decls

    def to_code_block(self):
        if len(self.functions) == 1:
            option = self.option(0)
            result = CodeBlock([
                'boost::python::def("{func}", &{func}{opt});'.format(
                    func=self.name,
                    opt=option
                ),
            ])
        else:
            result = CodeBlock([])
            for i, func in enumerate(self.functions):
                option = self.option(i)
                result.append(
                    'boost::python::def("{func}", static_cast<{rtype}(*)({args})>(&{func}){opt});'.format(
                        func=self.name,
                        rtype=self.result_type(func),
                        args=", ".join(self.arg_types(func)),
                        opt=option,
                    )
                )
            result
        if self.name in CPP_OPERATORS:
            return CodeBlock.wrap_inline_comment(result)
        return result

    def result_type(self, node):
        return node.result_type.spelling

    @classmethod
    def arg_types(cls, node):
        return [x.type.spelling for x in node.get_arguments()]

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

        self.decls.append("{pp}({func}Overloads{suffix}, {func}, {min}, {max})".format(
            pp=self.boost_python_overloads(node),
            func=self.name,
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

    def option(self, suffix):
        overload = self.overload_decls[suffix]
        policy = self.value_policies[suffix]
        if overload or policy:
            if overload and policy:
                return ", {}[{}]".format(overload, policy)
            return ", {}".format(overload or policy)
        return ""

    def register_return_value_policy(self, node):
        result_type = self.result_type(node)
        if result_type.endswith("*") or result_type.endswith("&"):
            # TODO: other types
            if result_type.endswith("*"):
                policy = "boost::python::return_opaque_pointer"
            elif result_type.endswith("&"):
                # TODO: internal reference case
                if result_type.startswith("const"):
                    policy = "boost::python::copy_const_reference"
                else:
                    policy = "boost::python::copy_non_const_reference"
            self.value_policies.append("boost::python::return_value_policy<{}>()".format(policy))
        else:
            self.value_policies.append("")


class BoostPythonMethod(BoostPythonFunction):
    def to_code_block(self):
        class_name = self.functions[0].semantic_parent.spelling
        if len(self.functions) == 1:
            func = self.functions[0]
            option = self.option(0)
            decl = "&{cls}::{func}".format(cls=class_name, func=self.name)
            if func.is_pure_virtual_method():
                decl = "boost::python::pure_virtual({})".format(decl)
            result = CodeBlock([
                '.def("{func}", {decl}{opt})'.format(
                    func=self.name,
                    decl=decl,
                    opt=option
                ),
            ])
        else:
            result = CodeBlock([])
            for i, func in enumerate(self.functions):
                option = self.option(i)
                cast_scope = ""
                if not func.is_static_method():
                    cast_scope = "{}::".format(class_name)
                decl = "static_cast<{rtype}({scope}*)({args}){const}>(&{cls}::{func})".format(
                    cls=class_name,
                    func=self.name,
                    rtype=self.result_type(func),
                    args=", ".join(self.arg_types(func)),
                    const=" const" if func.is_const_method() else "",
                    scope=cast_scope,
                )
                if func.is_pure_virtual_method():
                    decl = "boost::python::pure_virtual({})".format(decl)
                result.append(
                    '.def("{func}", {decl}{opt})'.format(
                        func=self.name,
                        decl=decl,
                        opt=option,
                    )
                )
        if self.name in CPP_OPERATORS:
            return CodeBlock.wrap_inline_comment(result)
        return result

    def boost_python_overloads(self, node):
        if node.is_static_method():
            return "BOOST_PYTHON_FUNCTION_OVERLOADS"
        return "BOOST_PYTHON_MEMBER_FUNCTION_OVERLOADS"

    def register_overloads(self, node):
        class_name = node.semantic_parent.spelling
        suffix, minarg, maxarg = self._overload_info(node)

        if minarg == 0 or minarg == maxarg:
            # no overload
            self.overload_decls.append("")
            return

        self.decls.append("{base}({cls}{func}Overloads{suffix}, {cls}::{func}, {min}, {max})".format(
            base=self.boost_python_overloads(node),
            cls=class_name,
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


class BoostPythonClass(object):
    def __init__(self, name, enable_defvisitor=False, enable_scope=False):
        self.name = name
        self.methods = OrderedDict()
        self.static_methods = []
        self.virtual_methods = []
        self.constructors = []
        self.noncopyable = False
        self.enable_defvisitor = enable_defvisitor
        self.enable_scope = enable_scope

    def add_method(self, node):
        # skip implement part
        if node.lexical_parent.kind != clang.cindex.CursorKind.CLASS_DECL:
            return
        assert node.semantic_parent.spelling == self.name
        if node.kind == clang.cindex.CursorKind.CONSTRUCTOR:
            # skip move constructor
            if BoostPythonFunction.arg_types(node) == ["{} &&".format(self.name)]:
                return
            self.constructors.append(node)
            return
        elif node.kind == clang.cindex.CursorKind.DESTRUCTOR:
            assert node.is_pure_virtual_method()
            self.virtual_methods.append(node)
            self.set_noncopyable(True)
            return
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
        self.noncopyable = self.noncopyable or b

    def set_enable_scope(self, enable):
        self.enable_scope = enable

    def has_virtual_method(self):
        return bool(self.virtual_methods)

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
        for item in self.methods.values():
            if item.decls:
                result += item.decls
        return result

    def to_code_block(self):
        code = CodeBlock([])
        defs = CodeBlock([])
        assignment = ""
        if self.enable_scope:
            assignment = "auto boost_python_{} = ".format(self.name)
        class_ = self.name
        if self.has_virtual_method():
            class_ = "{}Wrapper".format(self.name)
        noncopy = ""
        if self.noncopyable:
            noncopy = ", boost::noncopyable"
        constructor_count = len(self.constructors)
        if constructor_count == 0:
            code.append(
            '{0}boost::python::class_<{1}{3}>("{2}", boost::python::no_init)'.format(
                assignment,
                class_,
                self.name,
                noncopy
                )
            )
        elif constructor_count == 1:
            init = self.init(self.constructors[0])
            if init:
                init = ", {}".format(init)
            code.append('{0}boost::python::class_<{1}{4}>("{2}"{3})'.format(
                assignment,
                class_,
                self.name,
                init,
                noncopy)
            )
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
                code.append('{0}boost::python::class_<{1}{3}>("{2}")'.format(
                    assignment,
                    class_,
                    self.name,
                    noncopy)
                )
            else:
                init = inits[0]
                inits = inits[1:]
                code.append('{0}boost::python::class_<{1}{4}>("{2}", {3})'.format(
                    assignment,
                    class_,
                    self.name,
                    init,
                    noncopy)
                )
            for init in inits:
                defs.append('.def({})'.format(init))
        if self.enable_defvisitor:
            defs.append(".def({}DefVisitor())".format(self.name))
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
            if not BoostPythonFunction.has_default_value(arg):
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
                args.append(arg.spelling or "_{}".format(i))
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


class BoostPythonEnum(object):
    def __init__(self, name, scope=None):
        self.name = name
        self.scope = scope
        self.values = []

    def add_value(self, node):
        self.values.append(node.spelling)

    def to_code_block(self):
        values = ['.value("{0}", &{0})'.format(x) for x in self.values]
        block = CodeBlock([
            'boost::python::enum_<{0}>("{0}")'.format(self.name),
            CodeBlock(values + [
                ".export_values()",
                ";",
            ]),
        ])
        if self.scope:
            block = CodeBlock([
                "{",
                CodeBlock([
                    "boost::python::scope scope = boost_python_{0};".format(self.scope),
                ]),
                block,
                "}",
            ])
        return block


class BoostPythonGenerator(Generator):
    def __init__(self, enable_defvisitor=False):
        self.classes = OrderedDict()
        self.functions = OrderedDict()
        self.enums = OrderedDict()
        self.enable_defvisitor = enable_defvisitor

    def generate(self, node):
        assert isinstance(node, AstNode)
        self.visit(node)
        block = CodeBlock([])
        for value in self.classes.values():
            block += value.to_code_block()
        for value in self.functions.values():
            block += value.to_code_block()
        for value in self.enums.values():
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

    def def_visitors(self):
        result = []
        for class_ in self.classes.values():
            if class_.enable_defvisitor:
                result.append("{}DefVisitor".format(class_.name))
        return result

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
        self.classes[name] = BoostPythonClass(name, enable_defvisitor=self.enable_defvisitor)
        pure_virtual_destructor = False
        disable_copy_constructor = False
        disable_copy_operator = False
        i = -1
        for i, child in enumerate(node):
            if child.ptr.access_specifier == clang.cindex.AccessSpecifier.INVALID:
                i = -1
                continue
            if child.ptr.kind == clang.cindex.CursorKind.DESTRUCTOR:
                if not child.ptr.is_pure_virtual_method():
                    continue
                pure_virtual_destructor = True
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

        self.classes[name].set_noncopyable(
            pure_virtual_destructor
            or
            (disable_copy_constructor and disable_copy_operator)
        )
        # remove forward declaration
        if i < 0:
            del self.classes[name]

    def visit_CONSTRUCTOR(self, node):
        class_name = node.ptr.semantic_parent.spelling
        assert class_name in self.classes
        self.classes[class_name].add_method(node.ptr)

    def visit_DESTRUCTOR(self, node):
        if not node.ptr.is_pure_virtual_method():
            return
        class_name = node.ptr.semantic_parent.spelling
        assert class_name in self.classes
        self.classes[class_name].add_method(node.ptr)

    def visit_CXX_METHOD(self, node):
        class_name = node.ptr.semantic_parent.spelling
        assert class_name in self.classes
        self.classes[class_name].add_method(node.ptr)

    def visit_ENUM_DECL(self, node, name=None):
        # unnamed special case
        if name is None:
            if not node.ptr.spelling:
                return
            name = node.ptr.spelling
        scope = None
        if node.ptr.semantic_parent.kind == clang.cindex.CursorKind.CLASS_DECL:
            scope = node.ptr.semantic_parent.spelling
            self.classes[scope].set_enable_scope(True)
        self.enums[name] = BoostPythonEnum(name, scope=scope)
        for child in node:
            assert child.ptr.kind == clang.cindex.CursorKind.ENUM_CONSTANT_DECL
            self.enums[name].add_value(child.ptr)

    def visit_TYPEDEF_DECL(self, node):
        for child in node:
            if child.ptr.kind == clang.cindex.CursorKind.ENUM_DECL:
                self.visit_ENUM_DECL(child, name=node.ptr.spelling)
