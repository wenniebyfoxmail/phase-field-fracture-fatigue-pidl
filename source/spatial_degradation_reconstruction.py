"""Legacy import bridge for ``fracture_state.spatial_degradation_reconstruction``.

The optional neural reconstruction module now has an explicit dependency on
``pidl_core``.  This legacy source-root path remains for current runners.
"""

from fracture_state.spatial_degradation_reconstruction import *  # noqa: F403
from fracture_state.spatial_degradation_reconstruction import __all__
