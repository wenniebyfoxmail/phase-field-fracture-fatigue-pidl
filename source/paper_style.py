"""Legacy import and script bridge for :mod:`fracture_visuals.paper_style`."""

from fracture_visuals.paper_style import *  # noqa: F403
from fracture_visuals.paper_style import __all__


if __name__ == "__main__":
    import runpy

    runpy.run_module("fracture_visuals.paper_style", run_name="__main__")
