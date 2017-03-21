# encoding:utf-8


class SelectorAdmin(object):
    def __init__(self, context, data):
        self.context = context
        self.data = data
        self.selectors = {}

    def execution(self):
        pass


class ExecutorAdmin(object):
    def __init__(self, context, data, environment):
        self.context = context
        self.data = data
        self.environment = environment
        self.executors = {}

    def execution(self):
        pass