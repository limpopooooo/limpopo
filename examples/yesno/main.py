#!/usr/bin/env python

from limpopo.services import TelegramService
from limpopo.storages import FakeStorage

from .quiz import quiz

if __name__ == "__main__":
    # NOTE: please enter your Telegram credentials to run this example
    settings = {
        "token": "123",  # telegram bot's token
        "api_id": 123,
        "api_hash": "123",
    }

    storage = FakeStorage()

    TelegramService(quiz=quiz, storage=storage, settings=settings).run_forever()
