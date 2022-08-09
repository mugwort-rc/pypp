#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import sys

import clang.cindex


def print_node_tree(node, indent=""):
    if node.kind == clang.cindex.CursorKind.FUNCTION_DECL:
        print("{}{}:".format(indent, node.mangled_name))
        print("{}  func: {}".format(indent, node.spelling))
        print("{}  arguments:".format(indent))
        has_out = False
        for arg in node.get_arguments():
            print("{}  - type: {}".format(indent, arg.type.spelling))
            print("{}    name: {}".format(indent, arg.spelling))
            inout = "in"
            if "*" in arg.type.spelling:
                inout = "inout"
                has_out = True
            if arg.type.is_const_qualified():
                inout = "in"
            print("{}    io: {}".format(indent, inout))
            if inout == "inout":
                print("{}    out: true".format(indent))
        print("{}  result_type:".format(indent))
        print("{}    type: {}".format(indent, node.result_type.spelling))
        out = "false" if node.result_type.spelling == "void" else "true"
        if not has_out:
            out = "true"
        print("{}    out: {}".format(indent, out))
    for child in node.get_children():
        print_node_tree(child, indent+"  ")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("header")
    parser.add_argument("--llvm-lib", default="/usr/lib/llvm-10/lib/libclang.so.1")
    parser.add_argument("-I", "--include-path", dest="include_path", nargs="+", default=[])
    parser.add_argument("-D", "--define", dest="defines", nargs="+", default=[])
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

    unit = index.parse(src_name, clang_args, src)

    for unit_cursor in unit.cursor.get_children():
        if not unit_cursor.location.file.name.endswith(args.header):
            continue
        print_node_tree(unit_cursor)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
