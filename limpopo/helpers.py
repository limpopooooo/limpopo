from io import StringIO

from markdown import Markdown
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


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


async def with_retry(coro, num_attempts=5, exceptions=Exception, stop_callback_coro=None):
    try:
        async for attempt in AsyncRetrying(
            wait=wait_exponential(min=1, max=60),
            stop=stop_after_attempt(num_attempts),
            retry=retry_if_exception_type(exceptions),
        ):
            with attempt:
                return await coro()
    except RetryError:
        if stop_callback_coro:
            await stop_callback_coro()
        raise
