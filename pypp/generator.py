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
    def generate(self, node):
        assert isinstance(node, AstNode)
        return "\n".join(self.visit(node).to_code())

    def visit_TRANSLATION_UNIT(self, node):
        return CodeBlock(self.visit(x) for x in node)

    def visit_FUNCTION_DECL(self, node):
        function_name = node.ptr.spelling
        decl = 'boost::python::def("{0}", &{0});'.format(function_name)
        return CodeBlock([decl])

    def visit_CLASS_DECL(self, node):
        name = node.ptr.spelling
        if self.has_constructor(node):
            ret = CodeBlock([
                'boost::python::class_<{0}>("{0}")'.format(name),
            ])
        else:
            ret = CodeBlock([
                'boost::python::class_<{0}>("{0}", boost::python::no_init)'.format(name),
            ])
        for child in node:
            if child.ptr.access_specifier.name != "PUBLIC":
                continue
            elif child.ptr.kind.name == "CXX_ACCESS_SPEC_DECL":
                continue
            ret.append(self.visit(child))
        ret.append(CodeBlock([";"]))
        return ret

    def has_constructor(self, node):
        for child in node:
            if child.ptr.access_specifier.name != "PUBLIC":
                continue
            if child.ptr.kind.name == "CONSTRUCTOR":
                return True
        return False

    def visit_CXX_METHOD(self, node):
        ret = CodeBlock()
        class_name = node.parent.ptr.spelling
        name = node.ptr.spelling
        ret.append('.def("{1}", &{0}::{1})'.format(class_name, name))
        if node.ptr.is_static_method():
            ret.append('.staticmethod("{}")'.format(name))
        return ret
