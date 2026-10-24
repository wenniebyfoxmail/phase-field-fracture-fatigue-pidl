"""Legacy import bridge for :mod:`pidl_core.damage_conditioned_equilibrium`.

New reusable code should import from ``pidl_core``.  This module remains so
existing SENS runners, which add ``source`` directly to ``sys.path``, retain
their historical import path while the mechanics implementation has one home.
"""

from pidl_core.damage_conditioned_equilibrium import *  # noqa: F403
from pidl_core.damage_conditioned_equilibrium import __all__
