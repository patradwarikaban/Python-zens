
class Template(object):
    def __init__(
            self,
            kwargs
    ):
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.__dict__.update(kwargs)
