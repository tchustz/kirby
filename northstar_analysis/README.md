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

## Refreshing the monitoring feed with new records

Open notebook 02 and follow **Before you refresh**. Its visible **EDIT HERE — refresh settings** cell controls `INPUT_FOLDER`, `AS_OF`, queue, window length, baseline, and review thresholds. Supply both complete, coordinated workbooks with their existing filenames and sheets; include enough history for your chosen baseline. New files replace the imported snapshot rather than append to it.

Clear all outputs, then restart the kernel and run all cells in **notebook 02 only**. Check every source date, warnings and sample counts, and the final **Refresh complete** message. Save the notebook to retain the results. This is a manual refresh, not a continuously connected dashboard. The load timestamp and `outputs/monitor_refresh_receipt.json` identify the run settings and input hashes; the receipt alone does not certify that the whole notebook finished.

For later exports, keep notebook 01 as the historical case analysis. `execute_notebooks.py` runs both notebooks and is intended to validate the original historical snapshot; use notebook 02 interactively for later monitoring data. Detailed instructions in notebook 02 identify where to adjust filenames, field names, and business rules if the export format changes. Archive prior inputs and outputs before replacement if you need a history of published reports.

## Learning Data Dashboard — proactive investigation pilot

Open **03_learning_early_warning.ipynb** for queue context, sample product/reason trends, QA/feedback signals, a filterable offline HTML dashboard, weekly insight digest, and persistent prioritized investigation register. Its refresh checklist explains exactly where to change inputs, dates, thresholds, source mappings and business rules. Results default to **historical_demo**: they demonstrate the method, not a successful early detection.

- Edit `learning_settings.json` for normal refreshes. Both the notebook and command-line runner use these settings. The visible notebook settings cell supports one-run overrides.
- Run just notebook 03 after changing its settings or replacing its coordinated exports. The existing notebooks remain available for historical analysis and recovery execution.
- For batch report generation, run `python learning_monitor.py --config learning_settings.json` from this folder; an optional `--as-of YYYY-MM-DD` overrides the report date. Nothing is scheduled or sent automatically. The notebook describes how an administrator could schedule the command after export delivery.
- Each successful run creates `outputs/learning/<UTC run timestamp>/` with `dashboard.html`, `weekly_digest.md`, `issue_register.csv`, weekly metrics, every rule evaluation, source coverage and hashes. `latest_run.json` points to the latest successful run. Changing browser filters does not reload data.
- Preserve `data/learning/issue_log.csv`: status, owner, notes and validated timing fields are retained on refresh. Historical and pilot issue IDs are separate. Disappearing flags do not close issues automatically. Back up the log and use a single writer.
- Use `python build_learning_notebook.py` to regenerate notebook 03 without changing notebooks 01/02; then execute it again to save fresh outputs. `python execute_notebooks.py --notebook 03_learning_early_warning.ipynb` runs only this notebook. Without `--notebook`, the runner now runs all three.
- Run checks with `python -m unittest discover -s . -p test_learning_monitor.py -v` from this folder.

Rules require sustained complete weeks, usable baseline history, fresh operations and sufficient observations. Full queue populations remain separate from sampled product/reason records and selected QA/feedback. The HTML contains aggregate figures, not customer/Guide identifiers. Repeat contacts are explicitly unavailable without authorized linked history; success timing remains unavailable until validated pilot dates exist. Guide views are off by default and never produce automated individual alerts or rankings. Counts alone cannot establish unbiased performance comparisons.
