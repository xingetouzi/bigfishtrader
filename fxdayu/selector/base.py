# encoding:utf-8


class Selector(object):

    def __init__(self, data_client=None):
        """

        :param data_client: 操作数据库的对象(用于数据持久化)
        :return:
        """
        self.client = data_client

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
