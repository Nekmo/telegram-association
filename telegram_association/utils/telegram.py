import time


def get_name(name_data):
    return ' '.join(filter(lambda x: x, [name_data.first_name, name_data.last_name]))


def securize_message(fn):
    def wrapper(message, *args, **kwargs):
        if time.time() - message.date > 10:
            return
        return fn(message, *args, **kwargs)
    return wrapper
