import enum
from asyncio import Event
from dataclasses import dataclass


@dataclass
class Message:
    id: int
    text: str


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


class Messengers(enum.Enum):
    telegram = 1
    viber = 2
    whatapp = 3
