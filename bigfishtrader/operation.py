# encoding=utf-8
from bigfishtrader.event import *
from bigfishtrader.engine.handler import HandlerCompose, Handler


class APIs(HandlerCompose):
    def __init__(self, queue, data, portfolio, engine, router, context, mode='paper'):
        super(APIs, self).__init__()
        self.event_queue = queue
        self.data = data
        self.portfolio = portfolio
        if isinstance(portfolio, dict):
            self.portfolios = portfolio
        self.order = router
        self.context = context
        self._engine = engine
        self.__id = 0
        self.buy_cost = 0
        self.sell_cost = 0
        self.slippage = 0
        self.mode = mode

    def register_handler(self, handler, event_type, topic='.', priority=0):
        self._engine.register(handler, event_type, topic, priority)

    def next_id(self):
        self.__id += 1
        return self.__id

    def get_portfolio(self, name=None):
        if name:
            return self.portfolios[name]
        else:
            return self.portfolio



def initialize_operation(queue, data, portfolio, engine, router, context=None, mode='paper'):
    global api
    api = APIs(queue, data, portfolio, engine, router, context, mode)


# def open_order(ticker, quantity, price=None, order_type=EVENTS.ORDER, tag=None, take_profit=0, stop_lost=0):
#     api.event_queue.put(
#         OrderEvent(
#             api.context.current_time, ticker, OPEN_ORDER,
#             quantity, price, order_type, tag, api.next_id(),
#             take_profit, stop_lost, 'oanda'
#         )
#     )


def order_close(position_id=None, quantity=None, price=None, position=None):
    position = api.portfolio.positions[position_id] if position is None else position
    quantity = position.quantity if quantity is None else quantity
    api.event_queue.put(
        OrderEvent(
            api.context.current_time, position.ticker,
            CLOSE_ORDER, quantity, price,
            local_id=position.position_id,
            topic='oanda'
        )
    )
    return position.position_id


def order_modify(order_id, **kwargs):
    api.event_queue.put(
        ModifyEvent(api.context.current_time, order_id, 'oanda', **kwargs)
    )


def get_orders():
    return api.order.get_orders()


def open_position(ticker, quantity, price=None, order_type=EVENTS.ORDER, **kwargs):
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
    local_id = api.next_id()
    api.event_queue.put(
        OrderEvent(
            api.context.current_time,
            ticker, OPEN_ORDER, quantity, price,
            order_type=order_type,
            local_id=local_id,
            **kwargs
        )
    )
    return local_id


def open_limit(ticker, quantity, price, **kwargs):
    return open_position(ticker, quantity, price, EVENTS.LIMIT, **kwargs)


def open_stop(ticker, quantity, price, **kwargs):
    return open_position(ticker, quantity, price, EVENTS.STOP, **kwargs)


def cancel_order(**conditions):
    api.event_queue.put(
        CancelEvent(**conditions)
    )


def close_position(ticker=None, quantity=None, price=None, order_type=EVENTS.ORDER, position=None, **kwargs):
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
            _id = position.position_id if position.position_id else api.next_id()
            api.event_queue.put(
                OrderEvent(
                    api.context.current_time,
                    position.ticker, CLOSE_ORDER,
                    available_quantity, price,
                    order_type=order_type,
                    local_id=_id
                )
            )
            return _id
        else:
            print('available_quantity == 0 , unable to close position')

    elif ticker and quantity:
        available_quantity = get_available_security(ticker).get('ticker', 0)
        if quantity > available_quantity:
            print('quantity(%s) > available_quantity(%s) , unable to close position'
                  % (quantity, available_quantity))

        if 'local_id' not in kwargs.keys():
            kwargs['local_id'] = api.next_id()
        api.event_queue.put(
            OrderEvent(
                api.context.current_time,
                ticker, CLOSE_ORDER, quantity, price,
                order_type=order_type,
                **kwargs
            )
        )
        return kwargs['local_id']


def close_limit(price, ticker=None, quantity=None, position=None):
    return close_position(ticker, quantity, price, EVENTS.LIMIT, position)


def close_stop(price, ticker=None, quantity=None, position=None):
    return close_position(ticker, quantity, price, EVENTS.STOP, position)


def set_commission(buy_cost=None, sell_cost=None, unit=None, min_cost=0, calculate_function=None):
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
            api.buy_cost, api.sell_cost = buy_cost, sell_cost
            if unit == 'value':
                setattr(exchange, "calculate_commission", commission_value)
            elif unit == 'share':
                setattr(exchange, "calculate_commission", commission_share)

        if calculate_function:
            setattr(exchange, "calculate_commission", calculate_function)


def commission_value(order, price):
    if order.action:
        return abs(order.quantity) * price * api.buy_cost
    else:
        return abs(order.quantity) * price * api.sell_cost


def commission_share(order, price):
    if order.action:
        return abs(order.quantity) * api.buy_cost
    else:
        return abs(order.quantity) * api.sell_cost


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
            api.slippage = value
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
        return api.slippage
    else:
        return api.slippage


def slippage_pct(order, price):
    # 开多和平空，滑点为正
    # 开空和平多，滑点为负
    if (order.quantity > 0 and order.action) or \
            (order.quantity < 0 and order.action == 0):
        return api.slippage * price
    else:
        return -api.slippage * price


def set_ticker_info(**ticker):
    exchange = api.order
    if exchange:
        ticker_info = getattr(exchange, 'ticker_info', {})
        for key, value in ticker.items():
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
    positions = api.portfolio.positions
    if len(tickers):
        for ticker in tickers:
            position = positions.get(ticker, None)
            if position:
                security[ticker] = position.quantity
    else:
        for ticker, position in positions.items():
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
                for order in orders.values()
            ]
        )
    return security


def get_positions():
    return api.portfolio.positions


def time_limit(func):
    def wrapper(event, kwargs=None):
        func(api.context, api.data)

    return wrapper


def register_time_limit(function, topic, **limit):
    api.register_handler(function, EVENTS.TIME, topic)

    api.data.put_limit_time(api.event_queue, topic, **limit)


def get_portfolio(name=None):
    return api.get_portfolio(name)

