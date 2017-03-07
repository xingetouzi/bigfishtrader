class Environment(object):
    __slots__ = ["_d"]

    def __init__(self):
        self._d = {}

    def __getattr__(self, item):
        return self._d[item]

    def __setitem__(self, key, value):
        if key == "_d":
            super(Environment).__setattr__(key, value)
        else:
            self._d[key] = value

    def __getitem__(self, item):
        return self._d[item]

    @property
    def dct(self):
        return self._d


if __name__ == "__main__":
    environment = Environment()
    environment["a"] = 1
    print(environment["a"])
    environment["b"] = 1
    print(environment.a)
