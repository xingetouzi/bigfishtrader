class Analysis(object):
    def __init__(self, performance):
        self.performance = performance

    def calculate(self):
        raise NotImplementedError

    def show(self):
        raise NotImplementedError


class FactorAnalysis(object):
    def __init__(self, performance):
        self.performance = performance

    def calculate(self):
        pass

    def show(self):
        pass
