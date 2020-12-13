#!/usr/bin/env python

import asyncio
import logging
import signal

from envparse import env  # External dependencies

from limpopo.services import TelegramService, TelegramSettings
from limpopo.storages import PostgreStorage

from .poll import quiz


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    settings = TelegramSettings(
        session=env("TELEGRAM_SESSION_NAME"),
        token=env("TELEGRAM_BOT_TOKEN"),
        api_id=env("TELEGRAM_API_ID", cast=int),
        api_hash=env("TELEGRAM_API_HASH"),
        answer_timeout=env("TELEGRAM_ANSWER_TIMEOUT", cast=int)

    )

    storage = PostgreStorage(env("TELEGRAM_POSTGRES_URI"))

    telegram_service = TelegramService(quiz, storage=storage, settings=settings)

    def stop_callback():
        logging.info("Graceful shutdown")
        asyncio.ensure_future(telegram_service.stop())

    loop = asyncio.get_event_loop()

    loop.add_signal_handler(signal.SIGINT, stop_callback)

    loop.run_until_complete(telegram_service.run_forever())
