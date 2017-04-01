# encoding: utf-8
from fxdayu.modules.order.style import MarketOrder, LimitOrder, StopLimitOrder, StopOrder

__all__ = ["sid", "symbol", "symbols", "order", "order_target", "order_percent",
           "order_target_percent", "order_target_value", "order_value", "get_open_orders",
           "time_schedule", "time_rules", "set_commission", "set_slippage",
           "file_path", "get_open_orders", "LimitOrder", "MarketOrder", "StopLimitOrder", "StopOrder"]


# Security 相关

def sid(s):
    """
    接受一个整数值来通过sid来查找Security（证券品种）对象。

    Args:
        s(int): Security的id。

    Returns:
        fxdayu.models.data.Security: 对应的证券品种对象。若找不到品种，返回None。
    """
    pass


def symbol(s):
    """
    接受一个字符串来查找一个Security（证券品种）对象。

    Args:
        s(str | fxdayu.models.data.Security): 表示Security代码的字符串。

    Returns:
        fxdayu.models.data.Security: 对应的证券品种对象。若找不到品种，返回None。
    """
    pass


def symbols(*s):
    """
    通过字符串查找多个证券。每个参数都必须是字符串，并用逗号分隔。

    Args:
        s(list(str)): 字符串列表

    Returns:
        list(fxdayu.models.data.Security): 返回Security列表。对应输入中的每一字符串，返回列表
        中有一个证券品种对象。若找不到品种，对应项为None。
    """
    pass


def order(security, amount, style=None):
    """
    发送所指定手数amount的给定证券security的订单。从所使用的style参数推断订单类型。
    如果仅传入security和amount参数，则将订单视为为市价订单。

    Args:
        security(str | fxdayu.models.data.Security): 证券，可以是证券代码或者Security对象。
        amount(int): 交易手数，整数。正值意味着买入，负值意味着卖出。
        style(fxdayu.modules.order.style.OrderType): (可选)指定订单样式，默认值为市价订单。可用的订单样式有：
            style = MarketOrder(exchange)
            style = StopOrder(stop_price, exchange)
            style = LimitOrder(limit_price, exchange)
            style = StopLimitOrder(limit_price=price1, stop_price=price2, exchange)

    Returns:
        fxdayu.models.data.OrderReq: 订单对象。
    """
    pass


def order_value(security, value, style=None):
    """
    根据给定价值value而不是给定的交易手数下单。传入负值代表卖出。交易手数总是被截断为整数手。

    Args:
        security(str | fxdayu.models.data.Security): 证券，可以是证券代码或者Security对象。
        value(float): 证券的价值，据此计算交易手数，并截断为整数手。正值意味着买入，负值意味着卖出。
        style(fxdayu.modules.order.style.OrderType): (可选)指定订单样式，默认值为市价订单。可用的订单样式有：
            style = MarketOrder(exchange)
            style = StopOrder(stop_price, exchange)
            style = LimitOrder(limit_price, exchange)
            style = StopLimitOrder(limit_price=price1, stop_price=price2, exchange)
    Examples:
        发送价值达￥10000的股票代码000002所代表股票的订单：order_value(symbol('000002'),10000)
        如果000002的价格是每股15元，这将购买6手(600股)，小数部分手数将被截断（不考虑滑点和交易成本）。

    Returns:
        fxdayu.models.data.OrderReq: 订单对象。
    """
    pass


def order_percent(security, percent, style=None):
    """
    发送对应于当前资产净值的给定百分比（即头寸总市值和期末现金余额的总和）的订单。传入负百分比值表示卖出。订单总是被截断为全股。百分比必须以小数表示（0.50表示50％）。

    Args:
        security(str | fxdayu.models.data.Security): 证券，可以是证券代码或者Security对象。
        percent(float): 百分比。正值意味着买入，负值意味着卖出。
        style(fxdayu.modules.order.style.OrderType): (可选)指定订单样式，默认值为市价订单。可用的订单样式有：
            style = MarketOrder(exchange)
            style = StopOrder(stop_price, exchange)
            style = LimitOrder(limit_price, exchange)
            style = StopLimitOrder(limit_price=price1, stop_price=price2, exchange)

    Examples:
        order_percent(symbol('000002'),.5)将买入价值当前投资组合50%的股票000002。
        如果000002是15元/股，投资组合价值是100000元，这将购买33手（不考虑滑点和交易成本）。

    Returns:
        fxdayu.models.data.OrderReq: 订单对象。
    """
    pass


def order_target(security, amount, style=None):
    """
    发送订单以将security的头寸调整为目标手数amount。如果账户中没有对应头寸，则会按整个目标amount下单。
    如果已有对应头寸，则对目标手数和当前持仓量之间的差额进行下单。
    传入负目标手数值将建立等于指定负数的空头头寸。

    Args:
        security(str | fxdayu.models.data.Security): 证券，可以是证券代码或者Security对象。
        amount(int): 目标手数，整数。正值意味多头头寸，负值意味着空头头寸。（股票中若传入负值将报错）
        style(fxdayu.modules.order.style.OrderType): (可选)指定订单样式，默认值为市价订单。可用的订单样式有：
            style = MarketOrder(exchange)
            style = StopOrder(stop_price, exchange)
            style = LimitOrder(limit_price, exchange)
            style = StopLimitOrder(limit_price=price1, stop_price=price2, exchange)

    Returns:
        fxdayu.models.data.OrderReq: 订单对象。
    """
    pass


def order_target_value(security, value, style=None):
    """
    根据目标头寸价值value计算目标头寸手数，并截取整数手。正值意味多头头寸，负值意味着空头头寸。
    然后按order_target中的方式下达订单。

    Args:
        security(str | fxdayu.models.data.Security): 证券，可以是证券代码或者Security对象。
        value(float): 目标头寸价值，据此计算目标头寸手数，并截断为整数手。正值意味多头头寸，负值意味着空头头寸。
        style(fxdayu.modules.order.style.OrderType): (可选)指定订单样式，默认值为市价订单。可用的订单样式有：
            style = MarketOrder(exchange)
            style = StopOrder(stop_price, exchange)
            style = LimitOrder(limit_price, exchange)
            style = StopLimitOrder(limit_price=price1, stop_price=price2, exchange)

    Returns:
        fxdayu.models.data.OrderReq: 订单对象。
    """
    pass


def order_target_percent(security, percent, style=None):
    """
    根据目标头寸占当前账户净值百分比数计算目标头寸手数，并截取整数手。正值意味多头头寸，负值意味着空头头寸。
    然后按order_target中的方式下达订单。

    Args:
        security(str | fxdayu.models.data.Security): 证券，可以是证券代码或者Security对象。
        percent(float): 目标头寸价值占当前账户净值百分比数。正值意味多头头寸，负值意味着空头头寸。
        style(fxdayu.modules.order.style.OrderType): (可选)指定订单样式，默认值为市价订单。可用的订单样式有：
            style = MarketOrder(exchange)
            style = StopOrder(stop_price, exchange)
            style = LimitOrder(limit_price, exchange)
            style = StopLimitOrder(limit_price=price1, stop_price=price2, exchange)

    Returns:
        fxdayu.models.data.OrderReq: 订单对象。
    """
    pass


def get_open_orders(security=None):
    """
    如果security为None, 返回所有活跃状态（未完全成交且仍有效）的订单. 如果指定了sid, 返回该品种的处于活跃状态的订单

    Args:
        security(int): 整数，证券的sid。

    Returns:
        如果security为None, 返回一个字典，以sid为key，value为对应security的订单列表, 订单按下单时间顺序排列.
        如果指定了security,返回一个列表，为对应security的订单列表，订单按下单时间顺序排列。
    """
    pass


def get_order(order_id):
    """
    返回给定order_id的订单.

    Args:
        order_id(str): 字符串类型的订单ID

    Returns:
        返回的订单对象是可读写的局部变量（若未被其他全局变量引用，将在函数运行结束时被回收）
    """
    pass


def cancel_order(order):
    """
    尝试取消指定的订单。取消将以异步的方式进行。

    Args:
        order(str | fxdayu.models.data.OrderReq): 可以是字符串类型的order_id或是order对象本身。

    Returns:
        None
    """
    pass


def time_schedule(func, time_rule, ahead=True):
    """
    设置定时任务

    :param func:
    :param time_rule:
    :param ahead:
    :return:
    """
    pass


def time_rules(**kwargs):
    """
    定时任务的时间条件

    :param kwargs:
    :return:
    """

    def function(time):
        for key, value in kwargs.items():
            v = getattr(time, key)
            if not callable(v):
                if v != value:
                    return False
            else:
                if v() != value:
                    return False

        return True

    return function


def set_commission(per_value=0, per_share=0, min_cost=0, function=None):
    """
    设置交易所(模拟)保证金

    :param per_value:
    :param per_share:
    :param min_cost:
    :return:
    """
    pass


def set_slippage(pct=0, function=None):
    """
    设置成交(模拟)时价格滑点

    :param pct:
    :param function:
    :return:
    """
    pass


def file_path(name):
    import os
    return os.path.abspath(name)

