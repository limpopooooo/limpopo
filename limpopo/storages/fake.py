from .archetype import ArchetypeStorage


class FakeStorage(ArchetypeStorage):
    async def save_question_and_answer(self, question, answer):
        pass

    async def save_dialog(self, dialog):
        pass

    async def save_function_call(self, dialog, funcs_hash: int):
        pass
