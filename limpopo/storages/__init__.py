from .fake import FakeStorage
from .postgres.storage import PostgreStorage

__all__ = [
    'FakeStorage',
    'PostgreStorage',
]
