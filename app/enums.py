from enum import Enum


class SlackEvent(Enum):
    MESSAGE_POSTED = 1
    MESSAGE_CHANGED = 2
    MESSAGE_DELETED = 3


class SauronEvent(Enum):
    THREAD_SPROUTING = 1
    THREAD_BURNING = 2
    THREAD_CONTINUED = 3
