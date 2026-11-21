"""Timed IWA opacity-enforcement theory.

``t_bts`` preserves the original IWA_4.3 semantics; ``w_aic`` is the
endpoint-aware implementation used by the Enforcement_IWA Example 4. Older
variants are stored in ``backups/opacity_iwa_before_consolidation.zip``.
"""

from .t_aic_2 import WeightedAllInclusiveController, w_aic
from .t_aic_1 import TimedBipartiteSystem, t_bts

WeightedAIC = w_aic

__all__ = [
    "TimedBipartiteSystem",
    "WeightedAllInclusiveController",
    "WeightedAIC",
    "t_bts",
    "w_aic",
]
