# -*- coding: utf-8 -*-

import clang.cindex

from . import base

from ..constants import CPP_OPERATORS
from ..generator import Function
from .. import utils


class EmbindOptionBuilder(base.OptionBuilder):
    def make(self, entity):
        if entity.has_pointer_arg_ret():
            # TODO: other types
            return "emscripten::allow_raw_pointers()"
        return ""


class EmbindFunctionBuilder(base.FunctionBuilder):
    def make(self, func):
        if len(func.functions) == 1:
            option = func.option(0, self.option)
            result = utils.CodeBlock([
                'emscripten::function("{pyfunc}", &{func}{opt});'.format(
                    pyfunc=utils.check_reserved(func.name),
                    func=func.cpp_name,
                    opt=option
                ),
            ])
            if func.has_function_pointer(func.functions[0]):
                # TODO: wrap callable object
                result = utils.CodeBlock.wrap_inline_comment(result)
        else:
            result = utils.CodeBlock([])
            for i, func_cur in enumerate(func.functions):
                option = func.option(i, self.option)
                def_ = 'emscripten::function("{pyfunc}", static_cast<{rtype}(*)({args})>(&{func}){opt});'.format(
                    pyfunc=utils.check_reserved(func.name),
                    func=func.cpp_name,
                    rtype=func.result_type(func_cur),
                    args=", ".join(func.arg_types(func_cur)),
                    opt=option,
                )
                if func.has_function_pointer(func_cur):
                    # TODO: wrap callable object
                    def_ = "//{}".format(def_)
                result.append(def_)
            result
        if func.name in CPP_OPERATORS:
            # global operator overload is not supported
            return utils.CodeBlock.wrap_inline_comment(result)
        return result


class EmbindMethodBuilder(base.MethodBuilder):
    def make(self, method, class_name=None):
        if class_name is None:
            class_name = method.functions[0].semantic_parent.type.spelling
        if len(method.functions) == 1:
            func_cur = method.functions[0]
            option = method.option(0, self.option)
            decl = "&{cls}::{func}".format(cls=class_name, func=method.name)
            pyname = method.pyname()
            # operator special case
            if utils.is_convertible_operator_name(method.name):
                pyname = method.resolve_operator_map(func_cur)
            result = utils.CodeBlock([
                '.function("{func}", {decl}{opt})'.format(
                    func=pyname,
                    decl=decl,
                    opt=option
                ),
            ])
            if method.has_function_pointer(func_cur):
                # TODO: wrap callable object
                result = utils.CodeBlock.wrap_inline_comment(result)
        else:
            result = utils.CodeBlock([])
            for i, func_cur in enumerate(method.functions):
                option = method.option(i, self.option)
                cast_scope = ""
                if not func_cur.is_static_method():
                    cast_scope = "{}::".format(class_name)
                decl = "static_cast<{rtype}({scope}*)({args}){const}>(&{cls}::{func})".format(
                    cls=class_name,
                    func=utils.check_reserved(method.name),
                    rtype=method.result_type(func_cur),
                    args=", ".join(method.arg_types(func_cur)),
                    const=" const" if func_cur.is_const_method() else "",
                    scope=cast_scope,
                )
                pyname = method.pyname()
                # operator special case
                if utils.is_convertible_operator_name(method.name):
                    pyname = method.resolve_operator_map(func_cur)
                # mixed static member case
                if func_cur.is_static_method() and method.is_static_mixed():
                    pyname += "Static"
                def_ = '.function{static}("{func}", {decl}{opt})'.format(
                    static="_static" if func_cur.is_static_method() else "",
                    func=pyname,
                    decl=decl,
                    opt=option,
                )
                if method.has_function_pointer(func_cur):
                    # TODO: wrap callable object
                    def_ = "//{}".format(def_)
                result.append(def_)
        if method.name in CPP_OPERATORS:
            if not utils.is_convertible_operator_name(method.name):
                # unsupported operator
                return utils.CodeBlock.wrap_inline_comment(result)
        return result


class EmbindClassBuilder(base.ClassBuilder):
    def make(self, clss):
        code = utils.CodeBlock([])
        defs = utils.CodeBlock([])
        assignment = ""
        if clss.enable_scope:
            assignment = "auto emscripten_{} = ".format(utils.name2snake(clss.decl))
        class_ = clss.decl
        if clss.has_wrapper():
            class_ = "{}, Py{}".format(clss.decl, clss.name)
        bases = ""
        held = ""
        # TODO: held class option
        noncopy = ""
        opt = held + noncopy
        constructors = list(filter(lambda x: x.access_specifier == clang.cindex.AccessSpecifier.PUBLIC, clss.constructors))
        def is_not_copy(x):
            return Function.arg_types(x) != ["const {} &".format(clss.decl)]
        constructors = list(filter(is_not_copy, constructors))
        constructor_count = len(constructors)
        if clss.has_pure_virtual_method():
            constructor_count = 0
        code.append(
        '{assign}emscripten::class_<{cls}{opt}>(scope, "{pycls}"{bases})'.format(
            assign=assignment,
            cls=class_,
            pycls=utils.check_reserved(clss.name),
            bases=bases,
            opt=opt,
            )
        )
        # constructor
        has_default = False
        inits = []
        for node in constructors:
            init = self.init(node)
            if init == "":
                has_default = True
                continue
            inits.append(init)
        for init in inits:
            defs.append('.constructor<{}>()'.format(init))
        # def_visitor
        if clss.enable_defvisitor:
            defs.append(".function({}())".format(clss.defvisitor_name))
        for item in clss.methods.values():
            defs += item.to_code_block(self.option)
        for prop, node in clss.properties.items():
            defs.append('.property("{0}", &{1}::{0})'.format(prop, class_))
        if clss.enable_protected:
            protected_static_methods = []
            for name, item in clss.protected_methods.items():
                defs += item.to_code_block(self.option, class_name=class_)
                if item.has_static_method():
                    protected_static_methods.append(name)
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
            if not Function.has_default_value(arg):
                tmp.append(arg.type.spelling)
            else:
                optional.append(arg.type.spelling)
        if optional:
            tmp.append("{}".format(", ".join(optional)))
        return ", ".join(tmp)

    def class_wrapper(self, class_):
        body = utils.CodeBlock()
        return body


class EmbindEnumBuilder(base.EnumBuilder):
    def make(self, enum):
        scope = ""
        value_scope = ""
        pybind11_scope = "scope"
        if enum.scope:
            scope = value_scope = enum.scope + "::"
            pybind11_scope = "emscripten_" + utils.name2snake(enum.scope)
        if enum.scoped_enum:
            value_scope += enum.name + "::"
        values = ['.value("{}", {})'.format(utils.check_reserved(x), value_scope+x) for x in enum.values]
        block = utils.CodeBlock([
            'pybind11::enum_<{enum}>({scope}, "{name}")'.format(
                scope=pybind11_scope,
                enum=scope + enum.name,
                name=utils.check_reserved(enum.name),
            ),
            utils.CodeBlock(values + ([";"] if enum.scoped_enum else [".export_values()", ";"])),
        ])
        return block
