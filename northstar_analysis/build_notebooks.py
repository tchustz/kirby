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

# Reader-facing presentation is kept here so regeneration preserves the accessible layout.
import textwrap

def md(text): return n.v4.new_markdown_cell(textwrap.dedent(text).strip())
def code(text): return n.v4.new_code_cell(textwrap.dedent(text).strip())

p=R/'01_analysis_and_solution.ipynb'
b=n.read(p,as_version=4)
b.cells[0]=md('''
# Why are callers waiting longer — and what should Care do?
## The main finding: more calls, longer conversations, and unfinished recovery
**Northstar Home · fictional case · read as of October 2, 2026.** Records cover April–September 2026.

September brought more calls and more time spent on each answered call. A recurring Wi-Fi issue is an important part of the picture. For customers whose hub qualified for help, the approved response required **two actions: a replacement hub and a free year of Plus**. Many sampled General Care calls did not complete both.

**Recommended next step:** give Guides a short, practical recovery guide and practice with realistic cases. Make the right help article easier to find, and make sure unfinished account credits receive follow-up. Test this approach with small groups before a wider launch.

### How to read this notebook
Read the summary cards, charts, and “What this means” notes first. You do not need to understand Python. Results are already displayed; code can remain collapsed. “Guide” means customer-care representative. “Recovery” means the approved help for an eligible Wi-Fi hub.

1. **What changed?** August compared with September.
2. **Where does recovery break down?** A closer look at sampled calls.
3. **What should change?** A practical recommendation and small test.
4. **How trustworthy are the figures?** Sources and data checks in the appendix.

**Reading the evidence:** daily operating figures include all recorded calls in each queue. Individual-call analysis covers a smaller sample. Quality reviews and customer feedback were selected unevenly. These sources help identify patterns; they do not prove what caused the changes.
''')
b.cells[1].source += '\nfrom presentation import table, cards, comparison, PercentFormatter, StrMethodFormatter'
# Move technical data-cleaning details out of the opening story.
audit=b.cells[2:5]
b.cells=b.cells[:2]+[code('''
ops['Month'] = ops.Date.dt.to_period('M').astype(str)
monthly = ops.groupby(['Queue','Month']).apply(population_metrics, include_groups=False)
a, b = monthly.loc[('General Care','2026-08')], monthly.loc[('General Care','2026-09')]
post = calls[calls.Queue.eq('General Care') & calls['Recovery available'] & calls['Eligible for recovery'].eq('Yes')]
complete = int(post['Complete recovery'].sum())
cards([
 ('Calls arriving each day', f"{a.offered_per_day:,.0f} → {b.offered_per_day:,.0f}", 'General Care: August → September'),
 ('Time handling an answered call', f"{a.AHT_min:.1f} → {b.AHT_min:.1f} minutes", 'Includes talking, hold time, and after-call notes'),
 ('Callers hanging up before help', f"{a.abandonment:.1%} → {b.abandonment:.1%}", 'Of all calls arriving in General Care'),
 ('Both recovery steps completed', f"{complete} of {len(post)} sampled calls", 'Eligible General Care calls, September 21–30 only')])
'''),md('''
### The decision these findings support
Treat this as a recovery-workflow and capacity problem. Coaching should help Guides move from listening to the right action, while Operations fixes search and transaction obstacles.

**Important limit:** 76 of 204 describes the eligible calls in this sample. It does not mean that only 37% of all customers received help. We also cannot tell whether a later contact completed an unfinished recovery.
''')]+b.cells[5:]
for cell in b.cells:
 if cell.cell_type=='code':
  s=cell.source
  if 'display(monthly.round(3))' in s:
   cell.source='''ops['Month'] = ops.Date.dt.to_period('M').astype(str)
monthly = ops.groupby(['Queue','Month']).apply(population_metrics, include_groups=False)
monthly.to_csv(OUT/'monthly_population_metrics.csv')
gc = monthly.loc['General Care']
a, b = gc.loc['2026-08'], gc.loc['2026-09']
table(comparison(a,b).rename(columns={'Earlier period':'August 2026','Later period':'September 2026'}),
      '1. General Care was under more pressure in September',
      'All recorded daily operations. A percentage point is the difference between two percentages: 4% to 28% is a rise of 24 points.')'''
  elif "g = ops[ops.Queue.eq('General Care')]" in s:
   cell.source='''g = ops[ops.Queue.eq('General Care')].sort_values('Date')
fig, axes = plt.subplots(2,2,figsize=(13,8))
metrics = [('offered_per_day','More calls arrived each day','Calls per day',False),
 ('AHT_min','Each answered call took longer','Minutes per call',False),
 ('abandonment','More callers left before reaching help','Share of arriving calls',True),
 ('WN7_contact_share','Wi-Fi hub contacts became more common','Share of answered calls',True)]
for ax,(key,title,unit,percent) in zip(axes.flat,metrics):
 values=[a[key],b[key]]
 ax.bar(['August','September'],values,color=['#94a3b8','#246b8e'],width=.55)
 ax.set_title(title,loc='left',fontweight='bold');ax.set_ylabel(unit);ax.set_ylim(0,max(values)*1.28)
 for i,v in enumerate(values):
  ax.text(i,v+max(values)*.04,f'{v:.1%}' if percent else f'{v:,.1f}' if key=='AHT_min' else f'{v:,.0f}',ha='center',fontweight='bold')
 if percent: ax.yaxis.set_major_formatter(PercentFormatter(1))
 else: ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
fig.suptitle('August vs September • all General Care operating records',fontsize=15)
fig.tight_layout();plt.show()'''
  elif '# Descriptive product segments' in s:
   cell.source='''calls['Month'] = calls['Call date'].dt.to_period('M').astype(str)
segments = calls.groupby(['Queue','Month','Product segment'])['AHT minutes'].agg(n='size',mean='mean',median='median')
segment_view=segments.loc[('General Care',['2026-08','2026-09']),:].reset_index()
segment_view['Month']=segment_view['Month'].map({'2026-08':'August','2026-09':'September'})
segment_view['Average minutes']=segment_view['mean'].map('{:.1f}'.format)
table(segment_view[['Month','Product segment','n','Average minutes']].rename(columns={'Product segment':'Product group','n':'Calls in sample'}),
 'A closer look: call length by product group',
 'Sampled General Care calls only. Unknown means the product code was missing. WN7-containing includes the WNM-7 bundle; a product tag does not establish eligibility.')
components = ops.groupby(['Queue','Month']).apply(
 lambda x: pd.Series({k:np.average(x[k],weights=x['Answered contacts']) for k in
 ['Average talk minutes','Average hold minutes','Average wrap minutes']}),include_groups=False)
comp=components.loc[('General Care',['2026-08','2026-09']),:].reset_index().drop(columns='Queue')
comp.columns=['Month','Talking (minutes)','On hold (minutes)','After-call notes (minutes)']
comp['Month']=comp.Month.map({'2026-08':'August','2026-09':'September'})
for col in comp.columns[1:]:comp[col]=comp[col].map('{:.1f}'.format)
table(comp,'Where did handling time go?', 'All General Care answered calls; averages reflect the number of calls handled each day.')'''
  elif 'phase = calls.groupby' in s:
   cell.source='''phase = calls.groupby(['Queue','Phase']).apply(recovery_metrics,include_groups=False)
available = calls[calls['Recovery available']].copy()
recovery = available.groupby('Queue').apply(recovery_metrics,include_groups=False)
recovery.to_csv(OUT/'available_period_recovery.csv')
e = available[available['Eligible for recovery'].eq('Yes')]
path = e.groupby(['Queue','Conversation path'])['AHT minutes'].agg(n='size',mean='mean',median='median')
gc_eligible=e[e.Queue.eq('General Care')]
counts=[len(gc_eligible),int(gc_eligible['Serial verified'].eq('Yes').sum()),
        int(gc_eligible['Replacement arranged'].eq('Yes').sum()),int(gc_eligible['Complete recovery'].sum())]
fig,ax=plt.subplots(figsize=(11,4))
labels=['Eligible sampled calls','Serial check recorded','Replacement arranged','Replacement AND Plus completed']
ax.barh(labels[::-1],counts[::-1],color=['#157f65','#246b8e','#246b8e','#94a3b8'])
for i,v in enumerate(counts[::-1]):ax.text(v+3,i,f'{v} of {counts[0]} ({v/counts[0]:.0%})',va='center')
ax.set_xlim(0,counts[0]*1.45);ax.set_xlabel('Number of calls in the sample')
ax.set_title('2. Recovery was often left unfinished',loc='left',fontweight='bold')
fig.text(.02,.01,'General Care • eligible sampled calls, September 21–30. These are recorded actions, not timed steps.',fontsize=10)
fig.tight_layout(rect=[0,.05,1,1]);plt.show()
subset=path.loc['General Care'].reset_index()
fig,ax=plt.subplots(figsize=(11,4))
ax.barh(subset['Conversation path'],subset['mean'],color=['#157f65' if s=='Complete recovery' else '#64748b' for s in subset['Conversation path']])
for i,row in subset.iterrows():ax.text(row['mean']+.3,i,f"{row['mean']:.1f} min • {int(row['n'])} calls",va='center')
ax.set_xlim(0,subset['mean'].max()*1.4);ax.set_xlabel('Average handling time (minutes)')
ax.set_title('Completed recovery was associated with shorter calls',loc='left',fontweight='bold')
fig.text(.02,.01,'Same queue and period. This comparison does not prove that the recovery approach caused shorter calls.',fontsize=10)
fig.tight_layout(rect=[0,.05,1,1]);plt.show()'''
  elif "q = D['qa_joined']" in s:
   cell.source='''q = D['qa_joined']; f = D['feedback_joined']
qpost=q[q['Recovery available'] & q['Eligible for recovery'].eq('Yes')]
fpost=f[f['Recovery available'] & f['Eligible for recovery'].eq('Yes')]
feedback_view=fpost[fpost.Queue.eq('General Care')].groupby('Conversation path').agg(
 responses=('Feedback ID','size'),average=('Satisfaction score','mean')).reset_index()
feedback_view['Average rating (out of 5)']=feedback_view.average.map('{:.1f}'.format)
table(feedback_view[['Conversation path','responses','Average rating (out of 5)']].rename(
 columns={'Conversation path':'What happened on the call','responses':'People who responded'}),
 'What customers who responded told us',
 'Eligible General Care calls after September 21. Responses are voluntary and unevenly selected; these ratings do not represent every customer.')
qa_view=qpost.groupby('Queue').agg(reviewed=('QA review ID','size'),recap=('Recap complete',lambda x:x.eq('Yes').sum())).reset_index()
qa_view['Clear recap recorded']=qa_view.apply(lambda row:f"{row.recap} of {row.reviewed} reviewed calls",axis=1)
table(qa_view[['Queue','Clear recap recorded']],'Did reviewed calls explain what happens next?',
 'Selected quality reviews after each queue gained the recovery path. Different selection and dates mean the queues are not a fair head-to-head comparison.')'''
 else:
  cell.source=cell.source.replace('## 2. Queue pressure is a volume and handling problem','### What this means: more demand and longer calls are straining the queue').replace('## 3. Availability is not adoption or successful recovery','## 2. Why having an article was not enough').replace('## 4. Proposed solution: an actionable recovery cue plus a bounded test','## 3. What to put in Guides’ hands next week').replace('## 5. Ownership, capacity, and decision rules — proposals, not completed actions','## 4. A small test before a wider rollout — proposed, not yet implemented')
  cell.source=cell.source.replace('**Immediate learning response:**','**The practical learning response:**').replace('**Limits and next data needed:**','### What we still cannot tell from these files\n')
# Appendix keeps the underlying cleaning explanation without putting it ahead of findings.
audit[0].source=audit[0].source.replace('## 1. Data contract and cleaning','## Appendix: what the data includes and how it was checked')
audit[1].source='''table(D['audit'].rename(columns={'table':'Source table','raw_rows':'Rows received','header_excel_row':'Header row in Excel','missing_key':'Rows missing an identifier','clean_rows':'Rows kept','removed_rows':'Duplicate rows removed'}), 'Data checks: what was kept and removed')
missing = calls[['Product code','Reason code']].isna().sum()
table(pd.DataFrame({'Missing information':['Product code','Reason code'],'Calls affected':missing.values,
 'Share of sampled calls':[f'{v/len(calls):.1%}' for v in missing.values]}),'What information was missing?',
 'Missing values were left blank; they were not guessed.')
table(D['catalog_unmatched'].rename(columns={'Product code':'Code absent from catalog','sample_calls':'Calls retained in sample'}),
 'Product codes needing a catalog update', 'These calls remain in the analysis. No product descriptions were invented.')
export_clean(D)'''
b.cells.extend(audit)
# Split lengthy recommendation material into navigable sections, preserving the full content.
expanded=[]
for cell in b.cells:
 if cell.cell_type=='markdown' and '\n## ' in cell.source:
  parts=cell.source.split('\n## ')
  expanded.append(md(parts[0]));expanded.extend(md('## '+part) for part in parts[1:])
 else: expanded.append(cell)
b.cells=expanded
for cell in b.cells:
 if cell.cell_type=='code':cell.metadata.update({'jupyter':{'source_hidden':True},'collapsed':True})
n.write(b,p)

# Give the monitoring notebook the same plain-language labels and reading guidance.
p=R/'02_monitoring.ipynb';b=n.read(p,as_version=4)
b.cells[0]=md('''
# Are customers getting the full recovery — without a longer wait?
## A weekly check-in for Care leaders
**Historical demonstration, not a live feed.** The supplied operating records end September 30, 2026.

Use this notebook to answer three questions:
1. **Is the queue getting harder to manage?** Check call volume, time handling calls, and callers leaving before help.
2. **Are eligible customers receiving both parts of recovery?** Check replacement **and** Plus together.
3. **What needs attention?** Review warnings, then ask Quality or Workforce Management to investigate.

The results are already displayed. You do not need to edit code to read them. A colleague refreshing the report can change the queue, dates, and review settings in the next cell, then Run All. The default compares the latest seven available days with August. Thresholds are proposed discussion points, not agreed service targets.

**Quick glossary:** “eligible” means the serial result qualifies the hub for the approved offer; “complete recovery” means replacement and Plus are both recorded complete; “sample” means only some calls were examined. A warning means investigate, not that a particular Guide is at fault.
''')
for cell in b.cells:
 if cell.cell_type=='code':
  s=cell.source
  if 'from analysis_utils import *' in s:
   s=s.replace('from analysis_utils import *','from analysis_utils import *\nfrom presentation import table, cards, comparison, PercentFormatter')
   s=s.replace("display(D['audit'])", "display(Markdown('### 1. Report coverage and freshness\\nThe dates above describe the data available, not today’s live queue. No record of the proposed training rollout has been supplied.'))")
  if 'display(scorecard.round(3))' in s:
   s=s.replace('display(scorecard.round(3))',"table(comparison(baseline,now).rename(columns={'Earlier period':'Baseline period','Later period':'Latest available period'}), '2. Has queue pressure changed?', 'Baseline and current dates are shown above. Percentage points describe the gap between percentages.')")
   s=s.replace("display(r.to_frame('sampled calls — eligible denominator').round(3))", "cards([('Eligible calls examined',f'{int(r.eligible_n)}','This is a call sample, not total customer demand'),('Both recovery steps completed',f'{int(r.complete_n)} of {int(r.eligible_n)}',f'{r.complete_rate:.0%}' if r.eligible_n else 'No eligible calls in this window'),('Recovery not recorded complete',f'{int(r.incomplete_n)}','Confirm the latest case status before acting')])")
   s=s.replace('display(alert_table)',"table(alert_table.rename(columns={'check':'What to check','status':'Review status','evidence':'Why this status appears'}), '3. What needs attention?', 'REVIEW = investigate. INSUFFICIENT = too few eligible sampled calls to judge. OK / Within trigger does not prove the approach is working.')")
  if "['Answered-weighted AHT (min)'" in s:
   s=s.replace("['Answered-weighted AHT (min)','Abandoned / offered','WN7-containing / answered','Actual / planned Guide-days']", "['Average handling time (minutes)','Callers leaving before help (%)','Answered calls tagged WN7 / WNM-7 (%)','Staff present vs planned (%)']")
   s=s.replace("axis.plot(weekly.index,weekly[col],marker='o',color='#246b8e');axis.set_title(title)","axis.plot(weekly.index,weekly[col],marker='o',color='#246b8e');axis.set_title(title)\n if col != 'AHT_min': axis.yaxis.set_major_formatter(PercentFormatter(1))")
  s=s.replace('display(wr.round(3))',"table(pd.DataFrame({'Week starting':wr.index.strftime('%b %d'), 'Eligible calls examined':wr.eligible_n.astype(int), 'Both steps completed':wr.complete_n.astype(int), 'Completion rate':wr.complete_rate.map(lambda v:f'{v:.0%}' if pd.notna(v) else 'No eligible calls')}), '4. Is recovery improving over time?', 'Only sampled eligible calls after this queue gained the recovery path. Short edge weeks and small samples need caution.')")
  s=s.replace("ax.set_ylim(0,1.1);ax.legend()", "ax.set_ylim(0,1.1);ax.yaxis.set_major_formatter(PercentFormatter(1));ax.legend()")
  s=s.replace("display(candidates[fields].head(20))", "table(candidates[fields].head(20).rename(columns={'Call ID':'Call reference','Call date':'Date','Serial verified':'Serial check recorded','Conversation path':'Call approach','Northstar Plus attached':'Plus recorded complete'}), 'Calls to review with Quality', 'Up to 20 sampled calls shown. These are not a list of all open household cases; later resolution is unknown.')")
  s=s.replace("display(q['Selection reason'].value_counts().to_frame('review_n'))", "table(q['Selection reason'].value_counts().rename_axis('Why calls were selected').reset_index(name='Reviews'), '5. How were the quality reviews selected?', 'These are selected reviews, not a representative survey of all calls.')")
  s=s.replace("'yes_n':q[col].eq('Yes').sum()", "'Calls with behavior recorded':q[col].eq('Yes').sum()")
  s=s.replace("'applicable_n':q[col].isin(['Yes','No']).sum()", "'Calls assessed':q[col].isin(['Yes','No']).sum()")
  s=s.replace("mean_score=('Satisfaction score','mean')).round(2)", "mean_score=('Satisfaction score','mean')).round(1).rename(columns={'responses':'People who responded','mean_score':'Average rating out of 5'})")
  cell.source=s
  cell.metadata.update({'jupyter':{'source_hidden':True},'collapsed':True})
  if '# User controls.' in s:cell.metadata.update({'jupyter':{'source_hidden':False},'collapsed':False})
 else:
  cell.source=cell.source.replace('## Operating review and future instrumentation','## 6. Who should act on these results?').replace('**Unavailable metrics must stay unavailable:**','### Questions this report cannot answer yet\n').replace('**Refresh contract:**','### For the colleague refreshing the data\n')
n.write(b,p)

# Final plain-language pass: keep methodological details in the appendix.
p=R/'01_analysis_and_solution.ipynb';b=n.read(p,as_version=4)
for cell in b.cells:
 if cell.cell_type=='markdown':
  s=cell.source
  if s.startswith('### What this means:'):
   cell.source='''### What this means: callers face pressure at both ends
More people called in September, and each answered call took longer. About **28 in every 100 arriving callers hung up before reaching help**, compared with about **4 in every 100** in August.

Calls tagged with the WN7 hub or its WNM-7 bundle also became more common. At the same time, the share of planned staff actually present fell slightly, from about 94% to 92%.

**What to do with this finding:** address call handling and coverage together. The records do not tell us how much of the overall rise in call time was caused by the Wi-Fi issue. A product tag is not proof of a defective or eligible hub.'''
  elif s.startswith('## 2. Why having an article'):
   cell.source='''## 2. Why having an article was not enough
The approved offer became available to different teams at different times:

| Date | What became possible |
|---|---|
| August 31 | Product confirmed the Wi-Fi issue. |
| September 10 | The replacement plus free-year offer was approved. |
| September 12 | Specialist Care began a small trial. |
| September 21 | General Care gained access to the help article. |

The article went into a weekly update, but there was no separate incident alert or scheduled briefing across shifts. We do not know who read it. Meeting notes also describe Guides finding an older restart article or being unsure what to do when a Plus credit stayed pending.

**What this means:** putting guidance online is a start. Guides also need to find it, recognize when to use it, and finish both recovery actions. The next chart looks only at eligible General Care calls **after** its article became available; earlier calls are not judged against a process they could not yet use.'''
  elif s.startswith('In General Care after September 21'):
   cell.source='''### What the recovery charts tell us
Of **204 eligible General Care calls examined from September 21–30**:

- **76 completed both actions**: a replacement and Plus.
- **13 arranged a replacement but did not record Plus as attached.**
- **115 followed generic troubleshooting** rather than completing the approved offer.

The records also show a serial check on 159 of those 204 calls. The horizontal bars show recorded actions, not the exact order or timing of steps.

**Complete recovery was associated with shorter calls:** about **10.9 minutes across 76 calls**, compared with **19.8 minutes across 115 generic-troubleshooting calls**. This suggests a useful approach to test, but does not prove it makes calls shorter. Easier cases, different Guides, or other factors could explain part of the difference.

Specialist Care completed both steps on 163 of 193 eligible sampled calls after its September 12 start. Those customers and dates differ, so that figure is useful background rather than a fair ranking of the teams.

**What to do with this finding:** coach complete recovery, not speed alone. The data cannot show whether an unfinished call was resolved later.'''
  elif s.startswith('Selected feedback is consistent'):
   cell.source='''### Customers who responded described a better experience after complete recovery
Among eligible General Care respondents, those with both recovery steps complete rated the experience **4.5 out of 5 on average (47 responses)**. Those who went through generic troubleshooting averaged **1.5 out of 5 (61 responses)**.

**Treat this as a clue, not a company-wide satisfaction score.** Customers chose whether to respond, and the feedback collection placed extra attention on WN7. Quality reviewers also deliberately selected higher-risk and longer calls. Their findings help identify what to coach; they do not tell us how often every Guide makes a mistake.'''
  else:
   s=s.replace('**Test plan:** proposed two-week staggered test; collect a one-week pre-period where the General article is already available and compare contemporaneous eligible calls within General Care. If randomization is impractical, report descriptive changes with strata for shift, tenure, mix, and staffing. Log simultaneous article/search/routing changes; do not isolate a training effect from a bundled test.',
   '### How to test the recommendation fairly\nRun the proposed test for two weeks with small groups at different times. First collect a week of results while the article is already available. Compare with similar General Care teams handling calls during the test. If practical, assign the groups by chance. Otherwise explain differences in shifts, Guide experience, call types, and staffing. Record any search or system changes happening at the same time: improved results would not tell us which change helped most.')
   s=s.replace('**Proposed gates requiring owner agreement:** 100% safe branch selection in practice before unsupervised use; no unsupported offer in reviewed ineligible calls; eligible sample completion improves ≥15 percentage points over comparable baseline with denominator ≥30 per group; no >2-point abandonment or >0.5-minute wait deterioration in matched operating windows. These are operational starting proposals, not statistically validated thresholds. Small/biased samples yield an inconclusive result, not success. Review transaction failures separately from Guide behavior.',
   '### What would justify a wider rollout?\nThese starting rules need agreement from the owners; they are not proven targets.\n\n- Guides choose the safe next step in every practice case, including cases that do not qualify.\n- Reviewed ineligible calls contain no unsupported offer.\n- Completion of both steps improves by at least **15 percentage points** compared with a similar starting period. For example, 40% to 55% is a 15-point increase. Examine at least **30 eligible calls in each group**; even then, consider how calls were selected before drawing a conclusion.\n- In comparable operating windows, the share hanging up before help does not worsen by more than **2 percentage points**, and estimated wait does not worsen by more than **half a minute**.\n\nIf too few calls were reviewed, the answer is “we do not know yet.” Separate system failures from missed Guide actions.')
   s=s.replace('no household/account IDs to measure repeat contacts, no order/credit event ledger to verify final fulfillment or backlog age, no exposure/roster/tenure file, no reliable wait numerator or interval-level staffing. Request those internally before claiming repeat-contact reduction, causal impact, closed recovery backlog, or sustainable capacity. Sample incomplete calls exported by monitoring are review candidates, not a deduplicated household backlog.',
   'We cannot identify repeat calls from the same household, check whether an order shipped or a credit was later applied, or see which Guides took part in training. Daily totals also hide busy periods within a shift. Those extra records are needed before claiming fewer repeat calls, a successful rollout, or enough ongoing capacity. The monitoring call list is a starting point for review, not a count of all households still waiting.')
   cell.source=s
 elif cell.cell_type=='code' and 'export_clean(D)' in cell.source:
  cell.source=cell.source.replace('export_clean(D)', "export_clean({**D, 'calls':calls.drop(columns='Month',errors='ignore')})")
n.write(b,p)

p=R/'02_monitoring.ipynb';b=n.read(p,as_version=4)
for cell in b.cells:
 if cell.cell_type=='markdown' and cell.source.startswith('**How to read the scorecard:**'):
  cell.source='''### How to read the numbers above
**Call time** includes talking, time on hold, and after-call notes. Busier days contribute more to the overall average. **Callers leaving before help** means the number who hung up divided by all arriving calls. **Staff present vs planned** compares the number of Guides available with the schedule.

The wait figure is an **estimate**: the file gives daily average waits but does not explain exactly which callers are included. We combine those daily figures using the number of arriving calls.

The queue figures cover all recorded calls. The recovery cards cover only **eligible calls in the sample**. August is useful background, but it is not a fair test of training effectiveness because the situation changed in September.

**What to do next:** review any warning with the relevant owner. Too few calls means there is not enough evidence. A result within a trigger does not prove success, and daily totals cannot predict what happens when a small group leaves the phones for practice.'''
 if cell.cell_type=='code':
  cell.source=cell.source.replace("display(pd.DataFrame([{'behavior':col,", "table(pd.DataFrame([{'Behavior checked':col,")
  cell.source=cell.source.replace("['Acknowledged practical impact','Recognized recovery path','Recap complete']]))", "['Acknowledged practical impact','Recognized recovery path','Recap complete']]), 'What reviewers heard', 'Each behavior has its own count of assessed calls; unassessed calls are not treated as failures.')")
  cell.source=cell.source.replace("display(f.groupby('Conversation path').agg(responses=('Feedback ID','size'),mean_score=('Satisfaction score','mean')).round(1).rename(columns={'responses':'People who responded','mean_score':'Average rating out of 5'}))", "table(f.groupby('Conversation path').agg(responses=('Feedback ID','size'),mean_score=('Satisfaction score','mean')).round(1).reset_index().rename(columns={'Conversation path':'What happened on the call','responses':'People who responded','mean_score':'Average rating out of 5'}), 'What responding customers reported', 'Voluntary responses only; small groups can be misleading.')")
n.write(b,p)

# Manual-feed instructions and editable source location for ongoing monitoring.
p=R/'02_monitoring.ipynb';b=n.read(p,as_version=4)
b.cells[0].source=b.cells[0].source.replace('**Historical demonstration, not a live feed.** The supplied operating records end September 30, 2026.',
 '**A manually refreshed monitoring feed.** This notebook updates when you supply new exports and run it; it does not refresh continuously. The saved example still uses operating records through September 30, 2026.')
refresh_guide=md('''
## Before you refresh: update the files, change the settings, then Run All
You can use this notebook for ongoing progress reviews. No connection to Orbit or another live system has been configured. Each run takes a fresh look at the Excel files you provide.

### Step 1 — Get a complete, consistent set of exports
Save the previous exports outside the active input folder so you can recover them. Put the new files in **`northstar_analysis/data/raw/`**, or use a separate folder and enter its path in **EDIT HERE — refresh settings** below.

| File to supply | Sheets that must remain available | What it updates |
|---|---|---|
| `Orbit_operations.xlsx` | `Daily operations`, `Call sample`, `Staffing`, `Product catalog` | Call volume, handling time, waiting, staffing, and sampled recovery actions |
| `Quality_and_feedback.xlsx` | `QA reviews`, `Customer feedback` | Selected quality checks and voluntary customer ratings |

**Replace each workbook with a full updated export, not just the newest rows.** Keep enough history for your baseline and weekly charts. The notebook does not append files or remember previous imports. Preserve sheet names, column names, identifiers, and Yes/No values. It finds the header row automatically. Both sources should come from a coordinated extract; newer QA or feedback IDs must match calls in the call sample. Keep QA and feedback sheets even if no new reviews or responses arrived.

Use complete daily records rather than partially completed days: the charts compare daily totals. A more recent daily export paired with an old call sample does **not** provide fresh recovery results. Check each source date shown after loading.

### Step 2 — Edit only the settings cell below for a routine refresh
The cell is labeled **EDIT HERE — refresh settings** and stays visible. Keep quotation marks around paths and dates. Dates use **year-month-day**, such as `'2026-10-16'`.

| Setting in the code | What you change | Example or guidance |
|---|---|---|
| `INPUT_FOLDER` | Folder containing both workbooks | `'data/raw'` is relative to this notebook’s folder; an absolute folder path also works. |
| `AS_OF` | Date through which this report may use events | For an October 16 review, set `'2026-10-16'`. Do not automatically move it just to make old data look fresh. Events after this date stop the run. |
| `QUEUE` | Team to review | `'General Care'` or `'Specialist Care'`. |
| `WINDOW_DAYS` | Number of recent calendar days to compare | `7` for a week or `14` for two weeks. The window ends on the latest available operating date, not automatically on `AS_OF`. |
| `BASELINE_START`, `BASELINE_END` | Earlier operating period for comparison | Keep a fixed agreed baseline when tracking progress. Moving it every run changes the question you are answering. Both dates must be included in the exports. |
| `MIN_ELIGIBLE_SAMPLE` | Minimum eligible sampled calls before judging recovery | Default `30` is a proposed review rule, not a guarantee of reliable evidence. |
| `MAX_STALENESS_DAYS` | How old operating records can be before a warning appears | Default `3`; source dates and sample counts still need inspection. |
| `ABANDONMENT_DELTA_PP`, `WAIT_DELTA_MIN` | How much worsening prompts a review | `2.0` means two percentage points; `0.5` means half a minute. Change only with the owners’ agreement. |
| `COMPLETION_REVIEW_FLOOR` | Proposed recovery completion threshold | `0.80` means 80%. This is a review trigger, not an established service target. |

**Example:** keep the filenames above, change `INPUT_FOLDER` to your new export folder, set `AS_OF = '2026-10-16'`, and leave `WINDOW_DAYS = 7`. With operating records through October 14, the window will be October 8–14. If your files end in September, changing `AS_OF` alone will only show that they are older.

### Step 3 — Restart, run, check, and save
1. Choose **Clear All Outputs** to remove old results, then **Kernel → Restart Kernel and Run All Cells** (some editors call this **Restart & Run All**). This clears old variables and reruns every calculation. Wait for all cells to finish.
2. Check **Report coverage and freshness**: confirm the run time, source folder, latest operating date, dates of the call sample/reviews/feedback, and comparison periods.
3. Check warnings and eligible-call counts before interpreting progress. A newer report run is not the same as newer source data. Look for consistent direction across several weeks, not just one small sample.
4. Save the notebook to retain the refreshed charts. Generated monitoring CSVs in `outputs/` are overwritten each run; archive them first if you need snapshots. `monitor_refresh_receipt.json` records when the data was loaded, settings, and workbook hashes so you can identify the inputs used. It does not certify that a failed run finished successfully.

**If a cell fails, do not share the partly refreshed dashboard.** Fix the issue and restart/run all again; old outputs further down may still be visible. Confirm that the last cell says **“Refresh complete”** with the same run time shown at the top. Notebook 01 is the fixed historical analysis; refresh **this monitoring notebook** for later records.
''')
b.cells.insert(1,refresh_guide)
for cell in b.cells:
 if cell.cell_type!='code':continue
 s=cell.source
 if '# User controls.' in s:
  s=s.replace('# User controls. Queue must match the workbook labels.',
 '# EDIT HERE — refresh settings\n# Change this folder and date when new exports arrive; then Restart & Run All.\nINPUT_FOLDER = "data/raw"  # Contains both workbooks; relative to this notebook folder.\n# Queue must match the workbook labels.')
 if 'D = load_data(as_of=AS_OF, call_through=AS_OF)' in s:
  s=s.replace('D = load_data(as_of=AS_OF, call_through=AS_OF)',
 '''# READ NEW FILES HERE. Normally, change INPUT_FOLDER in the settings cell instead.
INPUT_PATH = Path(INPUT_FOLDER).expanduser()
if not INPUT_PATH.is_absolute(): INPUT_PATH = ROOT / INPUT_PATH
if not INPUT_PATH.is_dir(): raise ValueError(f'Input folder not found: {INPUT_PATH}')
RUN_AT = pd.Timestamp.now(tz='UTC')
D = load_data(raw=INPUT_PATH, as_of=AS_OF, call_through=AS_OF)''')
  s += '''
# Show separate source dates so old samples cannot look fresh beside new daily totals.
coverage_rows=[]
for name,label,date_col in [('daily','Daily operations','Date'),('staff','Staffing','Date'),
 ('calls','Sampled calls','Call date'),('qa','Quality reviews (review date)','Review date'),
 ('feedback','Customer feedback (response date)','Response date')]:
 frame=D[name]
 frame=frame[frame.Queue.eq(QUEUE)]
 dates=frame[date_col].dropna()
 coverage_rows.append({'Source':label,'Records available':len(frame),
  'Latest event date':dates.max().strftime('%Y-%m-%d') if len(dates) else 'No records',
  'Age at report date':f'{(AS_OF-dates.max()).days} days' if len(dates) else 'Not available'})
display(Markdown(f'**Data loaded at:** {RUN_AT.strftime("%Y-%m-%d %H:%M UTC")}  \\n**Input folder:** `{INPUT_PATH}`  \\nThis is the last manual load time; it is not a live connection.'))
table(pd.DataFrame(coverage_rows),'Check the dates of every source',
 'Review and response dates may lag call dates. A recent daily total does not make an old call sample current. Empty-window or low-sample recovery results cannot show current progress.')
import hashlib, json
OUT.mkdir(exist_ok=True)
receipt={'loaded_at_utc':RUN_AT.isoformat(),'as_of':AS_OF.date().isoformat(),
 'input_folder':str(INPUT_PATH),'queue':QUEUE,'window_start':start.date().isoformat(),
 'window_end':end.date().isoformat(),'baseline_start':BASELINE_START,'baseline_end':BASELINE_END,
 'source_coverage':coverage_rows,
 'review_settings':{'window_days':WINDOW_DAYS,'minimum_eligible_calls':MIN_ELIGIBLE_SAMPLE,
 'max_staleness_days':MAX_STALENESS_DAYS,'abandonment_delta_pp':ABANDONMENT_DELTA_PP,
 'wait_delta_minutes':WAIT_DELTA_MIN,'completion_review_floor':COMPLETION_REVIEW_FLOOR},
 'workbook_sha256':{name:hashlib.sha256((INPUT_PATH/name).read_bytes()).hexdigest() for name in
 ['Orbit_operations.xlsx','Quality_and_feedback.xlsx']}}
(OUT/'monitor_refresh_receipt.json').write_text(json.dumps(receipt,indent=2))
'''
 cell.source=s
b.cells.append(md('''
## When the export format or recovery process changes
Routine refreshes need edits only in **EDIT HERE — refresh settings**. Ask the colleague maintaining the notebook to make the following changes when the source itself changes:

| Change | Exact place to update | Check afterwards |
|---|---|---|
| Different workbook names or sheet names | `analysis_utils.py`, `load_data()`, the `specs` mapping; also the workbook list in the **READ NEW FILES HERE** cell and this guide | Every required table loads and the receipt hashes the right files. |
| Renamed columns or different status values | `analysis_utils.py`, `load_data()` cleaning and validation; code cells using those fields | Keep unique identifiers, duplicate checks, staffing joins, and the rule requiring both recovery actions. Do not just suppress an error. |
| Different queues, changed offer, or a newly approved path | `analysis_utils.py`, `load_data()`, the `Recovery available` and `Complete recovery` definitions; `recovery_metrics()` | Confirm the new business rules and effective dates with Care/Product, then review labels and comparisons. Existing rules are specific to this case. |
| Different operating comparison or review triggers | **EDIT HERE — refresh settings**, near the top of this notebook | Record why the baseline or triggers changed so progress remains interpretable. |
| Connecting an API or database in future | Replace the Excel-reading part of `load_data()` with an authorized connector that returns the same validated tables | Credentials belong in secure configuration, never in notebook cells. No such connection exists in this version. |

If workbook headings or fields are missing, restore the agreed format or update the loader with a developer. If joins fail, get matching calls, staffing, and review exports. If a baseline is empty, supply its history or deliberately choose an available baseline. If data is dated after `AS_OF`, correct the report date or supply the appropriate snapshot. Do not bypass checks to obtain a chart.

**Tracking progress after a rollout:** keep a record of actual rollout dates, shifts/Guides included, search/system changes, and staffing changes. The weekly chart shows change over time, but without those extra records it cannot tell whether training caused a change. The supplied sources do not yet contain rollout participation or household-level repeat-call data.
'''))
b.cells.append(code('''
# A successful refresh reaches this final cell without earlier errors.
display(Markdown(f'### Refresh complete\\nAll monitoring cells finished for **{QUEUE}**. '
                 f'Data loaded at **{RUN_AT.strftime("%Y-%m-%d %H:%M UTC")}**; '
                 f'operating window **{start.date()}–{end.date()}**. '
                 'Save this notebook to retain these results.'))
'''))
for cell in b.cells:
 if cell.cell_type=='code':
  cell.metadata.update({'jupyter':{'source_hidden':'# EDIT HERE' not in cell.source},'collapsed':'# EDIT HERE' not in cell.source})
n.write(b,p)
