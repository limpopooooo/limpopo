class BaseLimpopoException(Exception):
    pass


class QuestionParameterWrongType(BaseLimpopoException):
    pass


class VideoParameterWrongType(BaseLimpopoException):
    pass


class QuestionChoicesWrongType(BaseLimpopoException):
    pass


class QuestionWrongAnswer(BaseLimpopoException):
    pass


class SettingsError(BaseLimpopoException):
    pass


class DialogStopped(BaseLimpopoException):
    pass
