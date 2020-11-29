from .archetype import ArchetypeStorage


class FakeStorage(ArchetypeStorage):
    def save_question_and_answer(self, question, answer):
        pass

    def save_dialog(self, dialog):
        pass
