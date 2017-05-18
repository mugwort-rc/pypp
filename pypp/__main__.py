#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import argparse
import sys
import os

from pypp.parser import AstParser
from pypp.generator import BoostPythonGenerator
from pypp.utils import name2snake

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("input")

    args = parser.parse_args(argv)

    ast_parser = AstParser()
    node = ast_parser.parse(args.input)
    generator = BoostPythonGenerator()

    generated = generator.generate(node)

    print("// generate by pypp")
    print("// original source code:", args.input)

    if generator.has_decl_code():
        print("")
        print(generator.decl_code())
        print("\n")

    print("void init_{}() {{\n{}\n}}".format(
            name2snake(args.input),
            generated,
    ))

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
