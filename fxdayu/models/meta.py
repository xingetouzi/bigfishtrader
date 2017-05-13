from collections import OrderedDict

LAZY_DATA_ATTR = "_data"


class BaseData(object):
    def to_dict(self):
        return self.__dict__

    def get_lazy(self):
        return LazyBaseData(self)


class LazyBaseData(object):
    def __init__(self, data):
        self._data = data

    def __getattr__(self, item):
        if item in self._data.__dict__:
            return getattr(self._data, item)


if __name__ == "__main__":
    import timeit


    class TestData(BaseData):
        __slots__ = ["test"]

        def __init__(self):
            self.test = "test"


    class PropertyTestData(object):
        def __init__(self, data):
            self._data = data

        @property
        def test(self):
            return self._data.test


    # print timeit.timeit("copy.copy(test).test", "from __main__ import TestData\nimport copy\ntest=TestData()")
    print(timeit.timeit("test.test",
                        "from __main__ import LazyBaseData, TestData\ntest = TestData()\ntest = LazyBaseData(test)"))
    print(timeit.timeit("test.test",
                        "from __main__ import PropertyTestData, TestData\n"
                        "test = TestData()\ntest = PropertyTestData(test)"))
    print(timeit.timeit("test.test", "from __main__ import LazyBaseData, TestData\ntest = TestData()\n"))
