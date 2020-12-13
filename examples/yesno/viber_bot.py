#!/usr/bin/env python

import asyncio
import logging

from envparse import env  # External dependencies

from limpopo.services import ViberService, ViberSettings
from limpopo.storages import PostgreStorage
from .poll import quiz


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    settings = ViberSettings(
            name=env("VIBER_NAME"),
            token=env("VIBER_TOKEN"),
            http_host=env("VIBER_HTTP_HOST"),
            http_port=env("VIBER_HTTP_PORT", cast=int)
    )

    storage = PostgreStorage("postgresql+asyncpg://postgres:123123@0.0.0.0:5432/alfed")

    viber_service = ViberService(quiz, storage=storage, settings=settings)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(viber_service.run_forever())
