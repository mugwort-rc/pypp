import enum
from .builder import boost, pybind11, embind


class GeneratorType(enum.Enum):
    Boost = enum.auto()
    Pybind11 = enum.auto()
    Embind = enum.auto()



class GeneratorOption:
    def __init__(self, type=GeneratorType.Boost):
        self.type = type
        self.init()

    def init(self):
        if self.type == GeneratorType.Boost:
            self.option = boost.BoostPythonOptionBuilder(self)
            self.function = boost.BoostPythonFunctionBuilder(self)
            self.method = boost.BoostPythonMethodBuilder(self)
            self.class_ = boost.BoostPythonClassBuilder(self)
            self.enum = boost.BoostPythonEnumBuilder(self)
        elif self.type == GeneratorType.Pybind11:
            self.option = pybind11.Pybind11OptionBuilder(self)
            self.function = pybind11.Pybind11FunctionBuilder(self)
            self.method = pybind11.Pybind11MethodBuilder(self)
            self.class_ = pybind11.Pybind11ClassBuilder(self)
            self.enum = pybind11.Pybind11EnumBuilder(self)
        elif self.type == GeneratorType.Embind:
            self.option = embind.EmbindOptionBuilder(self)
            self.function = embind.EmbindFunctionBuilder(self)
            self.method = embind.EmbindMethodBuilder(self)
            self.class_ = embind.EmbindClassBuilder(self)
            self.enum = embind.EmbindEnumBuilder(self)
        else:
            raise NotImplementedError("type:{} is not implemented".format(self.type))
