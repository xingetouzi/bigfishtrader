from datetime import datetime

from bigfishtrader.data.base import AbstractDataSupport


class PanelDataSupport(AbstractDataSupport):
    def __init__(self, panel, context=None):
        """

        Args:
            panel(pandas.Panel):
        """
        super(PanelDataSupport, self).__init__()
        self._panel = panel
        self._date_index = self._panel.iloc[0].index
        self._context = context

    @property
    def date_index(self):
        return self._date_index

    def set_context(self, context):
        self._context = context

    def instance(self, tickers, fields, frequency, start=None, end=None, length=None):
        pass

    def _get_ending_index(self, end):
        if isinstance(end, int):
            return end  # ending bar's number (start from 1) was given
        elif isinstance(end, datetime):
            return self._date_index.searchsorted(end, side="R")  # ending bar's datetime was given
        else:
            raise TypeError()

    def _get_starting_index(self, start):
        if isinstance(start, int):
            return start - 1  # starting bar's number (start from 1) was given
        elif isinstance(start, datetime):
            return self._date_index.searchsorted(start, side="L")  # starting bar's datetime was given
        else:
            raise TypeError()

    def history(self, tickers, fields, frequency, start=None, end=None, length=None):
        if isinstance(tickers, str):
            tickers = [tickers]
        if isinstance(fields, str):
            fields = [fields]
        if start:
            start_index = self._get_starting_index(start)
            if end:
                end_index = self._get_ending_index(end)
            elif length:
                end_index = start_index + length
            else:
                end_index = self._context.real_bar_num  # using current bar number in context
        else:
            if end:
                end_index = self._get_ending_index(end)
            else:
                end_index = self._context.real_bar_num  # using current bar number in context
            start_index = end_index - length
        if len(tickers) == 1:
            df = self._panel[tickers[0]].iloc[start_index:end_index]
            if fields:
                if len(fields) == 1:
                    return df[fields[0]]
                else:
                    return df[fields]
            else:
                return df
        else:
            panel = self._panel[tickers].iloc[:, start_index:end_index]
            if fields:
                if len(fields) == 1:
                    return panel.loc[:, :, fields[0]]
                else:
                    # TODO whether it is necessary to set copy=False
                    return panel.loc[:, :, fields].swapaxes(0, 2)
            else:
                return panel.swapaxes(0, 2)

    def current(self, tickers, fields=None):
        if isinstance(tickers, str):
            tickers = [tickers]
        if isinstance(fields, str):
            fields = [fields]
        if len(tickers) == 1:
            series = self._panel[tickers[0]].iloc[self._context.real_bar_num - 1]
            if fields:
                if len(fields) == 1:
                    return series[fields[0]]
                else:
                    return series[fields]
            else:
                return series
        else:
            df = self._panel[tickers].iloc[:, self._context.real_bar_num - 1].T
            if fields:
                if len(fields) == 1:
                    return df[fields[0]]
                else:
                    return df[fields]
            else:
                return df
