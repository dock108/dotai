"""Lightweight model builder for EDA.

Implements a simple logistic regression using gradient descent to avoid
heavy dependencies. Intended for exploratory analysis, not production-grade
modeling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence

import math


@dataclass
class TrainedModel:
    model_type: str
    features_used: List[str]
    feature_weights: Dict[str, float]
    accuracy: float
    roi: float


def _sigmoid(z: float) -> float:
    # Clamp to avoid overflow in exp for large magnitude z
    if z > 50:
        return 1.0
    if z < -50:
        return 0.0
    return 1 / (1 + math.exp(-z))


def train_logistic_regression(
    feature_data: Sequence[dict],
    features: List[str],
    target_key: str,
    lr: float = 0.1,
    epochs: int = 200,
) -> TrainedModel:
    """Train a minimal logistic regression.

    Args:
        feature_data: list of dicts containing feature values and target.
        features: feature names to use.
        target_key: key in feature_data for target value (0/1).
    """
    if not feature_data:
        return TrainedModel(
            model_type="logistic_regression",
            features_used=features,
            feature_weights={f: 0.0 for f in features},
            accuracy=0.0,
            roi=0.0,
        )

    weights = {f: 0.0 for f in features}
    bias = 0.0

    # gradient descent
    for _ in range(epochs):
        grad_w = {f: 0.0 for f in features}
        grad_b = 0.0
        n = 0
        for row in feature_data:
            if target_key not in row:
                continue
            y = float(row[target_key])
            x_vec = [float(row.get(f, 0.0) or 0.0) for f in features]
            z = sum(weights[f] * x for f, x in zip(features, x_vec)) + bias
            pred = _sigmoid(z)
            error = pred - y
            for f, x in zip(features, x_vec):
                grad_w[f] += error * x
            grad_b += error
            n += 1
        if n == 0:
            break
        for f in features:
            weights[f] -= lr * (grad_w[f] / n)
        bias -= lr * (grad_b / n)

    # Evaluate accuracy
    correct = 0
    total = 0
    profits = 0.0
    bets = 0
    for row in feature_data:
        if target_key not in row:
            continue
        y = float(row[target_key])
        x_vec = [float(row.get(f, 0.0) or 0.0) for f in features]
        z = sum(weights[f] * x for f, x in zip(features, x_vec)) + bias
        pred = _sigmoid(z)
        pred_label = 1.0 if pred >= 0.5 else 0.0
        if pred_label == y:
            correct += 1
        total += 1
        # Simple ROI proxy: bet when confidence > 0.55
        if pred >= 0.55:
            bets += 1
            profits += 1.0 if y == 1 else -1.0
    accuracy = correct / total if total else 0.0
    roi = (profits / bets) if bets else 0.0

    return TrainedModel(
        model_type="logistic_regression",
        features_used=features,
        feature_weights={f: weights[f] for f in features},
        accuracy=accuracy,
        roi=roi,
    )

