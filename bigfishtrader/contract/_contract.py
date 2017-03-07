import os
import pandas as pd

from bigfishtrader.models.data import ContractData
from bigfishtrader.context import ContextMixin

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contract.csv")


class ContractPool(ContextMixin):
    DF = None

    def __new__(cls, *args, **kwargs):
        if cls.DF is None:
            cls.DF = pd.DataFrame.from_csv(_PATH)
        return object.__new__(cls, *args, **kwargs)

    def __init__(self, context, environment):
        ContextMixin.__init__(self, context, environment)
        self.columns = self.DF.reset_index().columns

    def contract(self, symbol):
        if symbol in self.DF.index:
            series = self.DF.loc[symbol]
            c = ContractData()
            for field in self.DF.columns:
                setattr(c, field, series[field])
            c.longName = series.name
            return c
        else:
            # TODO warning
            return None

    def link_context(self):
        self.environment["contract"] = self.contract

if __name__ == "__main__":
    contract = ContractPool(object(), {}).contract("EUR.USD")
    print(contract.to_dict())
