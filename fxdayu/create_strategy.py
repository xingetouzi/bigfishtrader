import click


py_file = """# encoding:utf-8
from fxdayu.api import *
from datetime import datetime


def initialize(context, data):
    pass


def handle_data(context, data):
    pass

"""


trader_str = """
if __name__ == '__main__':
    from fxdayu.trader import Trader

    trader = Trader()
"""


@click.command()
@click.option('--name', default='strategy')
@click.option('--trader', default=True)
def create_strategy(name, trader):
    strategy = py_file
    if trader:
        strategy += trader_str

    if not name.endswith('.py'):
        name += '.py'
    f = open(name, 'w')
    f.write(strategy)
    f.close()


if __name__ == '__main__':
    create_strategy()