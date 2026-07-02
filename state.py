from enum import Enum


class State(str, Enum):
    IDLE = "IDLE"
    MENU = "MENU"
    WAITING_QUESTION = "WAITING_QUESTION"
    SHOW_BOIS_INFO = "SHOW_BOIS_INFO"
    SHOW_MAOS_INFO = "SHOW_MAOS_INFO"


_states: dict[int, State] = {}


def get_state(user_id) -> State:
    return _states.get(int(user_id), State.IDLE)


def set_state(user_id, state):
    _states[int(user_id)] = State(state)
