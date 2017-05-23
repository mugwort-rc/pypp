import clang.cindex
from clang.cindex import TranslationUnit

clang.cindex.Config.set_library_file("/usr/lib/llvm-3.8/lib/libclang-3.8.so.1")


class AstParser(object):

    clang_args = [
        "-std=c++1y",
    ]

    def __init__(self, include_path=[], lib_path=[], defines=[]):
        self.index = clang.cindex.Index.create()
        self.include_path = include_path
        self.lib_path = lib_path
        self.defines = defines

    def parse(self, source):
        #assert source.endswith(".h") or source.endswith(".hpp")
        clang_args = list(self.clang_args)  # copy
        clang_args += ["-I"+x for x in self.include_path]
        clang_args += ["-L"+x for x in self.lib_path]
        clang_args += ["-D"+x for x in self.defines]

        src = [
            ("<entrypoint>.cpp", '#include "{}"'.format(source)),
        ]
        unit = self.index.parse("<entrypoint>.cpp", clang_args, src,
                            TranslationUnit.PARSE_SKIP_FUNCTION_BODIES)
        return AstNodeRoot(unit.cursor, source)


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
    def __init__(self, node, source):
        super(AstNodeRoot, self).__init__(node)
        self.source = source

    def __iter__(self):
        for child in self.ptr.get_children():
            if not child.location.file.name.endswith(self.source):
                continue
            yield AstNode(child)


def parse(source, *args, **kwargs):
    parser = AstParser(*args, **kwargs)
    return parser.parse(source)
