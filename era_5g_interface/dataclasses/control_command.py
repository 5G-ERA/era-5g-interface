from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, Optional


class ControlCmdType(IntEnum):
    """Possible types of control commands for Network Application."""

    INIT = 1
    """Control Command used for initialization.

    Data required for initialization is provided using the data dict in the ControlCommand class.
    """

    RESET_STATE = 2
    """Reset current state of the Network Application."""

    GET_STATE = 3
    """Read and obtain current state of the Network Application."""

    SET_STATE = 4
    """Set newly defined state of the Network Application.

    The information about the new state can be provided using the data dict in the ControlCommand class.
    """

    SAVE_STATE = 5
    """Save current state on cloud storage."""

    LOAD_STATE = 6
    """Load saved state from cloud storage."""


@dataclass
class ControlCommand:
    """Dataclass containing information about control command for Network Application.

    Args:
        cmd_type (ControlCmdType): Type of the command to be sent.
        clear_queue (bool, optional): Clear previous unprocessed data (if any) in the internal queue. Default is False.
        data (Dict, optional): Data to be passed along with the command, e.g. new state data in case of command with
            type ControlCmdType.SET_STATE.
    """

    cmd_type: ControlCmdType
    clear_queue: bool = False
    data: Optional[Dict] = field(default_factory=dict)
