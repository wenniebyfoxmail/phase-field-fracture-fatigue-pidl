"""Legacy import bridge for :mod:`fracture_assimilation`.

New state-assimilation code should import from ``fracture_assimilation``.  The
source-root import remains available for existing runner code.
"""

from fracture_assimilation.fem_mechanism_assimilation import *  # noqa: F403
from fracture_assimilation.fem_mechanism_assimilation import __all__
