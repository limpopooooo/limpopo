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

    import env
    import envparse  # External dependencies
    import import
    from limpopo.question import Question
    from limpopo.services import TelegramService
    from limpopo.storages import FakeStorage

    how_are_you_question = Question(
        topic="How are you?",
        choices=[
            "fine"
        ],
        strict_choose=False
    )

    await def quiz(dialog):
        how_are_you_answer = await dialog.ask(how_are_you_question)

        if how_are_you_answer.text != "fine":
            await dialog.tell("Ohh")


    def main():
        settings = {
            'api_id': env("TELEGRAM_API_ID", cast=int),
            'api_hash': env("TELEGRAM_API_HASH", cast=str),
            'token': env("TELEGRAM_BOT_TOKEN", cast=str)
        }

        storage = FakeStorage()

        service = TelegramService(
            quiz=quiz,
            storage=storage,
            settings=settings
        )

        service.run_forever()

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
