from __future__ import print_function

from ast import iter_fields

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


class BoostPythonGenerator(Generator):
    def __init__(self):
        self.decls = CodeBlock()

    def generate(self, node):
        assert isinstance(node, AstNode)
        return "\n".join(self.visit(node).to_code())

    def has_decl_code(self):
        return bool(self.decls)

    def decl_code(self):
        return "\n".join(self.decls.to_code(indent=-1))

    def visit_TRANSLATION_UNIT(self, node):
        return CodeBlock(self.visit(x) for x in node)

    def visit_FUNCTION_DECL(self, node):
        function_name = node.ptr.spelling
        decl = 'boost::python::def("{0}", &{0});'.format(function_name)
        return CodeBlock([decl])

    def visit_CLASS_DECL(self, node):
        name = node.ptr.spelling
        class_ = name
        if self.has_virtual_method(node):
            class_ = "{}Wrapper".format(name)
        if self.has_constructor(node):
            ret = CodeBlock([
                'boost::python::class_<{}>("{}")'.format(class_, name),
            ])
        else:
            ret = CodeBlock([
                'boost::python::class_<{}>("{}", boost::python::no_init)'.format(class_, name),
            ])
        virtual_methods = []
        for child in node:
            if child.ptr.kind.name == "DESTRUCTOR":
                continue
            if child.ptr.is_virtual_method():
                virtual_methods.append(child)
            if child.ptr.access_specifier.name != "PUBLIC":
                continue
            elif child.ptr.kind.name == "CXX_ACCESS_SPEC_DECL":
                continue
            ret.append(self.visit(child))

        if virtual_methods:
            self.create_class_wrapper(name, class_, virtual_methods)

        ret.append(CodeBlock([";"]))
        return ret

    def has_constructor(self, node):
        for child in node:
            if child.ptr.access_specifier.name != "PUBLIC":
                continue
            if child.ptr.kind.name == "CONSTRUCTOR":
                return True
        return False

    def has_virtual_method(self, node):
        for child in node:
            if child.ptr.is_virtual_method():
                return True
        return False

    def create_class_wrapper(self, base, class_, methods):
        body = CodeBlock()
        for method in methods:
            result_type = method.ptr.result_type.spelling
            name = method.ptr.spelling
            const_type = ""
            if method.ptr.is_const_method():
                const_type = " const"

            args = []
            args_with_type = []
            for arg in method.ptr.get_arguments():
                args.append(arg.spelling)
                args_with_type.append("{} {}".format(arg.type.spelling, arg.spelling))
            tmp = CodeBlock([
                "{} {} ({}){} {{".format(
                    result_type,
                    name,
                    ", ".join(args_with_type),
                    const_type
                ),
            ])

            ret = ""
            if result_type != "void":
                ret = "return "
            if method.ptr.is_pure_virtual_method():
                tmp.append(CodeBlock([
                    '{}this->get_override("{}")({});'.format(ret, name, ", ".join(args))
                ]))
            else:
                tmp.append(CodeBlock([
                    'if ( auto {0} = this->get_override("{0}") ) {{'.format(name),
                    CodeBlock([
                        "{}{}({});".format(ret, name, ", ".join(args)),
                    ]),
                    "} else {",
                    CodeBlock([
                        "{}{}::{}({});".format(ret, base, name, ", ".join(args)),
                    ]),
                    "}",
                ]))
            tmp.append("}")
            body.append(tmp)
        self.decls.append(CodeBlock([
            "class {} : public {}".format(class_, base),
            "{",
            "public:",
            body,
            "};",
        ]))

    def visit_CXX_METHOD(self, node):
        ret = CodeBlock()
        class_name = node.parent.ptr.spelling
        name = node.ptr.spelling
        if node.ptr.is_pure_virtual_method():
            ret.append('.def("{1}", boost::python::pure_virtual(&{0}::{1}))'.format(class_name, name))
        else:
            ret.append('.def("{1}", &{0}::{1})'.format(class_name, name))
        if node.ptr.is_static_method():
            ret.append('.staticmethod("{}")'.format(name))
        return ret
