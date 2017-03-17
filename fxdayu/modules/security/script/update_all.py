import os
import logging

import pandas as pd


BASE_PATH = os.path.dirname(os.path.abspath(__file__))
RESULT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_FILE_LIST = ["industry_classified.csv"]
RESULT_FILE = "security.csv"
columns = ["symbol", "localSymbol", "name", "secType", "exchange", "currency", "gateway"]

if __name__ == "__main__":
    result = pd.DataFrame.from_csv(os.path.join(RESULT_PATH, RESULT_FILE))
    for filename in BASE_FILE_LIST:
        try:
            df = pd.DataFrame.from_csv(os.path.join(BASE_PATH, filename)).dropna()
            df = df[columns]
            result = pd.concat([result, df])
            result = result.drop_duplicates()
        except Exception as e:
            logging.exception(e)
            continue
    result.to_csv(os.path.join(RESULT_PATH, RESULT_FILE))

