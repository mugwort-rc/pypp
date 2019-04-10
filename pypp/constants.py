import clang.cindex


CPP_OPERATORS = [
    "operator()",
    #"operator \w+()",  # TODO: cast operator
    "operator->",
    "operator[]",
    "operator++",  # TODO: ++(int)
    "operator--",  # TODO: --(int)
    "operator new",
    "operator delete",
    "operator new[]",
    "operator delete[]",
    "operator~",
    "operator!",
    "operator+",  # TODO: +(const T &rhs)
    "operator-",  # TODO: -(const T &rhs)
    "operator&",  # TODO: &(const T &rhs)
    "operator*",  # TODO: *(const T &rhs)
    "operator->*",
    "operator/",
    "operator<<",
    "operator>>",
    "operator<",
    "operator<=",
    "operator>",
    "operator>=",
    "operator==",
    "operator!=",
    "operator^",
    "operator|",
    "operator&&",
    "operator||",
    "operator=",
    "operator*=",
    "operator/=",
    "operator%=",
    "operator+=",
    "operator-=",
    "operator<<=",
    "operator>>=",
    "operator&=",
    "operator^=",
    "operator|=",
    "operator,",
]
UNARY_OPERATOR_MAP = {
    "operator~": "__inv__",
    "operator!": "__not__",
    "operator+": "__pos__",
    "operator-": "__neg__",
}
BINARY_OPERATOR_MAP = {
    "operator+": "__add__",
    "operator-": "__sub__",
    "operator*": "__mul__",
    "operator/": "__floordiv__",
    "operator%": "__mod__",
    "operator<<": "__lshift__",
    "operator>>": "__rshift__",
    "operator<": "__lt__",
    "operator<=": "__le__",
    "operator>": "__gt__",
    "operator>=": "__ge__",
    "operator==": "__eq__",
    "operator!=": "__ne__",
    "operator^": "__xor__",
    "operator&": "__and__",
    "operator|": "__or__",
    "operator bool()": "__truth__",
    "operator+=": "__iadd__",
    "operator-=": "__isub__",
    "operator*=": "__imul__",
    "operator/=": "__ifloordiv__",
    "operator%=": "__imod__",
    "operator<<=": "__ilshift__",
    "operator>>=": "__irshift__",
    "operator&=": "__iand__",
    "operator^=": "__ixor__",
    "operator|=": "__ior__",
}
OTHER_OPERATOR_MAP = {
    "operator()": "__call__",
}


NOT_DEFAULT_ARG_KINDS = [
    clang.cindex.CursorKind.TYPE_REF,
    clang.cindex.CursorKind.TEMPLATE_REF,
    clang.cindex.CursorKind.NAMESPACE_REF,
]

PYTHON_RESERVED = [
    "and",
    "del",
    "from",
    "not",
    "while",
    "as",
    "elif",
    "global",
    "or",
    "with",
    "assert",
    "else",
    "if",
    "pass",
    "yield",
    "break",
    "except",
    "import",
    "print",
    "class",
    "exec",
    "in",
    "raise",
    "continue",
    "finally",
    "is",
    "return",
    "def",
    "for",
    "lambda",
    "try",
]
