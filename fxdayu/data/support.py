try:
    from _dataframe_data_support import PanelDataSupport, MultiPanelData
    from _mongo_data_support import MongoDataSupport, MultiDataSupport
except ImportError:
    from ._dataframe_data_support import PanelDataSupport, MultiPanelData
    from ._mongo_data_support import MongoDataSupport, MultiDataSupport

__all__ = [
    "PanelDataSupport",
    "MongoDataSupport",
    "MultiDataSupport",
    "MultiPanelData",
]
