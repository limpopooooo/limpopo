Limpopo
=======

**limpopo** is a framework that allows you to create an application for conducting surveys in the following messengers:

- Telegram

- Viber


Installing
----------

Install and update using `pip`:

.. code-block:: text

    pip install limpopo


A Simple Example
----------------

.. code-block:: python

        import asyncio
        import signal
        import logging
            
        from envparse import env # External dependencies

        from limpopo.question import Question
        from limpopo.services import TelegramService
        from limpopo.storages import PostgreStorage


        yesno_question = Question(
            topic="Choose yes or no!",
            choices={
                "yes": "Yes",
                "no": "No"
            }
        )


        async def quiz(dialog):
            answer = await dialog.ask(yesno_question)

            if answer.text == yesno_question.choices["yes"]:
                await dialog.tell("Your choice is `Yes`")
            else:
                await dialog.tell("Your choice is `No`")


        if __name__ == "__main__":
            logging.basicConfig(level=logging.INFO)

            settings = {
                "session": env("TELEGRAM_SESSION_NAME"),
                'api_id': env("TELEGRAM_API_ID", cast=int),
                'api_hash': env("TELEGRAM_API_HASH"),
                'token': env("TELEGRAM_BOT_TOKEN"),
                "dialog": {
                    "answer_timeout": env("TELEGRAM_ANSWER_TIMEOUT", cast=int)
                },
            }

            storage = PostgreStorage(env("TELEGRAM_POSTGRES_URI"))

            telegram_service = TelegramService(quiz, storage=storage, settings=settings)

            def stop_callback():
                logging.info("Graceful shutdown")
                asyncio.ensure_future(telegram_service.stop())

            loop = asyncio.get_event_loop()

            loop.add_signal_handler(signal.SIGTERM, stop_callback)
            loop.add_signal_handler(signal.SIGHUP, stop_callback)
            loop.add_signal_handler(signal.SIGINT, stop_callback)

            loop.run_until_complete(telegram_service.run_forever())


Design
------

limpopo provides the following entities, by which an poll-application is created:

1. Service (limpopo provides `TelegramService`, `ViberService`)

2. Storage (limpopo provides `PostgreStorage`, `FakeStorage`)

3. Dialog

4. Question


Development
-----------

How to lint and format the code
-------------------------------

We are using `pre-commit <https://pre-commit.com/>`_ tool,
see `installation guides <https://pre-commit.com/#installation>`_.

.. code-block:: text

    pre-commit install
    pre-commit run -a
