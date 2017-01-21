from datetime import datetime

from bigfishtrader.data.base import AbstractDataSupport
import pandas as pd


class PanelDataSupport(AbstractDataSupport):
    def __init__(self, panel, context=None, side="L", frequency='D'):
        """
        Create a PannelDataSupport with a pandas.Panel object.
        Panel's inner data can be accessed using method history() and current()
        context is a optional parameters, to

        Args:
            panel(pandas.Panel): Panel where real data stored in
            context: default end bar number refer to context.real_bar_num
            side(str): "L" or "R", "L" means bar's datetime refer to it's start time
                "R" means bar's datetime refer to it's end time
        """
        super(PanelDataSupport, self).__init__()
        self._panel = panel
        self._frequency = frequency
        self._others = {}
        self._date_index = self._panel.iloc[0].index
        self._side = side
        self._context = context

    @property
    def date_index(self):
        """
        Panel's datetime index, that is to it's major axis, which contains datetime of
        all the bars in panel.

        Returns:
            pandas.DatetimeIndex: Panel's datetime index
        """
        return self._date_index

    def set_context(self, context):
        """
        set the context

        Args:
            context:

        Returns:
            None
        """
        self._context = context

    def instance(self, tickers, fields, frequency, start=None, end=None, length=None):
        pass

    def _get_ending_index(self, end):
        if isinstance(end, int):
            return end  # ending bar's number (start from 1) was given
        elif isinstance(end, datetime):
            # ending bar's datetime was given
            return self._date_index.searchsorted(end, side=self._side)
        else:
            raise TypeError()

    def _get_starting_index(self, start):
        if isinstance(start, int):
            return start - 1  # starting bar's number (start from 1) was given
        elif isinstance(start, datetime):
            # starting bar's datetime was given
            return self._date_index.searchsorted(start, side=self._side)
        else:
            raise TypeError()

    def history(self, tickers, fields, frequency, start=None, end=None, length=None):
        """


        Args:
            tickers:
            fields:
            frequency:
            start:
            end:
            length:

        Returns:

        """
        if isinstance(tickers, str):
            tickers = [tickers]
        if isinstance(fields, str):
            fields = [fields]
        if frequency == self._frequency:
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
        else:
            pn = self._others[frequency]

    def current(self, tickers, fields=None):
        """

        Args:
            tickers:
            fields:

        Returns:

        """
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

    def pop(self, item):
        return self._panel.pop(item)

    def insert(self, item, frame, frequency=None):
        if not frequency or frequency == self._frequency:
            self._panel[item] = frame
        else:
            self._others.setdefault(frequency, pd.Panel())[item] = frame


class Context(object):
    @property
    def current_time(self):
        return datetime.now()


class MultiPanelData(AbstractDataSupport):
    def __init__(self, context=None):
        super(MultiPanelData, self).__init__()
        self._panels = {}
        self._frequency = None
        self.major_axis = None
        self._context = context if context is not None else Context()

    def set_context(self, context):
        self._context = context

    def init(self, frequency, **ticker_frame):
        panel = self.insert(frequency, **ticker_frame)
        self._frequency = frequency
        self.major_axis = panel.major_axis

    def insert(self, frequency, **ticker_frame):
        panel = self._panels.get(frequency, None)
        if panel is not None:
            for ticker, frame in ticker_frame.items():
                panel[ticker] = frame

        else:
            panel = pd.Panel.from_dict(ticker_frame)
            self._panels[frequency] = panel
        return panel

    def drop(self, frequency, *tickers):
        panel = self._panels.get(frequency, None)
        if panel is not None:
            if len(tickers):
                for ticker in tickers:
                    panel.pop(ticker)
            else:
                self._panels.pop(frequency)

    def current(self, tickers, fields=None):
        panel = self._panels[self._frequency]
        end = pd.to_datetime(self._context.current_time)
        index = panel.major_axis.searchsorted(end, 'left')
        if index >= len(panel.major_axis):
            index = -1

        if isinstance(tickers, str):
            frame = panel[tickers]
            return frame[fields].iloc[index, :]
        elif isinstance(tickers, list):
            panel = panel[tickers]
            return panel.iloc[:, index, :].T[fields]
        else:
            raise TypeError('type of tickers must be str or list, not %s' % type(tickers))

    def history(
            self, tickers, fields, frequency,
            start=None, end=None, length=None
    ):
        if isinstance(tickers, str):
            tickers = [tickers]
        panel = self._panels[frequency]
        if start:
            start = pd.to_datetime(start)
            begin = panel.major_axis.searchsorted(start)
            if length:
                if len(tickers) == 1:
                    return panel[tickers[0]][fields].iloc[begin:begin+length]
                else:
                    return panel[tickers][:, begin:begin+length, fields]

            else:
                end = pd.to_datetime(end) if end else pd.to_datetime(self._context.current_time)
                stop = panel.major_axis.searchsorted(end)

                if stop < len(panel.major_axis):
                    if panel.major_axis[stop] <= end:
                        stop += 1
                else:
                    stop = None

                if len(tickers) == 1:
                    frame = panel[tickers[0]]
                    return frame.iloc[begin:stop][fields]
                else:
                    panel = panel[tickers]
                    return panel[:, begin:stop, fields]
        if end:
            end = pd.to_datetime(end)
            stop = panel.major_axis.searchsorted(end)

            if stop < len(panel.major_axis):
                if panel.major_axis[stop] <= end:
                        stop += 1
            else:
                stop = None

            if length:
                if len(tickers) == 1:
                    return panel[tickers[0]][fields].iloc[stop-length:stop]
                else:
                    return panel[tickers][:, stop-length:stop, fields]
            elif start:
                start = pd.to_datetime(start)
                begin = panel.major_axis.searchsorted(start)
                if len(tickers) == 1:
                    frame = panel[tickers[0]]
                    return frame.iloc[begin:stop][fields]
                else:
                    panel = panel[tickers]
                    return panel[:, begin:stop, fields]
            else:
                if len(tickers) == 1:
                    return panel[tickers[0]][fields].iloc[:stop]
                else:
                    return panel[tickers][:, :stop, fields]
        else:
            end = pd.to_datetime(self._context.current_time)
            stop = panel.major_axis.searchsorted(end)
            begin = stop - length if length else None
            if stop < len(panel.major_axis):
                if panel.major_axis[stop] <= end and frequency == self._frequency:
                        stop += 1
                        begin = begin + 1 if begin else None
            else:
                stop = None

            if len(tickers) == 1:
                return panel[tickers[0]][fields].iloc[begin:stop]
            else:
                return panel[tickers][:, begin:stop, fields]
        # else:
        #     raise TypeError('history() takes at least one param among start, end and length')