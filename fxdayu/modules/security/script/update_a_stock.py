# encoding: utf-8

import tushare as ts
import pandas as pd

FILE = "industry_classified.csv"

EXCHANGE_MAP = {
    "000": "szse",
    "001": "szse",
    "002": "szse",
    "200": "szse",
    "300": "szse",
    "600": "sse",
    "601": "sse",
    "603": "sse",
    "900": None,  # TODO B股处理
}

SEC_TYPE = "STK"

if __name__ == "__main__":
    stock_info = ts.get_industry_classified()
    stock_info.index = stock_info["code"].astype(int)
    stock_info.index.name = "sid"
    stock_info.sort_index(inplace=True)
    stock_info["code"] = stock_info["code"].map(lambda x: x.zfill(6))
    stock_info.rename_axis({"code": "symbol"}, axis=1, inplace=True)
    stock_info["localSymbol"] = stock_info["symbol"]
    stock_info["exchange"] = stock_info["symbol"].map(lambda x: EXCHANGE_MAP[x[:3]])
    stock_info["currency"] = ["CNY"] * len(stock_info)
    stock_info["gateway"] = ["STOCK"] * len(stock_info)
    stock_info["secType"] = ["STK"] * len(stock_info)
    stock_info.dropna(inplace=True)
    stock_info = stock_info.append(pd.Series({"symbol": "PLACEHOLDER", "localSymbol": "PLACEHOLDER"}, name=-1))
    stock_info.to_csv(FILE, encoding="utf-8")
