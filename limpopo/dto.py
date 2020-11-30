import enum
import typing
from asyncio import Event
from dataclasses import dataclass


class Messengers(enum.Enum):
    telegram = 1
    viber = 2
    whatapp = 3


@dataclass
class Message:
    id: int
    text: str


@dataclass
class Respondent:
    id: str
    messenger: Messengers
    username: typing.Optional[str] = None
    first_name: typing.Optional[str] = None
    last_name: typing.Optional[str] = None
    extra_data: typing.Optional[dict] = None

    def __post_init__(self):
        if not isinstance(self.id, str):
            raise ValueError("Field `id` must have type str")


class Answer(Event):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text = None

    def clear(self):
        self.text = None
        return super().clear()

    def set(self, text):
        self.text = text
        return super().set()
