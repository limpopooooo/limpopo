import typing

from .dto import Answer
from .exceptions import (
    QuestionChoicesWrongType,
    QuestionParameterWrongType,
    QuestionWrongAnswer,
)
from .helpers import markdown_to_plain_text

ANY = typing.TypeVar('ANY')


class Question:
    def __init__(
        self,
        topic: str,
        choices: typing.Union[
            typing.Dict[typing.Any, str], typing.List[str], ANY
        ] = ANY,
        strict_choose: bool = True,
        column_count: int = 2,
        inline: bool = True,
    ):
        if not isinstance(topic, str):
            raise QuestionParameterWrongType(
                "Field `topic`: is expected type `str`, received: {}".format(
                    type(topic)
                )
            )

        if not isinstance(strict_choose, bool):
            raise QuestionParameterWrongType(
                "Field `strict_choose` is expected type `bool`, received: {}".format(
                    type(strict_choose)
                )
            )

        if not isinstance(column_count, int):
            raise QuestionParameterWrongType(
                "Field `column_count`: is expected type `int`, received: {}".format(
                    type(column_count)
                )
            )

        #  Check that choices is ANY or dict/list of string, otherwise raise Questionexception
        if not self._validate_choices(choices):
            raise QuestionChoicesWrongType(
                "Non empty dict or list of string or ANY is expected, received: {}".format(
                    choices
                )
            )

        self.topic = topic
        self.plain_text = markdown_to_plain_text(topic)
        self.choices = choices
        self.strict_choose = strict_choose
        self.column_count = column_count
        self.inline = inline

    @property
    def options(self):
        if isinstance(self.choices, dict):
            return list(self.choices.values())
        elif isinstance(self.choices, list):
            return self.choices

    def _validate_choices(self, choices) -> bool:
        if choices == ANY:
            return True
        if choices and isinstance(choices, dict):
            iterator = (value for _, value in choices.items())
        elif choices and isinstance(choices, list):
            iterator = choices
        else:
            return False

        for value in iterator:
            if not isinstance(value, str):
                return False

        return True

    def validate_answer(self, answer: Answer):
        if (
            self.strict_choose
            and self.choices != ANY
            and answer.text not in self.options
        ):
            raise QuestionWrongAnswer(
                "Question: {}\nchoose invalid answer: {}".format(
                    self.topic, answer.text
                )
            )

        return True
