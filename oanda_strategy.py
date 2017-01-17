from bigfishtrader.operation import *
from datetime import datetime
import pandas as pd


def initialize(context, data):
    context.ticker = 'EUR_USD'
    context.period = 'D'
    data.init(context.ticker, context.period, datetime(2016, 12, 1))


def handle_data(context, data):
    pass