"""
Abstract base class for all profilers.

Every concrete profiler must perform a **full-scan** over the input array
using vectorised (NumPy/SciPy) operations — no sampling, no Python loops.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    from pydantic import BaseModel


class BaseProfiler(ABC):
    """Strategy interface for column-level profilers.

    Subclasses implement :meth:`fit` to produce a specific
    :class:`pydantic.BaseModel` profile contract.
    """

    @abstractmethod
    def fit(self, data: np.ndarray) -> BaseModel:
        """Perform a full-scan analysis on *data* and return a profile.

        :param data: 1-D NumPy array to profile.
        :return: A frozen Pydantic model containing the analysis results.
        :raises DataQualityError: If the data is irrecoverably dirty.

        .. note::

            **Architecture mandate** — implementations MUST:

            * Scan 100% of the data (no down-sampling).
            * Use vectorised NumPy / SciPy operations (no ``for`` loops).
        """
        ...  # pragma: no cover
