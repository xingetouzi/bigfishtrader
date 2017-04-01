# encoding: utf-8

from functools import wraps

import fxdayu.api
from fxdayu.utils.environment_instance import get_environment_instance, set_environment_instance


class EnvironmentContext(object):
    def __init__(self, environment):
        self.environment_instance = environment

    def __enter__(self):
        self.old_environment_instance = get_environment_instance()
        set_environment_instance(self.environment_instance)

    def __exit__(self, exc_type, exc_val, exc_tb):
        set_environment_instance(self.old_environment_instance)


def api_method(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        environment = get_environment_instance()
        if environment is None:
            raise RuntimeError(
                'api method %s must be called during a simulation.'
                % f.__name__
            )
        return environment[f.__name__](*args, **kwargs)

    wrapper.is_api_method = True  # 用于自动生成fxdayu.
    setattr(fxdayu.api, f.__name__, wrapper)
    if f.__name__ not in fxdayu.api.__all__:
        fxdayu.api.__all__.append(f.__name__)
    return f


def callback_method(name):
    def callback(f):
        def wrapper(*args, **kwargs):
            environment = get_environment_instance()

            try:
                environment[name](*args, **kwargs)
            except KeyError:
                pass

        return wrapper
    return callback