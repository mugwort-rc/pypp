#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import argparse
import sys
import os
import code
import readline

from jinja2 import Environment, PackageLoader

from pypp.parser import AstParser
from pypp.generator import Generator
from pypp.option import GeneratorType
from pypp.option import GeneratorOption
from pypp.utils import name2snake

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--headers", nargs="+", default=[])
    parser.add_argument("--name", default=None)
    parser.add_argument("--strip-path", default=None)
    parser.add_argument("--include-path", "-I", nargs="+", default=[])
    parser.add_argument("--defines", "-D", nargs="+", default=[])
    parser.add_argument("--install-common-h", default=False, action="store_true")
    parser.add_argument("--common-h", default="common.h", type=str)
    parser.add_argument("--install-defvisitor", default=False, action="store_true")
    parser.add_argument("--enable-protected", default=False, action="store_true")
    parser.add_argument("--after-shell", default=False, action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--silence-errors", action="store_true", default=False)
    parser.add_argument("--generate-boost", action="store_true")
    parser.add_argument("--generate-embind", action="store_true")
    parser.add_argument("--allow-all", action="store_true")
    # for linux
    parser.add_argument("--using-gcc-version", default="7")

    args = parser.parse_args(argv)

    env = Environment(
        loader=PackageLoader("pypp", "templates"),
    )

    boost = args.generate_boost
    embind = args.generate_embind
    if boost and embind:
        print("can't enable both boost and embind", file=sys.stderr)
        return 1
    if boost:
        template = env.get_template("boost.cpp")
    elif embind:
        template = env.get_template("embind.cpp")
    else:
        template = env.get_template("pybind11.cpp")

    include_path = args.include_path
    if os.name == "posix":
        include_path.append("/usr/lib/gcc/x86_64-linux-gnu/{}/include/".format(args.using_gcc_version))

    ast_parser = AstParser(headers=args.headers, include_path=include_path, defines=args.defines, allow_all=args.allow_all)
    node = ast_parser.parse(args.input)

    if args.verbose or not args.silence_errors:
        if args.verbose or ast_parser.errors:
            print("/*")
            ast_parser.dump_errors(sys.stderr)
            print(" */")

    generator = Generator(
        enable_defvisitor=args.install_defvisitor,
        enable_protected=args.enable_protected,
    )

    type = GeneratorType.Pybind11
    if boost:
        type = GeneratorType.Boost
    elif embind:
        type = GeneratorType.Embind
    option = GeneratorOption(type=type)

    generated = generator.generate(node, option)

    if args.strip_path:
        if args.input.startswith(args.strip_path):
            args.input = args.input[len(args.strip_path):]
    ctx = {
        "input": args.input,
        "init_name": name2snake(args.input) if args.name is None else args.name,
        "class_forward_declarations": generator.class_forward_declarations,
        "install_common_h": args.install_common_h,
        "common_h": args.common_h,
        "install_defvisitor": args.install_defvisitor,
        "def_visitors": generator.def_visitors(),
        "has_decls": generator.has_decl_code(),
        "decl_code": generator.decl_code(option),
        "generated": generated,
    }
    print(template.render(ctx))

    if args.after_shell:
        code.interact(local=locals())

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
