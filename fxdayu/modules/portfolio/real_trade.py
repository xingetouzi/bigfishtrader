# encoding:utf-8
from fxdayu.modules.portfolio.handlers import PortfolioHandler, PositionData
from pymongo import MongoClient
from datetime import datetime


class TradingPortfolio(PortfolioHandler):
    """
    db_config(dict): 数据库配置(在持仓变动时往数据库存入当前持仓和现金快照)
        sample:  {"host": "localhost", //地址
                  "port": 27017, //端口号
                  "db": "portfolios", // 数据库名
                  "collection": "TradeDemo", // 表名
                  "user": {"name": "XXX", "password": "XXX"} // 对应db的用户权限，没有可以不填
    """

    def __init__(self, engine, mode=None, sync_policy=None, execution_mode=None, has_frozen=False, db_config=None):
        super(TradingPortfolio, self).__init__(engine, mode, sync_policy, execution_mode, has_frozen)
        if isinstance(db_config, dict):
            self.db = db_config.pop('db')
            self.col = db_config.pop('collection')
            self.user = db_config.pop('user', {})
            self.db_config = db_config
            self.client = self.connect()
            self.init_position()
        else:
            raise TypeError("db_config must be %s not %s" % (type(dict()), type(db_config)))

    def connect(self):
        client = MongoClient(**self.db_config)
        if len(self.user):
            client[self.db].authenticate(**self.user)
        return client

    def get_memory(self):
        try:
            return self.client[self.db][self.col]
        except Exception as e:
            print e
            self.client = self.connect()
            return self.client[self.db][self.col]

    def init_position(self):
        collection = self.get_memory()
        doc = collection.find_one(sort=[('datetime', -1)])
        if doc:
            self._cash = doc['cash']
            positions = {code: self.create_position(dct) for code, dct in doc['positions'].items()}
            if self._mode == self.MODE.BROKER.value:
                self._broker_positions = positions
            else:
                self._strategy_positions = positions
        else:
            self.snap_shot()

    @staticmethod
    def create_position(dct):
        position = PositionData()
        for key, value in dct.items():
            setattr(position, key, value)
        return position

    def on_execution(self, event, kwargs=None):
        super(TradingPortfolio, self).on_execution(event, kwargs)
        self.snap_shot()

    def snap_shot(self):
        doc = {'datetime': datetime.now(),
               'cash': self._cash,
               'positions': {code: position.to_dict() for code, position in self.positions.items()}}
        collection = self.get_memory()
        collection.insert_one(doc)