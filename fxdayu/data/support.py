try:
    from _dataframe_data_support import PanelDataSupport, MultiPanelData
    from _mongo_data_support import MongoDataSupport, MultiDataSupport
    from _tushare_data_support import TushareDataSupport
except ImportError:
    from ._dataframe_data_support import PanelDataSupport, MultiPanelData
    from ._mongo_data_support import MongoDataSupport, MultiDataSupport
    from ._tushare_data_support import TushareDataSupport

__all__ = [
    "PanelDataSupport",
    "MongoDataSupport",
    "MultiDataSupport",
    "MultiPanelData",
    "TushareDataSupport"
]
