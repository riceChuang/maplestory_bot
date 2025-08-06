from enum import Enum, auto


class State(Enum):
    '''流程狀態'''
    INIT = auto()
    INIT_OK = auto()
    ATTACK_ACTION = auto()
    PICK_ITEM = auto()
    MOVE_UP_OR_DOWN = auto()
    CHANGE_CHANNEL = auto()
    UNSEAL_TRY = auto()
