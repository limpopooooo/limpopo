from markdown import Markdown
from io import StringIO


def unmark_element(element, stream=None):
    if stream is None:
        stream = StringIO()
    if element.text:
        stream.write(element.text)
    for sub in element:
        unmark_element(sub, stream)
    if element.tail:
        stream.write(element.tail)
    return stream.getvalue()


Markdown.output_formats["plain"] = unmark_element


def markdown_to_plain_text(markdown_text):
    converter = Markdown(output_format="plain")
    converter.stripTopLevelTags = False
    return converter.convert(markdown_text)
