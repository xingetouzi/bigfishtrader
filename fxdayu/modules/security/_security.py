# encoding: utf-8

import os
import pandas as pd

from fxdayu.models.data import Security
from fxdayu.context import ContextMixin
from fxdayu.utils.api_support import api_method

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "security.csv")


class SecurityPool(ContextMixin):
    DF = None
    count = 0

    def __new__(cls, *args, **kwargs):
        if cls.DF is None:
            cls.DF = pd.DataFrame.from_csv(_PATH)
            cls.DICT_SID = {k: cls._to_security(s) for k, s in cls.DF.iterrows()}
            cls.DICT_STR = {s.symbol: s for s in cls.DICT_SID.values()}
        return object.__new__(cls, *args, **kwargs)

    def __init__(self, context, environment, data):
        ContextMixin.__init__(self, context, environment, None)
        self.columns = self.DF.reset_index().columns

    @classmethod
    def _to_security(cls, series):
        c = Security()
        for field in cls.DF.columns:
            setattr(c, field, series[field])
        c.sid = series.name
        return c

    @classmethod
    def _miss_security(cls, s):
        # TODO warning
        s = str(s)
        cls.count += 1
        security = Security()
        security.localSymbol = s
        security.sid = - cls.count
        security.gateway = "UNKNOWN"
        security.currency = "UNKNOWN"
        security.exchange = "UNKNOWN"
        security.secType = "UNKNOWN"
        security.symbol = s
        cls.DICT_SID[security.sid] = security
        cls.DICT_STR[security.symbol] = security
        return security

    @api_method
    def sid(self, s):
        """
        接受一个整数值来通过sid来查找Security（证券品种）对象。

        Args:
            s(int): Security的id。

        Returns:
            fxdayu.models.data.Security: 对应的证券品种对象。若找不到品种，返回None。
        """
        if s in self.DICT_SID:
            return self.DICT_SID[s]
        else:
            return self._miss_security(s)

    @api_method
    def symbol(self, s):
        """
        接受一个字符串来查找一个Security（证券品种）对象。

        Args:
            s(str): 表示Security代码的字符串。

        Returns:
            fxdayu.models.data.Security: 对应的证券品种对象。若找不到品种，返回None。
        """
        if s in self.DICT_STR:
            return self.DICT_STR[s]
        else:
            return self._miss_security(s)

    @api_method
    def symbols(self, *s):
        """
        通过字符串查找多个证券。每个参数都必须是字符串，并用逗号分隔。

        Args:
            s(list(str)): 字符串列表

        Returns:
            list(fxdayu.models.data.Security): 返回Security列表。对应输入中的每一字符串，返回列表
            中有一个证券品种对象。若找不到品种，对应项为None。
        """
        if s:
            item = s[0]
            if isinstance(item, str):
                return [self.symbol(s) for s in s]
            elif isinstance(item, int):
                return [self.sid(s) for s in s]
        else:
            return []

    def link_context(self):
        self.environment["sid"] = self.sid
        self.environment["symbol"] = self.symbol
        self.environment["symbols"] = self.symbols


if __name__ == "__main__":
    security = SecurityPool(object(), {}, None).symbol("000003")
    print(security.to_dict())
    security = SecurityPool(object(), {}, None).symbol("000003")
    print(security.to_dict())
    for security in SecurityPool.DICT_SID.values():
        if len(security.symbol) != 6 or len(security.localSymbol) != 6:
            print(security.to_dict())
