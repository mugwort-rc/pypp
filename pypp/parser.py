try:
    import configparser
except ImportError:
    # for python2
    import ConfigParser as configparser
import os

import clang.cindex
from clang.cindex import TranslationUnit

LIBCLANG_PATH = None
LIBCLANG_PATH_DEFAULT = {
    "posix": "/usr/lib/llvm-3.8/lib/libclang-3.8.so.1",  # Ubuntu 16.04
    "nt": r"C:\Program Files\LLVM\bin\libclang.dll",
}

def __load_config(path):
    global LIBCLANG_PATH
    config = configparser.ConfigParser()
    config.read(path)
    LIBCLANG_PATH = config.get("llvm", "libclang")
if not LIBCLANG_PATH and os.path.exists(".PYPP_LIBCLANG_PATH"):
    __load_config(".PYPP_LIBCLANG_PATH")
if not LIBCLANG_PATH and os.path.exists(os.path.expanduser("~/.config/pypp.conf")):
    __load_config(os.path.expanduser("~/.config/pypp.conf"))
if not LIBCLANG_PATH:
    LIBCLANG_PATH = os.getenv("PYPP_LIBCLANG_PATH", LIBCLANG_PATH_DEFAULT[os.name])

clang.cindex.Config.set_library_file(LIBCLANG_PATH)


CLANG_ERROR_SEVERITY = [
    "Ignored",
    "Note",
    "Warning",
    "Error",
    "Fatal",
]


class AstParser(object):

    clang_args = [
        "-std=c++1y",
    ]

    def __init__(self, headers=[], include_path=[], lib_path=[], defines=[], allow_all=False):
        self.index = clang.cindex.Index.create()
        self.headers = headers
        self.include_path = include_path
        self.lib_path = lib_path
        self.defines = defines
        self.errors = []
        self.allow_all = allow_all

    def parse(self, source):
        #assert source.endswith(".h") or source.endswith(".hpp")
        clang_args = list(self.clang_args)  # copy
        clang_args += ["-I"+x for x in self.include_path]
        clang_args += ["-L"+x for x in self.lib_path]
        clang_args += ["-D"+x for x in self.defines]

        includes = self.headers + [source]
        lines = ['#include "{}"'.format(x) for x in includes]
        src = [
            ("<entrypoint>.cpp", "\n".join(lines)),
        ]
        unit = self.index.parse("<entrypoint>.cpp", clang_args, src,
                            TranslationUnit.PARSE_SKIP_FUNCTION_BODIES)
        self.errors = list(unit.diagnostics)
        return AstNodeRoot(self, unit.cursor, source)

    def dump_errors(self, fileobj):
        if not self.errors:
            print("no errors", file=fileobj)
            return
        for error in self.errors:
            print("{}: {!r}@{!r}".format(
                CLANG_ERROR_SEVERITY[error.severity],
                error.spelling,
                error.location,
            ))


class AstNode(object):
    def __init__(self, node, parent=None):
        self.ptr = node
        self.parent = parent

    def __iter__(self):
        for child in self.ptr.get_children():
            yield AstNode(child, self)

    @property
    def _fields(self):
        return []


class AstNodeRoot(AstNode):
    def __init__(self, parser, node, source):
        super(AstNodeRoot, self).__init__(node)
        self.parser = parser
        self.source = source

    def __iter__(self):
        for child in self.ptr.get_children():
            if not self.parser.allow_all and not child.location.file.name.endswith(self.source):
                print("continue")
                continue
            yield AstNode(child)


def parse(source, *args, **kwargs):
    parser = AstParser(*args, **kwargs)
    return parser.parse(source)
