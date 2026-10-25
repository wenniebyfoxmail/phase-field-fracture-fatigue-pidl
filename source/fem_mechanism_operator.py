"""Legacy import bridge for :mod:`pidl_core.fem_mechanism_operator`.

New reusable neural-mechanics code should import from ``pidl_core``.  The
historical source-root path remains available for existing SENS runners.
"""

from pidl_core.fem_mechanism_operator import *  # noqa: F403
from pidl_core.fem_mechanism_operator import __all__
