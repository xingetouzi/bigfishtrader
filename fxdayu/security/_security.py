import os
import pandas as pd

from fxdayu.models.data import Security
from fxdayu.context import ContextMixin

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "security.csv")


class SecurityPool(ContextMixin):
    DF = None

    def __new__(cls, *args, **kwargs):
        if cls.DF is None:
            cls.DF = pd.DataFrame.from_csv(_PATH)
            cls.DICT_STR = {k: cls._to_security(s) for k, s in cls.DF.iterrows()}
            cls.DICT_SID = {s.sid: s for s in cls.DICT_STR.values()}
        return object.__new__(cls, *args, **kwargs)

    def __init__(self, context, environment, data):
        ContextMixin.__init__(self, context, environment, None)
        self.columns = self.DF.reset_index().columns

    @classmethod
    def _to_security(cls, series):
        c = Security()
        for field in cls.DF.columns:
            setattr(c, field, series[field])
        c.longName = series.name
        return c

    def sid(self, sid):
        if sid in self.DICT_SID:
            return self.DICT_SID[sid]
        else:
            # TODO warning
            pass

    def symbol(self, symbol):
        """

        Args:
            symbol(str):

        Returns:
            Security:
        """
        if symbol in self.DICT_STR:
            return self.DICT_STR[symbol]
        elif symbol in self.DICT_SID:
            return self.DICT_SID[symbol]
        # TODO warning

    def symbols(self, *symbols):
        return [self.symbol(s) for s in symbols]

    def link_context(self):
        self.environment["sid"] = self.sid
        self.environment["symbol"] = self.symbol
        self.environment["symbols"] = self.symbols


if __name__ == "__main__":
    security = SecurityPool(object(), {}, None).symbol("EUR.USD")
    print(security.to_dict())
