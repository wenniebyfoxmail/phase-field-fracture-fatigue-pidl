"""Legacy import bridge for :mod:`fracture_state.damage_state_inversion`.

New state-estimation code should import from ``fracture_state``.  The legacy
source-root import stays available for current SENS runners.
"""

from fracture_state.damage_state_inversion import *  # noqa: F403
from fracture_state.damage_state_inversion import __all__
