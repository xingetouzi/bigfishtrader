# encoding:utf-8
from collections import OrderedDict


def sort_selector(selectors):
    dct = OrderedDict()

    for s in sorted(selectors):
        dct.setdefault(s.rule, []).append(s)

    return dct


class Admin(object):
    def __init__(self, *selectors):
        self.selectors = sort_selector(selectors)

    def on_time(self, time, context, data):
        pass


class IntersectionAdmin(Admin):
    def on_time(self, time, context, data):
        for rule, selectors in self.selectors.items():
            if rule.match(time):
                pool = data.can_trade()
                for selector in selectors:
                    pool = selector.execute(pool, data)
                context.pool = pool


class UnionAdmin(Admin):
    def on_time(self, time, context, data):
        for rule, selectors in self.selectors.items():
            if rule.match(time):
                pool = data.can_trade()
                result = []
                for selector in selectors:
                    result = filter(lambda x: x not in result, selector.execute(pool))
                context.pool = result
