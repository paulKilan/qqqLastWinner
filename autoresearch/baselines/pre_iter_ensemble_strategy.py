'''
Ensemble Trading Strategy

Blends multiple sub-strategies with configurable weights.
Uses a threshold-based voting system to decide positions:
  - If weighted long signal > threshold → go long (TQQQ)
  - If weighted short signal > threshold → go short (SQQQ)
  - Otherwise → stay in cash

This avoids holding partial TQQQ + partial SQQQ simultaneously
(which would be wasteful with leveraged ETFs).
'''

import pandas as pd
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from .base_strategy import BaseStrategy


class EnsembleStrategy(BaseStrategy):
    """
    Ensemble strategy that blends multiple sub-strategies with weights.

    Args:
        strategies: List of (strategy_instance, weight) tuples.
                    Weights are normalized to sum to 1.0.
        long_threshold: Minimum blended long score to go long (default 0.5).
        short_threshold: Minimum blended short score to go short (default 0.5).
    """

    def __init__(
        self,
        strategies: List[Tuple[Any, float]],
        long_threshold: float = 0.5,
        short_threshold: float = 0.5,
    ):
        super().__init__(allow_short=True)

        if not strategies:
            raise ValueError("Must provide at least one (strategy, weight) pair")

        total_weight = sum(w for _, w in strategies)
        if total_weight <= 0:
            raise ValueError("Total weight must be positive")

        self.strategies = [(s, w / total_weight) for s, w in strategies]
        self.long_threshold = long_threshold
        self.short_threshold = short_threshold

    def execute(
        self,
        startDate: str,
        endDate: str,
        contextData: Optional[Dict[str, Any]] = None,
    ) -> pd.DataFrame:
        """
        Run all sub-strategies, blend their signals, and apply thresholds.
        Overrides BaseStrategy.execute() entirely — data loading is delegated to sub-strategies.

        Returns DataFrame with columns: longPositionPct, shortPositionPct, error
        """
        all_long = []
        all_short = []
        weights = []

        for strategy, weight in self.strategies:
            try:
                output = strategy.execute(
                    startDate=startDate,
                    endDate=endDate,
                    contextData=contextData or {},
                )

                # Ensure index is datetime
                if "date" in output.columns:
                    output = output.set_index("date")
                output.index = pd.to_datetime(output.index)
                output.sort_index(inplace=True)

                long_pct = pd.to_numeric(output["longPositionPct"], errors="coerce").fillna(0.0)
                short_pct = pd.to_numeric(output["shortPositionPct"], errors="coerce").fillna(0.0)

                all_long.append(long_pct)
                all_short.append(short_pct)
                weights.append(weight)

            except Exception as e:
                name = type(strategy).__name__
                print(f"Warning: {name} failed — {e}")
                continue

        if not all_long:
            raise RuntimeError("All sub-strategies failed")

        # Re-normalize weights in case some strategies failed
        w_total = sum(weights)
        weights = [w / w_total for w in weights]

        # Align all signals to a common date index (union of all dates)
        common_index = all_long[0].index
        for s in all_long[1:]:
            common_index = common_index.union(s.index)
        common_index = common_index.sort_values()

        # Compute weighted blend
        blended_long = pd.Series(0.0, index=common_index)
        blended_short = pd.Series(0.0, index=common_index)

        for long_s, short_s, w in zip(all_long, all_short, weights):
            blended_long += long_s.reindex(common_index).ffill().fillna(0.0) * w
            blended_short += short_s.reindex(common_index).ffill().fillna(0.0) * w

        # Apply thresholds to decide discrete positions
        long_mask = (blended_long >= self.long_threshold) & (blended_long >= blended_short)
        short_mask = (blended_short >= self.short_threshold) & (blended_short > blended_long)

        result_df = pd.DataFrame(
            {'longPositionPct': 0.0, 'shortPositionPct': 0.0, 'error': None},
            index=common_index,
        )
        result_df.index.name = "date"
        result_df.loc[long_mask, "longPositionPct"] = 1.0
        result_df.loc[short_mask, "shortPositionPct"] = 1.0

        return result_df

    def _calculate_positions(self, data, contextData=None):
        # EnsembleStrategy overrides execute() directly and never uses this path.
        raise NotImplementedError(
            "EnsembleStrategy overrides execute() directly. "
            "_calculate_positions is not used."
        )
