import click
from collections import OrderedDict


frame_gap, main_gap = "\n\n", "\n"
import_list = []
import_dict = {"fxdayu.api": "*",
               "datetime": "datetime"}


def line_skip(head=0, tail=1):
    def wrapper(function):
        def jump(*args, **kwargs):
            text = function(*args, **kwargs)
            if len(text):
                return "\n"*head + text + "\n"*tail
            else:
                return text
        return jump
    return wrapper


def indent(gap=1):
    def wrapper(function):
        def wrapped(*args, **kwargs):
            return "\n".join(map(lambda x: '    '+x, function(*args, **kwargs).split("\n")))
        return wrapped
    return wrapper


def encoding(e='utf-8'):
    return "# encoding:%s\n" % e


@line_skip(tail=3)
def import_models(*args, **kwargs):
    def kws(item):
        key, value = item
        return "from %s import %s" % (key, value if isinstance(value, str) else ', '.join(value))

    a = "\n".join(map(lambda x: "import %s" % x, args))
    k = "\n".join(map(kws, kwargs.items()))

    if len(a):
        if len(k):
            return "\n".join((a, k))
        else:
            return a
    elif len(k):
        return k
    else:
        return ''


@line_skip(tail=2)
def frame_function(*args):
    args = list(args)
    for func in ['initialize', 'handle_data']:
        if func not in args:
            args.append(func)

    return frame_gap.join(map(lambda x: "def %s(context, data):\n   pass\n" % x, args))


def set_main():
    return "if __name__ == '__main__':\n"


@line_skip()
@indent()
def set_trader(*args):
    import_dict.setdefault('fxdayu.trader', []).append('Trader')
    return "trader = Trader()" + "\n" + "\n".join(args)


@line_skip()
@indent()
def set_optimizer(*args):
    import_dict.setdefault('fxdayu.trader', []).append('Optimizer')
    return "optimizer = Optimizer()" + "\n" + "\n".join(args)


executor = {
    'trader': set_trader,
    'optimizer': set_optimizer
}


writer = OrderedDict([
    ("encoding", encoding),
    ("func", frame_function),
    ("main", set_main),
    ('execute', lambda *func: ''.join(map(lambda x: executor[x](), func))),
])


@click.command()
@click.option('-n', '--name', default='strategy')
@click.option('--origin', default=None)
@click.option('-f', '--func', multiple=True)
@click.option('-e', '--execute', default=['trader'], multiple=True)
def create_strategy(name, origin, **kwargs):
    if origin:
        strategy = open(origin).read()
    else:
        strategy = []
        for key, value in writer.items():
            param = kwargs.get(key, ())
            strategy.append(value(*param))

        strategy.insert(1, import_models(*import_list, **import_dict))
        strategy = ''.join(strategy)

    if not name.endswith('.py'):
        name += '.py'
    f = open(name, 'w')
    f.write(strategy)
    f.close()


if __name__ == '__main__':
    create_strategy()