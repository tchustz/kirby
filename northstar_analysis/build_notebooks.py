from pathlib import Path
import nbformat as n
R=Path(__file__).resolve().parent

def notebook(name,cells):
 b=n.v4.new_notebook(cells=[n.v4.new_markdown_cell(t) if k=='m' else n.v4.new_code_cell(t) for k,t in cells],metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3.12'}})
 n.write(b,R/name)

setup="""from pathlib import Path
import sys
ROOT = Path.cwd() if (Path.cwd() / 'analysis_utils.py').exists() else Path.cwd() / 'northstar_analysis'
assert (ROOT / 'analysis_utils.py').exists(), 'Run from northstar_analysis or its parent.'
sys.path.insert(0, str(ROOT))
from analysis_utils import *
import matplotlib.pyplot as plt
from IPython.display import display, Markdown
plt.rcParams.update({'figure.figsize': (11, 4), 'axes.spines.top': False, 'axes.spines.right': False})
pd.set_option('display.max_columns', 30)
pd.set_option('display.max_rows', 40)
D = load_data()
calls, ops = D['calls'], D['ops']
"""
notebook('01_analysis_and_solution.ipynb',[
('m',"""# Northstar Care: complete the recovery, then reduce avoidable time
**Decision notebook · fictional case as of October 2, 2026 · operations through September 30.**

**Recommendation:** give General Care a WN7-specific recognition and recovery cue, short worked example, and branch practice; fix article discovery and system follow-up alongside coaching. Test in staggered cohorts before wider deployment. A generic empathy video alone cannot supply the missing operational path.

This notebook fulfills the user's request for cleaning, analysis, and a proposed solution. Attached requests for a Dana email, video, or interviewer note are case context, not additional user instructions. No messages are sent. All facts come from the packet; proposed actions and targets are labeled. Run all cells in order. See `02_monitoring.ipynb` for refreshable monitoring, `analysis_utils.py` for shared cleaning, and `README.md` for execution instructions.
"""),('c',setup),
('m',"""## 1. Data contract and cleaning
Daily operations and staffing are **full populations**; sampled calls are not demand. QA oversamples long/recovery-risk calls; feedback is voluntary and oversamples WN7 outreach. Neither produces population behavior or satisfaction rates.

The loader detects Excel headers below four title/note rows, trims strings, parses dates, converts metrics, validates keys and joins, and removes only consistent duplicate Call IDs. Missing product/reason values remain missing; no inferred eligibility or imputation. WN7 + WNM-7 product buckets identify WN7-containing contacts, not affected households or eligible serials. Source eligibility is retrospective: pre-release non-recovery is not a Guide failure.

AHT and its components are independently rounded to one decimal; a 0.15-minute tolerance accommodates the observed ±0.1-minute differences without rewriting source durations. Daily wait lacks a denominator definition: offered-weighted wait is explicitly a proxy. Occupancy is scheduled-hours weighted, also a proxy. AHT is answered-contact weighted; abandonment is total abandoned / total offered.
"""),
('c',"""display(D['audit'])
missing = calls[['Product code','Reason code']].isna().sum().to_frame('missing_n')
missing['share'] = missing['missing_n'] / len(calls)
display(missing)
display(D['catalog_unmatched'])
print('Unmatched catalog rows:', D['catalog_unmatched']['sample_calls'].sum())
print('Duplicate export rows removed:', len(D['duplicate_rows']))
print('Operations range:', ops.Date.min().date(), 'to', ops.Date.max().date())
print('QA joined:',len(D['qa_joined']),'; feedback joined:',len(D['feedback_joined']))
export_clean(D)
"""),
('m',"""**Additional data-quality finding:** the catalog omits several non-WN7 codes present in sampled calls. Retain them as other products; do not discard their calls or fabricate catalog descriptions. WN7 and WNM-7 are explicitly documented. The table above lists all unmatched codes. Sample missingness and catalog gaps limit granular product comparisons. Cleaned CSVs, duplicate removals, and source SHA-256 hashes are exported to `outputs/` for audit.
"""),
('c',"""ops['Month'] = ops.Date.dt.to_period('M').astype(str)
monthly = ops.groupby(['Queue','Month']).apply(population_metrics, include_groups=False)
display(monthly.round(3))
monthly.to_csv(OUT/'monthly_population_metrics.csv')
gc = monthly.loc['General Care']
a, b = gc.loc['2026-08'], gc.loc['2026-09']
display(pd.DataFrame({'August':a,'September':b,'change':b-a}).round(3))
"""),
('m',"""## 2. Queue pressure is a volume and handling problem
General Care offered contacts per day rose **22.6%**, from 22,100 in August to 27,098 in September. Answered-weighted AHT rose **8.58 → 11.14 minutes** (+29.8%). Abandonment rose **4.16% → 28.46%** (+24.30 percentage points). WN7-containing share of answered contacts rose **1.32% → 30.28%**, while actual/planned Guide coverage slipped **94.1% → 92.0%**.

These concurrent changes support addressing WN7 recovery and staffing, but do not identify how much population AHT is causally attributable to the defect. Tags are imperfect; there are no population durations by product or customer identifiers. More callers abandoning also changes the answered population. Do not multiply sampled call differences by full volume to claim savings.
"""),
('c',"""g = ops[ops.Queue.eq('General Care')].sort_values('Date')
fig, ax = plt.subplots(2, 2, figsize=(13,8), sharex=True)
for axis, field, title in zip(ax.flat,
 ['Offered contacts','Average handle minutes','Abandonment rate','Actual Guides'],
 ['Daily offered contacts (population)','Daily AHT (minutes)','Daily abandonment (share of offered)','Daily actual Guides']):
 axis.plot(g.Date,g[field],color='#246b8e');axis.set_title(title)
 for date in ['2026-08-31','2026-09-12','2026-09-21']:
  axis.axvline(pd.Timestamp(date),color='grey',ls=':',alpha=.6)
fig.suptitle('General Care • dotted lines: confirmation, Specialist pilot, General article')
fig.autofmt_xdate();fig.tight_layout();plt.show()
"""),
('c',"""# Descriptive product segments, including missing codes; no sample expansion weights.
calls['Month'] = calls['Call date'].dt.to_period('M').astype(str)
segments = calls.groupby(['Queue','Month','Product segment'])['AHT minutes'].agg(n='size',mean='mean',median='median')
display(segments.loc[('General Care', ['2026-08','2026-09']), :].round(2))
components = ops.groupby(['Queue','Month']).apply(
 lambda x: pd.Series({k:np.average(x[k],weights=x['Answered contacts']) for k in
 ['Average talk minutes','Average hold minutes','Average wrap minutes']}),include_groups=False)
display(components.loc[('General Care', ['2026-08','2026-09']),:].round(2))
"""),
('m',"""## 3. Availability is not adoption or successful recovery
Chronology matters: August 31 issue confirmed; September 10 offer approved; September 12 Specialist pilot starts; September 21 General Care article becomes available. The September 28 thread confirms a weekly roundup, **no separate incident alert or scheduled shift briefing**, and no readership evidence. General article publication therefore does not prove exposure or competence.

`Case_info.md`, BH-4419 / PO-117: verify serial, follow the eligible/not-eligible/unavailable branch, and complete **both** replacement and Plus. Product model alone is insufficient. `meetings.md`, September 21 and 24: generic search can return the old restart flow; pending credit and incomplete recaps persist. These qualitative observations explain plausible mechanisms, not prevalence.
"""),
('c',"""phase = calls.groupby(['Queue','Phase']).apply(recovery_metrics,include_groups=False)
display(phase.round(3))
available = calls[calls['Recovery available']].copy()
recovery = available.groupby('Queue').apply(recovery_metrics,include_groups=False)
display(recovery.round(3))
recovery.to_csv(OUT/'available_period_recovery.csv')
e = available[available['Eligible for recovery'].eq('Yes')]
path = e.groupby(['Queue','Conversation path'])['AHT minutes'].agg(n='size',mean='mean',median='median')
display(path.round(2))
fig,ax=plt.subplots(figsize=(10,4))
path['mean'].unstack(0).plot.barh(ax=ax)
ax.set_xlabel('Sample mean AHT (minutes)');ax.set_title('Eligible calls after queue-specific path availability • association only')
plt.tight_layout();plt.show()
"""),
('m',"""In General Care after September 21, **76/204 eligible sampled calls (37.3%)** completed both transactions; **159/204** recorded a serial check, **89/204** arranged replacement. Thirteen replacement calls lacked Plus. The other 115 eligible calls followed generic troubleshooting. This is a sampled-call result, not an estimate of all eligible demand.

Within that same queue and period, complete recovery averaged **10.89 minutes (n=76)** versus **19.84 (n=115)** for generic troubleshooting. Specialist eligible calls after September 12 completed both in **163/193 (84.5%)**. These are promising exemplars, not a controlled comparison: routing, selection, account complexity, Guide experience, and dates differ. A shorter incomplete call is not success. No rollout initiated by Dana's request is documented.
"""),
('c',"""q = D['qa_joined']
f = D['feedback_joined']
display(D['qa']['Selection reason'].value_counts().rename('reviews').to_frame())
qpost=q[q['Recovery available'] & q['Eligible for recovery'].eq('Yes')]
qa_summary=qpost.groupby('Queue').agg(review_n=('QA review ID','size'),
 impact_yes=('Acknowledged practical impact',lambda x:x.eq('Yes').sum()),
 recognized_yes=('Recognized recovery path',lambda x:x.eq('Yes').sum()),
 recap_yes=('Recap complete',lambda x:x.eq('Yes').sum()))
display(qa_summary)
fpost=f[f['Recovery available'] & f['Eligible for recovery'].eq('Yes')]
fb_summary=fpost.groupby(['Queue','Conversation path']).agg(response_n=('Feedback ID','size'),
 mean_score=('Satisfaction score','mean'),satisfied_share=('Satisfied (4 or 5)',lambda x:x.eq('Yes').mean()))
display(fb_summary.round(3))
print('Repeated QA Call IDs:',q['Call ID'].duplicated().sum(),'; repeated feedback Call IDs:',f['Call ID'].duplicated().sum())
"""),
('m',"""Selected feedback is consistent with recovery quality: General Care complete-recovery respondents averaged **4.53/5 (n=47)** versus **1.46 (n=61)** following generic troubleshooting. This is not population CSAT or evidence of training impact. QA behavior checklist totals are not validated performance scores. Keep review dates and call dates separate; October 1 reviews/responses can refer to September calls.

## 4. Proposed solution: an actionable recovery cue plus a bounded test
**Immediate learning response:** a ≤5-minute worked example can introduce the pivot from acknowledgment to action, but must link to the current Beacon article. Pair it with branch practice and one observed-call coaching check. Do not teach every Guide every product, force a memorized speech, or reward shorter calls at the expense of recovery.

**One-screen cue — learner-facing draft, subject to Product/Quality review:**
1. **Hear the disruption.** “Losing the whole connection during work calls is disruptive. You said it drops briefly and returns by itself. I can check whether your hub is included in the group we can replace.” Confirm the reported pattern; then model and hub serial. WNM-7 contains a WN7 hub.
2. **Check Orbit, don't guess.** Use BH-4419 / PO-117 and the serial eligibility result. Model alone is not eligibility. If not eligible, continue appropriate troubleshooting/escalation. If serial unavailable or tool down, open eligibility review and give a specific follow-up expectation you can keep; do not invent timing.
3. **Eligible: do both actions.** “Your hub is eligible for a no-cost replacement. We'll also attach twelve months of Plus at no cost as a goodwill benefit. Plus is not a repair for this issue and doesn't prevent every outage.” Verify replacement confirmation and Plus **Applied**. Keep satellite nodes unless separately diagnosed. Do not require repeated restarts before the approved remedy.
4. **Close the loop accurately.** Recap confirmation, shipping estimate shown in Orbit (normally five–seven business days), Plus status, and next steps. Document confirmation/status/follow-up. “The replacement is confirmed; the Plus credit is still pending. Your recovery case remains open, and [specific owner/follow-up expectation confirmed in the tool].” Bracketed text must be filled with a real commitment, never read as a promise without verification. Use unresolved recovery follow-up when either transaction fails; do not report full completion.

**Practice prompts and answer check:**
- Eligible customer has already restarted three times: acknowledge work interruption, check serial once, explain both benefits, verify both transactions, recap; no new restart condition.
- WN7 serial is not eligible: no replacement/free-year promise; diagnose/escalate the actual issue.
- Order confirmed, credit pending: do not call recovery complete; keep case open, record both statuses and arrange specific follow-up.
- Serial absent or eligibility tool unavailable: eligibility review and clear follow-up, no guessed entitlement.

Team Lead checks the observable branch and transaction status, gives one specific correction, and has the Guide retry. Attendance and quiz completion track reach, not transfer to the call.

## 5. Ownership, capacity, and decision rules — proposals, not completed actions
| Owner | Next step | Evidence before expansion |
|---|---|---|
| Dana / Priya | Sponsor 24-General-Care-Guide pilot across shifts and tenure groups; match comparison shifts or randomize small cohorts if practical | Roster, exposure dates, comparable call mix, baseline reviews |
| Learning + Mateo | ≤5-minute model, one-screen cue, 7-minute branch practice | 12 minutes/Guide; 24 × 12 = **4.8 Guide-hours** total, excluding Lead/QA effort |
| Renee / WFM | Stagger six groups of four outside 11 a.m.–4 p.m. Central, subject to coverage approval | 48 Guide-minutes removed per cohort; model actual queue effect rather than infer from daily averages |
| Product Operations / Knowledge / Systems | Validate offer language; fix customer-language search and older-article cross-link; confirm screen access and unresolved follow-up | Successful retrieval and transaction walkthrough from General Care workstation; no assumed sandbox |
| Priya / Team Leads + Elias / Quality | One coached call per participating Guide within a week; focused reviews across both groups, including ineligible and failed-transaction cases | Recognition, serial result followed, two transactions or honest unresolved handoff, clear recap; no new punitive score |
| Jules + Product/Legal | Own proactive notice timing and audience | Notice remains in review as of October 1; annotate actual release if it occurs |

**Test plan:** proposed two-week staggered test; collect a one-week pre-period where the General article is already available and compare contemporaneous eligible calls within General Care. If randomization is impractical, report descriptive changes with strata for shift, tenure, mix, and staffing. Log simultaneous article/search/routing changes; do not isolate a training effect from a bundled test.

**Proposed gates requiring owner agreement:** 100% safe branch selection in practice before unsupervised use; no unsupported offer in reviewed ineligible calls; eligible sample completion improves ≥15 percentage points over comparable baseline with denominator ≥30 per group; no >2-point abandonment or >0.5-minute wait deterioration in matched operating windows. These are operational starting proposals, not statistically validated thresholds. Small/biased samples yield an inconclusive result, not success. Review transaction failures separately from Guide behavior.

If completion improves but queues worsen, revise capacity/cohort scheduling before expansion. If serial checking improves but Plus failures persist, prioritize Systems follow-up rather than repeat empathy training. Specialist capacity is limited (about 70 extra contacts/day temporarily per September 19 notes); blanket transfers and an automated offer lack approval and are not recommended as an immediate substitute.

**Limits and next data needed:** no household/account IDs to measure repeat contacts, no order/credit event ledger to verify final fulfillment or backlog age, no exposure/roster/tenure file, no reliable wait numerator or interval-level staffing. Request those internally before claiming repeat-contact reduction, causal impact, closed recovery backlog, or sustainable capacity. Sample incomplete calls exported by monitoring are review candidates, not a deduplicated household backlog.

## Source traceability
- `DATA_DICTIONARY.md`: populations, duplicates, bias, retrospective eligibility, chronology.
- `Orbit_operations.xlsx`: Daily operations and Staffing for population metrics; Call sample for paths and duration; Product catalog for code checks.
- `Quality_and_feedback.xlsx`: selected reviews and voluntary responses; joined on Call ID with cardinality checks.
- `Case_info.md`: BH-2240 vs BH-4419, PO-117 approved recovery, CLEAR, product limits.
- `threads.md`, “Guide reference follow-up,” September 28: distribution versus readership.
- `meetings.md`: August 31 confirmation; September 10 approval; September 16 calibration; September 18 Guide feedback; September 19 workforce; September 21 release; September 24 open items; October 1 leadership discussion.
- Dana's September 29 email frames urgency and original short-video request. `00_START_HERE.md` establishes fictional scope and case date. `INTERVIEW_PREP_PROMPT.md` adds no empirical case facts.
""")])

notebook('02_monitoring.ipynb',[
('m',"""# Recovery and queue monitoring
**Refreshable notebook dashboard · synthetic case · no live system connection.**

Change the parameter cell, replace the two source workbooks with refreshed exports retaining the same schemas, and Run All. The notebook re-cleans raw data, validates joins, displays date/queue filters and sample denominators, and exports monitoring tables and sampled recovery-review candidates. Charts render directly in Jupyter; no server is required.

This is a historical dashboard through September 30, 2026, not evidence that a proposed intervention has happened. Default as-of is the **case date**, October 2. For a real refresh change it deliberately; historical data must not look current. Operational alert thresholds below are proposed review triggers; they are not contractual targets or causal tests.
"""),
('c',"""# User controls. Queue must match the workbook labels.
QUEUE = 'General Care'
AS_OF = '2026-10-02'
WINDOW_DAYS = 7
BASELINE_START = '2026-08-01'
BASELINE_END = '2026-08-31'
MIN_ELIGIBLE_SAMPLE = 30
MAX_STALENESS_DAYS = 3
ABANDONMENT_DELTA_PP = 2.0
WAIT_DELTA_MIN = 0.5
COMPLETION_REVIEW_FLOOR = 0.80  # proposed target, not historical expectation
"""),
('c',setup.replace('D = load_data()', 'D = load_data(as_of=AS_OF, call_through=AS_OF)')+"""
AS_OF = pd.Timestamp(AS_OF)
assert QUEUE in set(ops.Queue), 'Unknown queue'
assert WINDOW_DAYS > 0
latest = ops.loc[ops.Queue.eq(QUEUE), 'Date'].max()
if latest > AS_OF: raise ValueError('Source operations include dates after AS_OF; choose a valid snapshot')
end = min(latest, AS_OF)
start = end - pd.Timedelta(days=WINDOW_DAYS-1)
base = ops[ops.Queue.eq(QUEUE) & ops.Date.between(BASELINE_START, BASELINE_END)]
current = ops[ops.Queue.eq(QUEUE) & ops.Date.between(start,end)]
if base.empty or current.empty: raise ValueError('Empty baseline or current window')
stale_days = (AS_OF-latest).days
print(f'Queue: {QUEUE} | source latest: {latest.date()} | case as-of: {AS_OF.date()}')
print(f'Current: {start.date()}–{end.date()} | baseline: {BASELINE_START}–{BASELINE_END}')
print(f'Data age: {stale_days} days | '+('STALE — refresh required' if stale_days>MAX_STALENESS_DAYS else 'within configured freshness tolerance'))
print('No intervention exposure file supplied; intervention status: NOT OBSERVED.')
display(D['audit'])
"""),
('c',"""baseline = population_metrics(base)
now = population_metrics(current)
scorecard = pd.DataFrame({'baseline':baseline,'current':now,'delta':now-baseline})
display(scorecard.round(3))
scorecard.to_csv(OUT/'monitor_population_scorecard.csv')
window_calls = calls[calls.Queue.eq(QUEUE) & calls['Call date'].between(start,end)]
active_calls = window_calls[window_calls['Recovery available']]
r = recovery_metrics(active_calls)
display(r.to_frame('sampled calls — eligible denominator').round(3))
print('All sampled calls in window:',len(window_calls),'; missing product:',window_calls['Product code'].isna().sum())
# Unique event IDs are validated; these are not total Care demand or unique households.
alerts = [
 ('Freshness', 'REVIEW' if stale_days>MAX_STALENESS_DAYS else 'OK', f'{stale_days} days since latest operations'),
 ('Complete date window','OK' if len(current)==WINDOW_DAYS else 'REVIEW',f'{len(current)}/{WINDOW_DAYS} queue-days'),
 ('Abandonment','REVIEW' if 100*(now.abandonment-baseline.abandonment)>ABANDONMENT_DELTA_PP else 'Within trigger',f'{100*(now.abandonment-baseline.abandonment):.2f} pp versus baseline'),
 ('Wait proxy','REVIEW' if now.wait_min_proxy-baseline.wait_min_proxy>WAIT_DELTA_MIN else 'Within trigger',f'{now.wait_min_proxy-baseline.wait_min_proxy:.2f} min versus baseline'),
 ('Recovery sample','INSUFFICIENT' if r.eligible_n<MIN_ELIGIBLE_SAMPLE else ('REVIEW' if r.complete_rate<COMPLETION_REVIEW_FLOOR else 'Within trigger'),f'{int(r.complete_n)}/{int(r.eligible_n)} completed both; sampled calls only')]
alert_table=pd.DataFrame(alerts,columns=['check','status','evidence'])
display(alert_table)
alert_table.to_csv(OUT/'monitor_alerts.csv',index=False)
"""),
('m',"""**How to read the scorecard:** AHT uses answered contacts; abandonment uses offered contacts. Wait is an offered-weighted proxy because the source does not specify its underlying wait denominator. Coverage is summed actual/planned Guide-days; occupancy is scheduled-hours weighted. Full-population operational comparisons and sampled recovery results are separate. August is a pre-incident reference, not a valid causal control for a future learning rollout.

Review triggers mean investigate with WFM/Quality. A low-sample recovery window is **insufficient evidence**. Meeting a trigger does not establish improvement. Daily aggregates cannot assess the queue impact of a 12-minute learning cohort.
"""),
('c',"""history = ops[ops.Queue.eq(QUEUE) & ops.Date.le(end)].copy()
history['week'] = history.Date.dt.to_period('W-SUN').dt.start_time
weekly = history.groupby('week').apply(population_metrics,include_groups=False)
fig, axes=plt.subplots(2,2,figsize=(13,8),sharex=True)
for axis,col,title in zip(axes.flat,['AHT_min','abandonment','WN7_contact_share','actual_planned'],
 ['Answered-weighted AHT (min)','Abandoned / offered','WN7-containing / answered','Actual / planned Guide-days']):
 axis.plot(weekly.index,weekly[col],marker='o',color='#246b8e');axis.set_title(title)
 axis.axvline(pd.Timestamp('2026-09-21'),color='grey',ls=':')
fig.suptitle(f'{QUEUE} • weekly population metrics (edge weeks may be partial)')
fig.autofmt_xdate();fig.tight_layout();plt.show()
weekly.to_csv(OUT/'monitor_weekly_population.csv')
"""),
('c',"""ec = calls[calls.Queue.eq(QUEUE) & calls['Recovery available'] & calls['Call date'].le(end)].copy()
ec['week'] = ec['Call date'].dt.to_period('W-SUN').dt.start_time
wr = ec.groupby('week').apply(recovery_metrics,include_groups=False)
display(wr.round(3))
fig,ax=plt.subplots(figsize=(11,4))
if len(wr):
 ax.plot(wr.index,wr.complete_rate,marker='o',label='sampled eligible complete rate')
 for dt,row in wr.iterrows(): ax.annotate(f'n={int(row.eligible_n)}',(dt,row.complete_rate),xytext=(0,8),textcoords='offset points')
 ax.axhline(COMPLETION_REVIEW_FLOOR,color='grey',ls='--',label='proposed review floor')
 ax.set_ylim(0,1.1);ax.legend()
ax.set_title('Both transactions complete • after queue-specific availability only')
fig.autofmt_xdate();plt.tight_layout();plt.show()
wr.to_csv(OUT/'monitor_weekly_sample_recovery.csv')
# Review candidates: sampled CALLS, not open cases or unique households. No contact action is taken.
candidates=active_calls[active_calls['Eligible for recovery'].eq('Yes') & ~active_calls['Complete recovery']]
fields=['Call ID','Call date','Queue','Serial verified','Conversation path','Replacement arranged','Northstar Plus attached','Disposition']
display(candidates[fields].head(20))
candidates[fields].to_csv(OUT/'sampled_recovery_review_candidates.csv',index=False)
print(len(candidates),'sampled review candidates. Confirm current case/transaction state before any action.')
"""),
('c',"""# QA and feedback are selected/voluntary; filter by call date AND event availability as-of.
q=D['qa_joined']; f=D['feedback_joined']
q=q[q.Queue.eq(QUEUE) & q['Call date'].between(start,end) & q['Review date'].le(AS_OF)]
f=f[f.Queue.eq(QUEUE) & f['Call date'].between(start,end) & f['Response date'].le(AS_OF)]
print('Selected QA reviews in window:',len(q),'; voluntary feedback responses:',len(f))
display(q['Selection reason'].value_counts().to_frame('review_n'))
if len(q):
 display(pd.DataFrame([{'behavior':col,'yes_n':q[col].eq('Yes').sum(),
                       'applicable_n':q[col].isin(['Yes','No']).sum()} for col in
 ['Acknowledged practical impact','Recognized recovery path','Recap complete']]))
if len(f):
 display(f.groupby('Conversation path').agg(responses=('Feedback ID','size'),mean_score=('Satisfaction score','mean')).round(2))
print('These are sample diagnostics, not population performance ratings.')
"""),
('m',"""## Operating review and future instrumentation
- **Daily, Care Operations/WFM:** examine abandonment, offered volume, AHT components, coverage and occupancy; review whether coaching must be rescheduled. Annotate notices, staffing changes, search releases, routing, and actual learning exposure dates.
- **Twice weekly, Quality/Team Leads (proposed):** inspect sampled incomplete recovery and ineligible branches, serial verification and recap. Separate system pending/failure from a missed action. Validate a manageable cadence with Elias and Priya rather than add unbudgeted manager work.
- **After two weeks, Dana:** use the pilot gates in notebook 01 and a contemporaneous comparison. Expand only with recovery quality, queue protection, and sufficient evidence. No before/after causal claim from this historical dashboard.

**Unavailable metrics must stay unavailable:** household-level 7-day repeat contacts; order shipment and Plus Applied timestamps; pending backlog and age; unsupported offers to ineligible households; follow-up kept; exposure by shift/tenure; interval service levels. Current data contains call-level transaction flags but cannot verify transaction status histories or later resolution. Add authorized event feeds and a stable household/case key with appropriate access controls before implementing these metrics. Never count sampled review candidates as a population backlog.

**Refresh contract:** preserve source copies and hashes; rerun cleaning/joins and inspect audit changes. The analysis notebook retains the supplied historical cutoff. Monitoring passes its explicit `AS_OF` parameter to the loader, so refreshed calls, reviews, and responses must not extend beyond that date. Update `AS_OF` and document the new extract contract when adding genuinely later data; future-date checks remain active. No thresholds or processes here have been implemented at Northstar.
""")])
