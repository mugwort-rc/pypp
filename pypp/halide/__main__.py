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
from pypp.halide.interpreter import Interpreter

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("vars", nargs="+")
    parser.add_argument("--headers", nargs="+", default=[])
    parser.add_argument("--include-path", "-I", nargs="+", default=[])
    parser.add_argument("--defines", "-D", nargs="+", default=[])
    parser.add_argument("--after-shell", default=False, action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--silence-errors", action="store_true", default=False)
    parser.add_argument("--allow-all", action="store_true")
    # for linux
    parser.add_argument("--using-gcc-version", default="9")

    args = parser.parse_args(argv)

    include_path = args.include_path
    if os.name == "posix":
        include_path.append("/usr/lib/gcc/x86_64-linux-gnu/{}/include/".format(args.using_gcc_version))

    ast_parser = AstParser(headers=args.headers, include_path=include_path, defines=args.defines, allow_all=args.allow_all)
    ast_parser.skip_function_bodies = False
    node = ast_parser.parse(args.input)

    if args.verbose or not args.silence_errors:
        if args.verbose or ast_parser.errors:
            print("/*")
            ast_parser.dump_errors(sys.stderr)
            print(" */")

    # TODO:
    interpreter = Interpreter()
    interpreter.evaluate(node)

    #interpreter.extract(args.vars)

    if args.after_shell:
        code.interact(local=locals())

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
