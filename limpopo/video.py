import os
import socket
import time
import typing
from urllib.parse import urlparse

from .exceptions import VideoParameterWrongType


class Video:
    def __init__(self, path_to_file: str, width=None, height=None, url: typing.Optional[str] = None):
        if not isinstance(path_to_file, str):
            raise VideoParameterWrongType(
                "Field `path_to_file`: is expected type `str`, received: {}".format(
                    type(path_to_file)
                )
            )

        if not os.path.exists(path_to_file):
            raise VideoParameterWrongType(
                "File `{}` doesn't exist".format(type(path_to_file))
            )

        if not os.path.isfile(path_to_file):
            raise VideoParameterWrongType(
                "Path `{}` it's not a file".format(type(path_to_file))
            )

        if not (url is None or isinstance(url, str)):
            raise VideoParameterWrongType(
                "Field `url`: is expected type `str`, received: {}".format(type(url))
            )

        if url:
            parse_result = urlparse(url)

            if parse_result.hostname is None:
                raise VideoParameterWrongType(
                    "Field `url`: #{} doesn't have hostname".format(type(url))
                )

            if not self._resolve_url(parse_result):
                raise VideoParameterWrongType(
                    "Field `url`: #{} doesn't resolve".format(type(url))
                )

        self.path_to_file = path_to_file
        self.url = url
        self.width = width
        self.height = height

    @staticmethod
    def _resolve_url(parse_result) -> bool:
        for _ in range(3):
            try:
                socket.getaddrinfo(
                    parse_result.hostname, parse_result.port, socket.AF_INET
                )
                return True
            except socket.error:
                time.sleep(1)

        return False
