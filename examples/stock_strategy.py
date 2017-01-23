# encoding=utf-8
from bigfishtrader.operation import *
from datetime import datetime


period = 10


def initialize(context, data):
    # 指定回测的股票池为['000001', '000002']，10年到16年的日线数据
    data.init(['000001', '000002'], 'D', start=datetime(2010, 1, 1), end=datetime(2016, 12, 31))


def handle_data(context, data):
    # 每个月的第一个周一计算
    time = context.current_time
    if (time.isoweekday() == 1) and (time.day <= 7):
        # 获取当前持仓
        security = get_security()
        s1 = security.get('000001', 0)
        s2 = security.get('000002', 0)

        # 获取历史数据
        history = data.history(['000001', '000002'], frequency='D', fields='close', length=period)
        if len(history) < period:
            return

        h1 = history['000001']
        h2 = history['000002']

        # 如果s1持仓不为0
        if s1:
            # 如果过去10个交易日s1的涨幅小于s2 则卖出s1买入s2
            if (h1.values[-1] - h1.values[0])/h1.values[-1] < (h2.values[-1] - h2.values[0])/h2.values[-1]:
                close_position('000001', s1)
                open_position('000002', 1000)

        # 如果s2持仓不为0
        elif s2:
            # 如果过去10个交易日s1的涨幅大于s2 则卖出s2买入s1
            if (h1.values[-1] - h1.values[0])/h1.values[-1] > (h2.values[-1] - h2.values[0])/h2.values[-1]:
                close_position('000002', s2)
                open_position('000001', 1000)

        # 如果都没有持仓，则开仓
        else:
            if (h1.values[-1] - h1.values[0])/h1.values[-1] < (h2.values[-1] - h2.values[0])/h2.values[-1]:
                open_position('000002', 1000)
            else:
                open_position('000001', 1000)




