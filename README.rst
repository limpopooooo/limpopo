Limpopo
=====

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

    import envparse import env  # External dependencies
    
    from limpopo.question import Question
    from limpopo.storages import FakeStorage
    from limpopo.services import TelegramService

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
----------------

limpopo provides the following entities, by which an poll-application is created:  

1. Service (limpopo provices `TelegramService`, `ViberService`)

2. Storage (limpopo provides `PosgtreStorage`, `FakeStorage`)

3. Dialog

4. Question
