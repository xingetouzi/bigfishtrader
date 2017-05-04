# encoding:utf-8
from collections import OrderedDict
from functools import partial


def sort_selector(selectors):
    dct = OrderedDict()

    for s in sorted(selectors):
        dct.setdefault(s.rule, []).append(s)

    return dct


class Context(object):
    pass


class Admin(object):
    def __init__(self, *selectors):
        self.sorted = sort_selector(selectors)
        self.selectors = selectors

    def on_time(self, time, context, data):
        return []


class IntersectionAdmin(Admin):
    def on_time(self, time, context, data):
        for rule, selectors in self.sorted.items():
            if rule.match(time):
                pool = data.can_trade()
                for selector in selectors:
                    pool = selector.execute(pool, context, data)
                context.pool = pool
                return pool
        else:
            return []


class UnionAdmin(Admin):
    def on_time(self, time, context, data):
        for rule, selectors in self.sorted.items():
            if rule.match(time):
                pool = data.can_trade()
                result = []
                for selector in selectors:
                    result.extend(filter(lambda x: x not in result, selector.execute(pool, context, data)))
                context.pool = result
                return result
        else:
            return []
