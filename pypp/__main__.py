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
from pypp.generator import BoostPythonGenerator
from pypp.utils import name2snake

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--template", default="template.cpp")
    parser.add_argument("--headers", nargs="+", default=[])
    parser.add_argument("--include-path", "-I", nargs="+", default=[])
    parser.add_argument("--defines", "-D", nargs="+", default=[])
    parser.add_argument("--install-defvisitor", default=False, action="store_true")
    parser.add_argument("--enable-protected", default=False, action="store_true")
    parser.add_argument("--after-shell", default=False, action="store_true")

    args = parser.parse_args(argv)

    env = Environment(
        loader=PackageLoader("pypp", "templates"),
    )

    template = env.get_template(args.template)

    ast_parser = AstParser(headers=args.headers, include_path=args.include_path, defines=args.defines)
    node = ast_parser.parse(args.input)
    generator = BoostPythonGenerator(
        enable_defvisitor=args.install_defvisitor,
        enable_protected=args.enable_protected,
    )

    generated = generator.generate(node)
    ctx = {
        "input": args.input,
        "snake_input": name2snake(args.input),
        "class_forward_declarations": generator.class_forward_declarations,
        "install_defvisitor": args.install_defvisitor,
        "def_visitors": generator.def_visitors(),
        "has_decls": generator.has_decl_code(),
        "decl_code": generator.decl_code(),
        "generated": generated,
    }
    print(template.render(ctx))

    if args.after_shell:
        code.interact(local=locals())

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
