# -*- coding: utf-8 -*-

class BuilderBase:
    def __init__(self, option):
        self.option = option

    def make(self, *args, **kwargs):
        raise NotImplementedError


class OptionBuilder(BuilderBase):
    def make(self, entity):
        raise NotImplementedError

class FunctionBuilder(BuilderBase):
    def make(self, func):
        raise NotImplementedError

class MethodBuilder(BuilderBase):
    def make(self, method, class_name):
        raise NotImplementedError

class ClassBuilder(BuilderBase):
    def make(self, clss):
        raise NotImplementedError

    def init(self, node):
        raise NotImplementedError

class EnumBuilder(BuilderBase):
    def make(self, enum):
        raise NotImplementedError
