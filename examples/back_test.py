from bigfishtrader.backtest import stock_backtest as back_test
import pandas as pd
from examples import stock_strategy

if __name__ == '__main__':
    portfolio = back_test.back_test(strategy=stock_strategy)
    print(
        pd.DataFrame(
            portfolio.history
        )
    )

    print(
        pd.DataFrame(
            list(
                [position.show() for position in portfolio.closed_positions]
            )
        )
    )
