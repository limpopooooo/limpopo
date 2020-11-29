from .archetype import ArchetypeDialog, ArchetypeService


class ViberDialog(ArchetypeDialog):
    def prepare_message(self, question):
        message = question.topic

        buttons = []
        if question.options:
            for option in question.options:
                buttons.append(option)

        return {"message": message, "buttons": buttons}


class ViberService(ArchetypeService):
    def __init__(self, quiz, storage):
        super().__init__(quiz, storage)

    def run_forever(self):
        pass

    async def send_message(self, user_id, *args, **kwargs):
        pass
