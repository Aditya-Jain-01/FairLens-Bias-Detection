def compute_fairness_score(metrics: dict, shap: dict) -> dict:
    """
    Produces a single 0-100 FairLens Score from the metric results.

    Weights:
    - Disparate Impact:              30 points (legal compliance, highest weight)
    - Demographic Parity Difference: 25 points
    - Equalized Odds Difference:     25 points
    - Calibration Difference:        10 points
    - SHAP protected attr leakage:   10 points (protected attrs not driving model)
    """
    score = 0.0

    # Disparate Impact (30 pts): DI=1.0 is perfect, DI<0.8 fails legal threshold
    di = metrics.get("disparate_impact", {}).get("value", 1.0)
    di_score = min(1.0, di) * 30  # Caps at 30 if DI > 1.0 (over-correction)
    score += di_score

    # Demographic Parity Difference (25 pts): 0 is perfect, ±0.1 is threshold
    dpd = abs(metrics.get("demographic_parity_difference", {}).get("value", 0.0))
    dpd_score = max(0.0, (1 - dpd / 0.3)) * 25
    score += dpd_score

    # Equalized Odds Difference (25 pts)
    eod = abs(metrics.get("equalized_odds_difference", {}).get("value", 0.0))
    eod_score = max(0.0, (1 - eod / 0.3)) * 25
    score += eod_score

    # Calibration (10 pts)
    # Using false_positive_rate_difference or similar calibration if actual calibration not available
    cal = abs(metrics.get("average_odds_difference", {}).get("value", 0.0))
    if "calibration_difference" in metrics:
        cal = abs(metrics["calibration_difference"]["value"])
        
    cal_score = max(0.0, (1 - cal / 0.2)) * 10
    score += cal_score

    # SHAP leakage penalty (10 pts)
    # If protected attributes have high SHAP values, penalise
    shap_score = 10.0
    if shap and "protected_attr_shap" in shap:
        # Sum the importances of protected attributes
        protected_shap = sum(list(shap["protected_attr_shap"].values()))
        shap_score = max(0.0, (1 - protected_shap / 0.2)) * 10
    score += shap_score

    final = round(score, 1)
    return {
        "score": final,
        "grade": "A" if final >= 80 else "B" if final >= 60 else "C" if final >= 40 else "F",
        "breakdown": {
            "disparate_impact_contribution": round(di_score, 1),
            "demographic_parity_contribution": round(dpd_score, 1),
            "equalized_odds_contribution": round(eod_score, 1),
            "calibration_contribution": round(cal_score, 1),
            "shap_leakage_contribution": round(shap_score, 1),
        }
    }
