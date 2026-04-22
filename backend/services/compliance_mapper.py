"""
services/compliance_mapper.py
Maps failing fairness metrics to relevant regulations and frameworks.
"""

REGULATORY_MAP = {
    "disparate_impact": {
        "failed": [
            {"framework": "US EEOC 80% Rule", "article": "Uniform Guidelines", "severity": "violation"},
            {"framework": "EU AI Act", "article": "Article 10 (Data Governance)", "severity": "violation"},
            {"framework": "Equal Credit Opportunity Act (ECOA)", "article": "General", "severity": "relevant"},
        ]
    },
    "demographic_parity_difference": {
        "failed": [
            {"framework": "EU AI Act", "article": "Article 10", "severity": "violation"},
        ]
    },
    "equalized_odds_difference": {
        "failed": [
            {"framework": "EU AI Act", "article": "Article 15 (Accuracy)", "severity": "violation"},
            {"framework": "Fair Housing Act (FHA)", "article": "General", "severity": "relevant"},
        ]
    },
}

def map_to_regulations(metrics: dict) -> list[dict]:
    """
    Given a dict of metrics (with boolean 'passed'), returns a list of 
    potential regulatory violations.
    """
    violations = []
    if not metrics:
        return violations
        
    for metric_name, metric_data in metrics.items():
        if not metric_data.get("passed", True) and metric_name in REGULATORY_MAP:
            for reg in REGULATORY_MAP[metric_name]["failed"]:
                violations.append({
                    "metric": metric_name.replace("_", " ").title(),
                    "metric_value": metric_data.get("value"),
                    **reg
                })
    return violations
