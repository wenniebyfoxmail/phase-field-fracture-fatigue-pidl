"""Frozen-field residual selection for phase-field road-crack diagnostics."""

from .library import DEFAULT_TERM_NAMES, DYNAMIC_TERM_NAMES, build_candidate_library
from .schema import SnapshotSchemaReport, validate_frozen_snapshots
from .selectors import (
    SelectionResult,
    ValidationSelectionResult,
    fit_stlsq,
    stability_validated_select,
    validation_select_support,
)
from .weak_system import WeakSystem, assemble_dynamic_weak_system, assemble_weak_system

__all__ = [
    "DEFAULT_TERM_NAMES",
    "DYNAMIC_TERM_NAMES",
    "SelectionResult",
    "ValidationSelectionResult",
    "SnapshotSchemaReport",
    "WeakSystem",
    "assemble_weak_system",
    "assemble_dynamic_weak_system",
    "build_candidate_library",
    "fit_stlsq",
    "stability_validated_select",
    "validation_select_support",
    "validate_frozen_snapshots",
]
