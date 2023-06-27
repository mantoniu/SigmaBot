from enum import Enum

class Bot_Status(Enum):
    PATTERN_ERROR = "0"
    WAITING_OPINION = "1"
    WAITING_PATTERN = "2"
    ASK_REFINEMENTS = "3"
    WAITING_REFINEMENT = "4"
    RECEIVED_REFINEMENT = "5"
    ONE_REFINEMENT = "6"
    WORD_NOT_FOUND = "7"