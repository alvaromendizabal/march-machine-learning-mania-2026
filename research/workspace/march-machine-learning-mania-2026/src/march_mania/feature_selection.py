"""Deterministic training-only screening for broad antisymmetric candidate spaces."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.utils.validation import check_is_fitted


class TrainingScreen(TransformerMixin, BaseEstimator):
    """Retain at most 128 hypotheses after support, association and redundancy checks.

    Fit only inside a temporal training fold, including inside nested model search.
    Input arrays are the mirrored training games, never validation observations.
    The score is absolute point-biserial association, not a claim of significance.
    A fixed capacity limits high-dimensional fits on the small NCAA sample; broad
    generation and family ablations remain available regardless of retention.
    """

    def __init__(self, max_features: int = 128, correlation: float = 0.995) -> None:
        self.max_features = max_features
        self.correlation = correlation

    def fit(self, x: Any, y: Any) -> TrainingScreen:
        values = np.asarray(x, dtype=float)
        labels = np.asarray(y, dtype=float)
        if values.ndim != 2 or not len(values) or not values.shape[1]:
            raise ValueError("Nonempty two-dimensional training matrix required")
        if (
            len(labels) != len(values)
            or not np.isin(labels, [0, 1]).all()
            or np.unique(labels).size != 2
        ):
            raise ValueError("Aligned binary training labels with both classes required")
        if np.isinf(values).any() or self.max_features < 1 or not 0 < self.correlation <= 1:
            raise ValueError("Invalid screening inputs or settings")
        self.n_features_in_ = values.shape[1]
        support = np.isfinite(values).sum(axis=0)
        safe = np.where(np.isfinite(values), values, 0.0)
        centered = safe - safe.mean(axis=0)
        norm = np.linalg.norm(centered, axis=0)
        nonzero = np.count_nonzero(np.abs(safe) > 1e-12, axis=0)
        # Mirrored differences are centered at zero. Reject signals active in fewer
        # than 0.5% of training orientations; do not inspect validation support.
        rare = (nonzero > 0) & (nonzero < max(2, int(np.ceil(0.005 * len(values)))))
        usable = (support > 0) & (norm > 1e-12) & ~rare
        z = centered / np.where(norm > 0, norm, 1)
        centered_y = labels - labels.mean()
        score = np.abs(z.T @ centered_y) / np.linalg.norm(centered_y)
        reasons = np.where(
            support == 0,
            "all_missing",
            np.where(rare, "near_constant", np.where(usable, "capacity", "constant")),
        ).astype(object)
        # Stable tie-break by original catalog order, not accidental dataframe/hash order.
        order = np.lexsort((np.arange(len(score)), -score))
        retained: list[int] = []
        redundant_with = np.full(values.shape[1], -1, dtype=int)
        pending = usable.copy()
        for index in order:
            if not pending[index]:
                continue
            if len(retained) >= self.max_features:
                break
            retained.append(int(index))
            reasons[index] = "retained"
            pending[index] = False
            correlations = np.abs(z.T @ z[:, index])
            redundant = pending & (correlations >= self.correlation)
            reasons[redundant] = "redundant"
            redundant_with[redundant] = index
            pending[redundant] = False
        if not retained:
            raise ValueError("No informative training candidates")
        self.indices_ = np.asarray(sorted(retained), dtype=int)
        self.audit_ = pd.DataFrame(
            {
                "index": np.arange(values.shape[1]),
                "status": reasons,
                "training_support": support,
                "nonzero_support": nonzero,
                "association": score,
                "redundant_with_index": redundant_with,
            }
        )
        return self

    def transform(self, x: Any) -> np.ndarray:
        check_is_fitted(self, "indices_")
        values = np.asarray(x, dtype=float)
        if values.ndim != 2 or values.shape[1] != self.n_features_in_ or np.isinf(values).any():
            raise ValueError("Screening schema changed or contains infinity")
        return values[:, self.indices_]

    def get_support(self) -> np.ndarray:
        check_is_fitted(self, "indices_")
        result = np.zeros(self.n_features_in_, dtype=bool)
        result[self.indices_] = True
        return result


class ScreenedPredictor:
    """Persist selection together with its fitted sklearn or native LightGBM model."""

    def __init__(self, screen: TrainingScreen, model: Any) -> None:
        self.screen = screen
        self.model = model

    def predict_proba(self, values: np.ndarray) -> np.ndarray:
        selected = self.screen.transform(values)
        if hasattr(self.model, "predict_proba"):
            return np.asarray(self.model.predict_proba(selected), dtype=float)
        p = np.asarray(self.model.predict(selected), dtype=float)
        return np.column_stack([1 - p, p])


def screening_audit(model: Any, columns: list[str]) -> pd.DataFrame:
    if not isinstance(model, ScreenedPredictor):
        raise ValueError("A persisted training screen is required")
    result = model.screen.audit_.copy()
    if len(result) != len(columns):
        raise ValueError("Screening catalog mismatch")
    result["feature"] = columns
    result["redundant_with"] = result.redundant_with_index.map(
        {i: name for i, name in enumerate(columns)}
    )
    return result
