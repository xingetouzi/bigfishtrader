# encoding:utf-8
from collections import OrderedDict


def sort_selector(selectors):
    dct = OrderedDict()

    for s in sorted(selectors):
        dct.setdefault(s.rule, []).append(s)

    return dct


class SelectorAdmin(object):
    def __init__(self, *selectors):
        self.selectors = sort_selector(selectors)

    def on_time(self, time, context, data):
        for rule, selectors in self.selectors.items():
            if rule.match(time):
                selectors[0].start(context, data)
                for selector in selectors:
                    selector.execute(context, data)
                selectors[-1].end(context, data)


class ExecutorAdmin(object):
    def __init__(self, *executors):
        self.executors = sort_selector(executors)

    def on_time(self, time, context, data, environment):
        for rule, executors in self.executors.items():
            if rule.match(time):
                executors[0].start(context, data, environment)
                for executor in executors:
                    executor.execute(context, data, environment)
                executors[-1].end(context, data, environment)