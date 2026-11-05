# Northstar Care analysis and monitoring

Start with **01_analysis_and_solution.ipynb**, then **02_monitoring.ipynb**. Both include saved execution outputs, charts, denominators, limitations, and proposed actions. This is a synthetic case as of October 2, 2026, not a live operational dashboard. Attached assignment instructions were treated as context; the deliverables answer the user's notebook request.

## Reading without coding experience

The analysis opens with summary cards, then August-versus-September charts, a recovery-completion chart, and plain-language explanations of what each finding means. Technical cleaning checks are in the appendix. Tables use readable labels and percentages; sample counts are shown alongside findings. Code starts collapsed in viewers that support notebook folding. In other viewers, skip the code blocks and read the saved results underneath.

The monitoring notebook explains its terms, periods, and review warnings before asking readers to act. Its controls remain visible for the colleague refreshing the data.

## Contents

- `01_analysis_and_solution.ipynb`: cleaning audit, population demand/staffing trends, sampled recovery and selected QA/feedback analysis, recommendation, learner-facing cue and practice, ownership and proposed pilot.
- `02_monitoring.ipynb`: parameterized queue/date dashboard, freshness and sample-size checks, proposed review triggers, weekly trends, sampled recovery-review candidates, operating review instructions.
- `analysis_utils.py`: shared validated Excel ingestion, deduplication, joins, definitions and exports.
- `presentation.py`: readable summary cards, formatted comparison tables, and chart formatting helpers.
- `data/raw/`: untouched copies of all nine supplied files for portable reruns.
- `outputs/`: cleaned tables, source hashes, analysis summaries, monitoring metrics and sampled review candidates. Generated files are replaceable; raw files are preserved.
- `build_notebooks.py`: notebook source generator. Running it resets saved notebook outputs; run `execute_notebooks.py` afterwards.
- `execute_notebooks.py`: executes both notebooks in fresh kernels and fails on errors.

## Run

Python 3.12 was used. From this directory:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python execute_notebooks.py
```

For interactive work, open either notebook in a Jupyter-compatible editor, select the virtual environment, and Run All from this directory or its parent. A browser Jupyter interface is optional (`python -m pip install jupyterlab`; then `jupyter lab`). No secrets, remote APIs, or services are needed. The current cloud instance also has `/workspace/notebook-venv/bin/python` with these dependencies. Local Jupyter kernel execution may need permission for loopback sockets.

To monitor a new extract, replace the two workbooks in `data/raw/` with the same schemas (preserve prior snapshots elsewhere), change `AS_OF`, queue and date/window controls in notebook 02, and Run All. Monitoring accepts later exports up to the explicit as-of date; notebook 01 intentionally retains historical cutoffs. Inspect schema checks, source hashes, freshness, missingness, and join audits at every refresh. Do not reuse historical narrative numbers for refreshed data without revising the interpretation.

## Important definitions

Population AHT is answered-contact weighted; abandonment is abandoned/offered. Offered-weighted wait and scheduled-hours-weighted occupancy are labeled proxies. Product tags are not serial eligibility. Eligible recovery is complete only when replacement and Plus are both recorded Yes. Analysis considers queue-specific availability: Specialist September 12, General September 21. Missing product/reason values remain missing. Duplicate calls are checked for consistency before deduplication; selected QA and voluntary feedback join many-to-one to calls.

Unexpectedly, 18 observed non-WN7 product codes are absent from the supplied catalog; they are retained and flagged. Rounded durations differ from summed components by at most 0.1 minute. QA/feedback selection and queue differences preclude causal claims. Repeat contacts, population eligible demand, transaction backlog and actual pilot exposure cannot be measured from these files.

Pilot sizes, schedules, thresholds, learner wording and ownership requests are proposals for review, not implemented business changes. Nothing is sent to Dana or other people.
