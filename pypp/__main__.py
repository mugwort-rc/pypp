#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import argparse
import sys
import os
import code
import readline

from pypp.parser import AstParser
from pypp.generator import BoostPythonGenerator
from pypp.utils import name2snake

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--include-path", "-I", nargs="+", default=[])
    parser.add_argument("--defines", "-D", nargs="+", default=[])
    parser.add_argument("--install-defvisitor", default=False, action="store_true")
    parser.add_argument("--after-shell", default=False, action="store_true")

    args = parser.parse_args(argv)

    ast_parser = AstParser(include_path=args.include_path, defines=args.defines)
    node = ast_parser.parse(args.input)
    generator = BoostPythonGenerator(
        enable_defvisitor=args.install_defvisitor,
    )

    generated = generator.generate(node)

    print("// generate by pypp")
    print("// original source code:", args.input)

    print("")
    print("#include <boost/python.hpp>")
    print('#include "{}"'.format(args.input))
    print("")
    if args.install_defvisitor:
        print("")
        for name in generator.def_visitors():
            print('#include "{}.hpp"'.format(name))
        print("")

    if generator.has_decl_code():
        print("")
        print(generator.decl_code())
        print("\n")

    print("void init_{}() {{\n{}\n}}".format(
            name2snake(args.input),
            generated,
    ))

    if args.after_shell:
        code.interact(local=locals())

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
