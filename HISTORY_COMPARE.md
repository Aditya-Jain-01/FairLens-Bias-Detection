# FairLens: History & Compare Models Documentation

This document explains the functionality, technical implementation, and purpose of two critical features in the FairLens Bias Detection Platform: the **History** section and the **Compare Models** section.

---

## 1. History Section

**Location:** `/history`

The History section serves as the system of record (audit trail) for the platform. It tracks all successfully completed fairness audits, allowing compliance teams and data scientists to revisit past evaluations.

### How it Works
1. **Data Retrieval:** When a user navigates to the History tab, the frontend makes an authenticated API call to the backend `GET /history` endpoint.
2. **Database/Storage:** The backend retrieves a list of past job runs. It checks the Google Cloud Storage bucket (or local fallback storage) to confirm the existence of a valid `results.json` file for each job.
3. **Display:** The page renders a list of cards sorted chronologically. Each card contains:
   - **Dataset Name:** The name of the CSV file that was audited.
   - **Target & Protected Attributes:** The variables that were mapped during the audit configuration.
   - **Timestamp:** The exact date and time the audit completed.
   - **FairLens Score:** The aggregate fairness score (0-100) calculated by the engine.

### Purpose
- **Compliance Tracking:** Maintains a persistent record of model evaluations for regulatory or internal policy reviews.
- **Easy Retrieval:** Allows users to quickly jump back into the detailed interactive report (`/results/[job_id]`) without needing to re-upload or re-process data.

---

## 2. Compare Models Section

**Location:** `/compare`

The Compare Models section is a powerful analytical tool that allows users to quantify the impact of their bias mitigation efforts. It provides a side-by-side delta analysis of two different models or datasets.

### How it Works
1. **Selection:** The page fetches the list of completed audits from the History endpoint and populates two dropdown menus: 
   - **Baseline Model:** The original, unmitigated model.
   - **Candidate Model:** The new, potentially improved model.
2. **Data Fetching:** Upon clicking "Compare Results", the frontend fetches the full `results.json` payload for *both* selected audits simultaneously via `GET /results/[job_id]`.
3. **Delta Calculation:** The system maps the metrics (Disparate Impact, Equalized Odds, Demographic Parity, Calibration Difference, and the overall Score) side-by-side.
4. **Visual Indicators:** It calculates the mathematical delta between the two models. 
   - A **Green Arrow** indicates an improvement (e.g., the bias metric moved closer to the ideal threshold, or the aggregate score increased).
   - A **Red Arrow** indicates degradation (e.g., the new model is more biased in a specific metric than the baseline).

### Purpose
- **Measuring Remediation Success:** If a user runs an audit, notices severe bias, applies a mitigation technique (like reweighing or threshold adjustment), and re-audits the model, the Compare tool explicitly proves whether the mitigation was successful.
- **Model Selection:** Helps teams decide between two different candidate models by clearly highlighting the fairness trade-offs between them.
