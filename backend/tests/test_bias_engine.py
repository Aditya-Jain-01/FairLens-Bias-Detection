import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add the ml directory to the python path so bias_engine can be imported
sys.path.insert(0, str(Path(__file__).parent.parent / "ml"))

from bias_engine import compute_bias_metrics

def test_disparate_impact_extreme_bias():
    """
    Test disparate impact calculation with an extreme synthetic dataset.
    Group 1 gets 100% positive predictions. Group 0 gets 0% positive predictions.
    DI should be exactly 0 (or close to 0 due to epsilon smoothing).
    """
    df = pd.DataFrame({
        "target": [1, 1, 1, 0, 0, 0],
        "pred":   [1, 1, 1, 0, 0, 0],    # perfect predictor
        "group":  ["A", "A", "A", "B", "B", "B"] # Group A gets all 1s, B gets all 0s
    })
    
    # Run the bias engine treating 'target' as truth, 'pred' as prediction, 'group' as protected attr
    # Let's say positive label is 1
    results = compute_bias_metrics(df, "target", ["group"], "pred", positive_label=1)
    
    di = results["metrics"]["disparate_impact"]["value"]
    
    # Since group B has 0/3=0% and group A has 3/3=100%, DI = 0/1 = 0
    # The bias engine adds a small epsilon, so it might be 0.00something
    assert di < 0.05, f"Expected DI near 0, got {di}"
    assert not results["metrics"]["disparate_impact"]["passed"], "DI should fail heavily"

def test_perfect_fairness():
    """
    Test fairness when both groups get exactly the same rates.
    """
    df = pd.DataFrame({
        "target": [1, 0, 1, 0],
        "pred":   [1, 0, 1, 0],
        "group":  ["Privileged", "Privileged", "Unprivileged", "Unprivileged"]
    })
    
    results = compute_bias_metrics(df, "target", ["group"], "pred", positive_label=1)
    
    # DI should be 1.0 (perfect parity)
    di = results["metrics"]["disparate_impact"]["value"]
    assert abs(di - 1.0) < 0.01, f"Expected DI around 1.0, got {di}"
    
    # Equalized odds diff should be 0.0 (TPR and FPR are identical across groups)
    eod = results["metrics"]["equalized_odds_difference"]["value"]
    assert eod < 0.01, f"Expected EOD near 0.0, got {eod}"
    
    # Demographic parity diff should be 0.0
    dpd = results["metrics"]["demographic_parity_difference"]["value"]
    assert dpd < 0.01, f"Expected DPD near 0.0, got {dpd}"
    
    assert results["metrics"]["disparate_impact"]["passed"], "Perfect fairness should pass DI check"

def test_equalized_odds_violation():
    """
    Test equalized odds computation when the model predicts falsely for one group.
    """
    df = pd.DataFrame({
        "target": [0, 0, 0, 0, 0, 0],
        "pred":   [1, 1, 1, 0, 0, 0], # Model highly discriminates false positives against group A
        "group":  ["A", "A", "A", "B", "B", "B"]
    })
    
    results = compute_bias_metrics(df, "target", ["group"], "pred", positive_label=1)
    
    # False Positive Rate:
    # Group A: Truth is 0, Pred is 1 (FPR = 3/3 = 1.0)
    # Group B: Truth is 0, Pred is 0 (FPR = 0/3 = 0.0)
    # FPR diff = 1.0 - 0.0 = 1.0
    
    eod = results["metrics"]["equalized_odds_difference"]["value"]
    assert eod > 0.8, f"Expected EOD to be high (violating FPR parity), got {eod}"
    assert not results["metrics"]["equalized_odds_difference"]["passed"], "Should fail the EOD threshold"
