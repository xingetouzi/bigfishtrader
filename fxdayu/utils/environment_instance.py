import threading

context = threading.local()


def get_environment_instance():
    return getattr(context, "environment", None)


def set_environment_instance(environment):
    context.environment = environment
