# encoding=utf-8
from bigfishtrader.event import *


class APIs(object):
    def __init__(self, queue, data, portfolio, router=None):
        self.event_queue = queue
        self.data = data
        self.portfolio = portfolio
        self.order = router
        self.__id = 0

    def next_id(self):
        self.__id += 1
        return self.__id


def initialize_operation(queue, handler, portfolio, router=None):
    global api
    api = APIs(queue, handler, portfolio, router)


def open_position(ticker, quantity, price=None, order_type=EVENTS.ORDER):
    """
    开仓
    市价单输入 ticker + quantity
    限价单调用 open_limit 和 open_stop
    :param ticker:
    :param quantity:
    :param price:
    :param order_type:
    :return:
    """

    api.event_queue.put(
        OrderEvent(
            api.data.current_time,
            ticker, OPEN_ORDER, quantity, price,
            order_type=order_type,
            local_id=api.next_id()
        )
    )


def open_limit(ticker, quantity, price):
    open_position(ticker, quantity, price, EVENTS.LIMIT)


def open_stop(ticker, quantity, price):
    open_position(ticker, quantity, price, EVENTS.STOP)


def cancel_order(**conditions):
    api.event_queue.put(
        CancelEvent(**conditions)
    )


def close_position(ticker=None, quantity=None, price=None, order_type=EVENTS.ORDER, position=None):
    """
    平仓
    市价单只需要 ticker + quantity 或 position
    限价单可调用 close_limit 和 close_stop

    :param ticker:
    :param quantity:
    :param price:
    :param order_type:
    :param position:
    :return:
    """
    if position:
        available_quantity = get_available_security(position.ticker)[position.ticker]

        if available_quantity:
            api.event_queue.put(
                OrderEvent(
                    api.data.current_time,
                    position.ticker, CLOSE_ORDER,
                    available_quantity, price,
                    order_type=order_type,
                    local_id=api.next_id()
                )
            )
        else:
            print('available_quantity == 0 , unable to close position')

    elif ticker and quantity and price:
        available_quantity = get_available_security(position.ticker)[ticker]
        if quantity > available_quantity:
            print('quantity(%s) > available_quantity(%s) , unable to close position'
                  % (quantity, available_quantity))

        api.event_queue.put(
            OrderEvent(
                api.data.current_time,
                ticker, CLOSE_ORDER, quantity, price,
                order_type=order_type,
                local_id=api.next_id()
            )
        )


def close_limit(price, ticker=None, quantity=None, position=None):
    close_position(ticker, quantity, price, EVENTS.LIMIT, position)


def close_stop(price, ticker=None, quantity=None, position=None):
    close_position(ticker, quantity, price, EVENTS.STOP, position)


def set_commission(buy_cost=None, sell_cost=None, unit=None, calculate_function=None):
    """
    佣金设置
    :param buy_cost: 买入(开仓)佣金
    :param sell_cost: 卖出(平仓)佣金
    :param unit:
        'value' : commission = price * quantity * (buy_cost or sell_cost)
        'share' : commission = quantity * (buy_cost or sell_cost)
    :param calculate_function:
        可自定义佣金计算方法，以order和price作为输入参数，返回佣金值
        sample:
        def calculation(order, price):
            return price * 0.0001
    :return:
    """
    exchange = api.order
    if exchange:
        if buy_cost and sell_cost and unit:
            global BUY_COST, SELL_COST
            BUY_COST, SELL_COST = buy_cost, sell_cost
            if unit == 'value':
                setattr(exchange, "calculate_commission", commission_value)
            elif unit == 'share':
                setattr(exchange, "calculate_commission", commission_share)

        if calculate_function:
            setattr(exchange, "calculate_commission", calculate_function)


def commission_value(order, price):
    if order.action:
        return abs(order.quantity) * price * BUY_COST
    else:
        return abs(order.quantity) * price * SELL_COST


def commission_share(order, price):
    if order.action:
        return abs(order.quantity) * BUY_COST
    else:
        return abs(order.quantity) * SELL_COST


def initialize():
    pass


def set_slippage(value=None, unit=None, function=None):
    """
    滑点设置
    :param value: 滑点值
    :param unit:
        'pct': slippage = price * value
        'value': slippage = value
    :param function:
        可自定义滑点计算方法，以order和price作为输入参数，返回滑点值
        sample:
        def calculation(order, price):
            if order.quantity > 0:
                return price * 0.0001
            else:
                return -price * 0.0001
    :return:
    """
    exchange = api.order
    if exchange:
        if value and unit:
            global SLIPPAGE
            SLIPPAGE = value
            if unit == 'pct':
                setattr(exchange, 'calculate_slippage', slippage_pct)
            elif unit == 'value':
                setattr(exchange, 'calculate_slippage', slippage_pct)
        elif function:
            setattr(exchange, 'calculate_slippage', function)


def slippage_value(order, price):
    # 开多和平空，滑点为正
    # 开空和平多，滑点为负
    if (order.quantity > 0 and order.action) or \
            (order.quantity < 0 and order.action == 0):
        return SLIPPAGE
    else:
        return -SLIPPAGE


def slippage_pct(order, price):
    # 开多和平空，滑点为正
    # 开空和平多，滑点为负
    if (order.quantity > 0 and order.action) or \
            (order.quantity < 0 and order.action == 0):
        return SLIPPAGE * price
    else:
        return -SLIPPAGE * price


def set_ticker_info(**ticker):
    exchange = api.order
    if exchange:
        ticker_info = getattr(exchange, 'ticker_info', {})
        for key, value in ticker:
            ticker_info[key] = value
        if not hasattr(exchange, 'ticker_info'):
            setattr(exchange, 'ticker_info', ticker_info)


def get_security(*tickers):
    """
    获取当前持仓
    :param tickers: 持仓品种，默认返回所有
    :return: {ticker: quantity}
    """
    security = {}
    positions = api.portfolio.get_positions()
    if len(tickers):
        for ticker in tickers:
            position = positions.get(ticker, None)
            if position:
                security[ticker] = position.quantity
    else:
        for ticker, position in positions:
            security[ticker] = position.quantity

    return security


def get_available_security(*tickers):
    """
    获取当前可用持仓
    :param tickers: 持仓品种，默认返回所有
    :return: {ticker: quantity}
    """
    security = get_security(*tickers)
    orders = api.order.get_orders()
    for ticker in security:
        security[ticker] -= sum(
            [
                order.quantity if order.match(action=CLOSE_ORDER, ticker=ticker) else 0
                for order in orders
            ]
        )
    return security


def get_positions():
    return api.portfolio.get_positions()