class TemplateEngineException(Exception):
    pass


class ErrInstanceLimitMet(TemplateEngineException):
    def __init__(self):
        super().__init__("Instance limit for this service has been reached")


class ErrInvalidParameters(TemplateEngineException):
    def __init__(self, msg):
        super().__init__(msg)


class ErrBadRequest(TemplateEngineException):
    """
    Raise if malformed or missing mandatory data
    """

    def __init__(self, msg="Malformed or missing data"):
        super().__init__(msg)

