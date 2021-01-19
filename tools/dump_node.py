#!/usr/bin/env python

import sys
import os

import argparse
import code
import readline

import clang.cindex


def print_node_tree(node, indent=""):
    if node.kind == clang.cindex.CursorKind.INTEGER_LITERAL:
        print("{}{} : {}".format(indent, node.kind.name, node.xdata))
    else:
        print("{}{} : {}".format(indent, node.kind.name, node.displayname))
    for child in node.get_children():
        print_node_tree(child, indent+"\t")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("header")
    parser.add_argument("--llvm-lib", default="/usr/lib/llvm-10/lib/libclang.so.1")
    parser.add_argument("-I", "--include-path", dest="include_path", nargs="+", default=[])
    parser.add_argument("-D", "--define", dest="defines", nargs="+", default=[])
    parser.add_argument("--shell", default=False, action="store_true")
    parser.add_argument("--show-function-bodies", default=False, action="store_true")
    parser.add_argument("--using-gcc-version", default="9")

    args = parser.parse_args()

    if args.header.endswith(".c") or args.header.endswith(".cpp"):
        src_name = args.header
        src = [
            (args.header, open(args.header).read()),
        ]
    else:
        src_name = "<entrypoint>.cpp"
        src = [
            ("<entrypoint>.cpp", '#include "{}"'.format(args.header)),
        ]
    clang_args = [
        "-std=c++17",
        "-I ./",
    ]
    clang_args += ["-I"+x for x in args.include_path]
    clang_args += ["-D"+x for x in args.defines]
    if os.name == "posix":
        clang_args.append("-I/usr/lib/gcc/x86_64-linux-gnu/{}/include/".format(args.using_gcc_version))

    clang.cindex.Config.set_library_file(args.llvm_lib)
    index = clang.cindex.Index.create()

    parse_args = []
    if not args.show_function_bodies:
        parse_args.append(clang.cindex.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES)
    print(clang_args)
    unit = index.parse(src_name, clang_args, src, *parse_args)

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
