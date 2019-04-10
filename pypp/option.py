from .builder import boost, pybind11


class GeneratorOption:
    def __init__(self, boost=True):
        self.boost = boost
        self.init()

    def init(self):
        if self.boost:
            self.return_value_policy = boost.BoostPythonReturnValuePolicyBuilder(self)
            self.function = boost.BoostPythonFunctionBuilder(self)
            self.method = boost.BoostPythonMethodBuilder(self)
            self.class_ = boost.BoostPythonClassBuilder(self)
            self.enum = boost.BoostPythonEnumBuilder(self)
        else:
            self.return_value_policy = pybind11.Pybind11ReturnValuePolicyBuilder(self)
            self.function = pybind11.Pybind11FunctionBuilder(self)
            self.method = pybind11.Pybind11MethodBuilder(self)
            self.class_ = pybind11.Pybind11ClassBuilder(self)
            self.enum = pybind11.Pybind11EnumBuilder(self)
