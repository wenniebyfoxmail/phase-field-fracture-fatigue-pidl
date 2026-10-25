"""Legacy import bridge for :mod:`fracture_observation`.

New observation-processing code should import from ``fracture_observation``.
The source-root import remains available for existing SENS runners.
"""

from fracture_observation.damage_observation_reconstruction import *  # noqa: F403
from fracture_observation.damage_observation_reconstruction import __all__
