# encoding:utf-8


class TimeRule(object):
    def __init__(self, tag=None, **rules):
        self.rules = rules
        self.tag = tag

    def __hash__(self):
        return hash(self.tag)

    def __eq__(self, other):
        if isinstance(other, TimeRule):
            return self.tag == other.tag
        else:
            return False

    def match(self, time):
        for key, value in self.rules.items():
            v = getattr(time, key)
            if not callable(v):
                if v != value:
                    return False
            else:
                if v() != value:
                    return False
        return True


class Selector(object):

    __name__ = 'selector'

    def __init__(self, rule=None, data_client=None, priority=0):
        """

        :param data_client: 操作数据库的对象(用于数据持久化)
        :return:
        """
        self.client = data_client
        self.name = None
        self.priority = priority
        self.rule = rule if rule else TimeRule()

    def __lt__(self, other):
        return self.priority < other.priority

    def __gt__(self, other):
        return self.priority > other.priority

    def __str__(self):
        return self.__name__

    def execute(self, context, data, **others):
        """
        执行选股逻辑

        :param context: 读写计算结果的对象
        :param data: 获取市场数据的对象
        :return:
        """
        raise NotImplementedError("Should implement function execute()")

    def start(self, context, data, **others):
        """
        在一个选股周期开始时被调用

        :param context:
        :param data:
        :param others:
        :return:
        """
        pass

    def end(self, context, data, **others):
        """
        在一个选股周期结束时被调用

        :param context:
        :param data:
        :param others:
        :return:
        """
        pass


class Executor(object):

    __name__ = 'executor'

    def __init__(self, rule=None, data_client=None, priority=0):
        """

        :param data_client: 操作数据库的对象(用于数据持久化)
        :return:
        """
        self.client = data_client
        self.name = None
        self.priority = priority
        self.rule = rule if rule else TimeRule()

    def __lt__(self, other):
        return self.priority < other.priority

    def __gt__(self, other):
        return self.priority > other.priority

    def __str__(self):
        return self.__name__

    def execute(self, context, data, environment):
        """
        执行选股结果，与引擎对接

        :param context: fxdayu.Context object
        :param data: fxdayu.data.DataSupport object
        :param environment: fxdayu.Environment object
        :return:
        """
        raise NotImplementedError("Should implement function execute()")

    def start(self, context, data, environment):
        """

        :param context:
        :param data:
        :param environment:
        :return:
        """
        pass

    def end(self, context, data, environment):
        """

        :param context:
        :param data:
        :param environment:
        :return:
        """
        pass
