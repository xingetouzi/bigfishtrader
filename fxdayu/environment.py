class Environment(object):
    def __init__(self):
        self._public = set()
        self._d = {}

    def __getattr__(self, item):
        if item in self._d:
            return self._d[item]
        else:
            raise AttributeError(item)

    def __delitem__(self, key):
        del self._d[key]
        self._public.remove(key)

    def __setitem__(self, key, value):
        self._d[key] = value
        self._public.add(key)

    def __getitem__(self, item):
        return self._d[item]

    @property
    def private(self):
        return {k: v for k, v in self._d.items() if k not in self._public}

    def set_private(self, key, value):
        self._d[key] = value

    @property
    def public(self):
        return {k: v for k, v in self._d.items() if k in self._public}


if __name__ == "__main__":
    environment = Environment()
    environment["a"] = 1
    print(environment["a"])
    environment["b"] = 1
    print(environment.a)
