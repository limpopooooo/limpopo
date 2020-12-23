from .helpers import markdown_to_plain_text


class MarkdownMessage:
    def __init__(self, text: str):
        if not isinstance(text, str):
            raise Exception("")

        self.text = text
        self.plain_text = markdown_to_plain_text(text)
