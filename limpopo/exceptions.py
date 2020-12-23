class BaseLimpopoException(Exception):
    pass


class ParameterError(BaseLimpopoException):
    pass


class QuestionParameterWrongType(ParameterError):
    pass


class VideoParameterWrongType(ParameterError):
    pass


class MarkdownMessageParameterWrongType(ParameterError):
    pass


class QuestionChoicesWrongType(ParameterError):
    pass


class QuestionWrongAnswer(BaseLimpopoException):
    pass


class SettingsError(BaseLimpopoException):
    pass


class DialogStopped(BaseLimpopoException):
    pass
