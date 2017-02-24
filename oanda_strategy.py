from bigfishtrader.operation import *
from datetime import datetime
import pandas as pd
from pymongo import MongoClient

s = 50
l = 100

def initialize(context, data):
    context.ticker = 'XAU_USD'
    context.period = 'M15'
    data.init(context.ticker, context.period, datetime(2016, 10, 1))
    context.client = MongoClient(port=10001)


def handle_data(context, data):

    his = data.data_base(context.ticker, context.period, length=l+1)

    low = his['low'].values[-1]
    high = his['high'].values[-1]
    low50 = his['low'].iloc[-s:-1].min()
    low100 = his['low'].head(l).min()
    high50 = his['high'].iloc[-s:-1].max()
    high100 = his['high'].head(l).max()
    print context.current_time, 'low', low, low50, low100, 'high', high, high50, high100

    positions = get_positions()
    if len(positions):
        for _id, position in positions.items():
            if position.quantity > 0:
                if low < low50:
                    order_close(_id)
                    context.client['Account']['log'].insert_one(
                        {
                            'datetime': context.current_time,
                            'operation': 'close',
                            'order_id': _id,
                            'low': low,
                            'low50': low50
                        }
                    )

            else:
                if high > high50:
                    order_close(_id)
                    context.client['Account']['log'].insert_one(
                        {
                            'datetime': context.current_time,
                            'operation': 'close',
                            'order_id': _id,
                            'high': high,
                            'high50': high50
                        }
                    )
        return

    if low < low100:
        open_position(
            context.ticker, -1,
            take_profit=his['close'].values[-1]-12,
            stop_lost=his['close'].values[-1]+4,
            topic='oanda'
        )
        context.client['Account']['log'].insert_one(
            {
                'datetime': context.current_time,
                'operation': 'open',
                'low': low,
                'low100': low100
            }
        )
    elif high > high100:
        open_position(
            context.ticker, 1,
            take_profit=his['close'].values[-1]+10,
            stop_lost=his['close'].values[-1]-3,
            topic='oanda'
        )
        context.client['Account']['log'].insert_one(
            {
                'datetime': context.current_time,
                'operation': 'open',
                'high': high,
                'high100': high100
            }
        )
    else:
        context.client['Account']['log'].insert_one(
            {
                'datetime': context.current_time,
                'low': low,
                'low100': low100,
                'high': high,
                'high100': high100
            }
        )

