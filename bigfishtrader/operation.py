# encoding=utf-8
from bigfishtrader.event import *


def initialize_operation(queue, handler, portfolio, router=None):
    global event_queue, price_handler, default_ticker, account, exchange
    event_queue = queue
    price_handler = handler
    default_ticker = handler.ticker
    account = portfolio
    exchange = router


def ticker():
    return default_ticker


def current_time():
    return price_handler.get_last_time()


def open_position(ticker, quantity, price=None, order_type=EVENTS.ORDER):
    event_queue.put(
        OrderEvent(
            price_handler.get_last_time(),
            ticker, OPEN_ORDER, quantity, price, order_type
        )
    )


def open_limit(ticker, quantity, price):
    open_position(ticker, quantity, price, EVENTS.LIMIT)


def open_stop(ticker, quantity, price):
    open_position(ticker, quantity, price, EVENTS.STOP)


def cancel_order(**conditions):
    event_queue.put(
        CancelEvent(**conditions)
    )


def close_position(ticker=None, quantity=None, price=None, order_type=EVENTS.ORDER, position=None):
    if position:
        event_queue.put(
            OrderEvent(
                price_handler.get_last_time(),
                position.ticker, CLOSE_ORDER, position.quantity, price
            )
        )
    else:
        event_queue.put(
            OrderEvent(
                price_handler.get_last_time(),
                ticker, CLOSE_ORDER, quantity, price
            )
        )


def close_limit(price, ticker=None, quantity=None, position=None):
    close_position(ticker, quantity, price, EVENTS.LIMIT, position)


def close_stop(price, ticker=None, quantity=None, position=None):
    close_position(ticker, quantity, price, EVENTS.stop, position)


def set_commission(buy_cost=None, sell_cost=None, unit=None, calculate_function=None):
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
    if exchange:
        ticker_info = getattr(exchange, 'ticker_info', {})
        for key, value in ticker:
            ticker_info[key] = value
        if not hasattr(exchange, 'ticker_info'):
            setattr(exchange, 'ticker_info', ticker_info)