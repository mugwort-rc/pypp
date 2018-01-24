#!/usr/bin/env python

import sys
import os

import argparse
import code
import readline

import clang.cindex


def print_node_tree(node, indent=""):
    print("{}{} : {}".format(indent, node.kind.name, node.displayname))
    for child in node.get_children():
        print_node_tree(child, indent+"\t")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("header")
    parser.add_argument("--llvm-lib", default="/usr/lib/llvm-3.8/lib/libclang-3.8.so.1")
    parser.add_argument("-I", "--include-path", dest="include_path", nargs="+", default=[])
    parser.add_argument("-D", "--define", dest="defines", nargs="+", default=[])
    parser.add_argument("--shell", default=False, action="store_true")

    args = parser.parse_args()

    src = [
        ("<entrypoint>.cpp", '#include "{}"'.format(args.header)),
    ]
    clang_args = [
        "-std=c++11",
        "-I ./",
    ]
    clang_args += ["-I"+x for x in args.include_path]
    clang_args += ["-D"+x for x in args.defines]

    clang.cindex.Config.set_library_file(args.llvm_lib)
    index = clang.cindex.Index.create()

    unit = index.parse("<entrypoint>.cpp", clang_args, src,
                        clang.cindex.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES)

    target_cursors = []
    for unit_cursor in unit.cursor.get_children():
        if not unit_cursor.location.file.name.endswith(args.header):
            continue
        target_cursors.append(unit_cursor)
        print_node_tree(unit_cursor)

    if args.shell:
        code.interact(local=locals())

    return 0


if __name__ == "__main__":
    sys.exit(main())
