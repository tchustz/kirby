"""Manually refreshed learning early-warning pilot. No remote connections or messages.
Run: python learning_monitor.py --config learning_settings.json
"""
from pathlib import Path
from html import escape
import argparse
import hashlib
import json
import os
import numpy as np
import pandas as pd
from analysis_utils import load_data, population_metrics, ROOT

# Shared settings are used by both the notebook and the optional scheduled command.
def read_settings(path=ROOT/'learning_settings.json'):
    cfg=json.loads(Path(path).read_text())
    for key in ['input_folder','output_folder','issue_log']:
        p=Path(cfg[key]).expanduser(); cfg[key]=str(p if p.is_absolute() else ROOT/p)
    return cfg


def validate_settings(c):
    start,end,asof=map(pd.Timestamp,[c['baseline_start'],c['baseline_end'],c['as_of']])
    if start>end or end>asof: raise ValueError('Baseline dates must be ordered and at/before as_of')
    if c['mode'] not in ['historical_demo','pilot']: raise ValueError('mode must be historical_demo or pilot')
    for k in ['window_days','consecutive_weeks','min_sample_per_week','min_baseline_sample','min_qa_per_week',
              'min_feedback_per_week','min_guide_calls','min_guide_reviews','min_guide_weeks']:
        if not isinstance(c[k],int) or c[k]<1: raise ValueError(f'{k} must be a positive integer')
    for k in ['aht_increase_fraction','volume_increase_fraction','qa_gap_fraction','low_feedback_fraction','generic_troubleshooting_fraction']:
        if not 0<=c[k]<=1: raise ValueError(f'{k} must be between 0 and 1')
    if c['max_source_age_days']<0 or c['abandonment_increase_pp']<0 or c['segment_share_increase_pp']<0:
        raise ValueError('Age and percentage-point triggers cannot be negative')
    if c.get('product_grouping','code') not in ['code','family']:raise ValueError('product_grouping must be code or family')
    if not isinstance(c['guide_view_approved'],bool): raise ValueError('Guide approval must be true/false')


def week_start(dates):
    return dates.dt.to_period('W-SUN').dt.start_time


def group_apply(frame,keys,func):
    return frame.groupby(keys,dropna=False).apply(func,include_groups=False).reset_index()


def prepare(c):
    validate_settings(c)
    D=load_data(raw=Path(c['input_folder']),as_of=c['as_of'],call_through=c['as_of'])
    asof=pd.Timestamp(c['as_of'])
    if D['ops'].Date.max()>asof: raise ValueError('Operations extend beyond as_of')
    if D['ops'].Date.min()>pd.Timestamp(c['baseline_start']): raise ValueError('Exports do not cover the requested baseline')
    for name in ['calls','qa_joined','feedback_joined']:
        d=D[name].copy()
        d['Product view']=d['Product code'].fillna('Unknown') if c.get('product_grouping','code')=='code' else d['Product segment']
        d['Reason view']=d['Reason code'].fillna('Unknown')
        d['week']=week_start(d['Call date'])
        D[name]=d
    D['ops']['week']=week_start(D['ops'].Date)
    coverage=[]
    for name,col in [('daily','Date'),('staff','Date'),('calls','Call date'),('qa','Review date'),('feedback','Response date')]:
        for queue in D['ops'].Queue.unique():
            d=D[name][D[name].Queue.eq(queue)]
            latest=d[col].max()
            age=(asof-latest).days if pd.notna(latest) else None
            coverage.append({'Source':name,'Queue':queue,'Records':len(d),'Latest date':latest,
                             'Age in days':age,'Freshness':'No records' if age is None else 'REVIEW — older source' if age>c['max_source_age_days'] else 'Within age setting'})
    return D,pd.DataFrame(coverage)


def build_metrics(D,c):
    op=group_apply(D['ops'],['Queue','week'],population_metrics)
    counts=D['ops'].groupby(['Queue','week']).agg(first=('Date','min'),last=('Date','max'),observed_days=('Date','nunique')).reset_index()
    op=op.merge(counts,on=['Queue','week'],validate='one_to_one')
    op['complete_week']=op.observed_days.eq(7)&op['first'].eq(op.week)&op['last'].eq(op.week+pd.Timedelta(days=6))
    baseline_rows=[]
    for queue,d in D['ops'].groupby('Queue'):
        base=d[d.Date.between(c['baseline_start'],c['baseline_end'])]
        expected=(pd.Timestamp(c['baseline_end'])-pd.Timestamp(c['baseline_start'])).days+1
        if base.Date.nunique()!=expected: raise ValueError(f'{queue}: missing baseline days')
        row=population_metrics(base).to_dict();row['Queue']=queue;baseline_rows.append(row)
    baselines=pd.DataFrame(baseline_rows).set_index('Queue')
    # Aggregate before looping: every sampled call contributes to four separate views,
    # never sum those views together as if they were distinct calls.
    calls=D['calls'].copy()
    calls['_eligible']=calls['Recovery available']&calls['Eligible for recovery'].eq('Yes')
    calls['_generic']=calls['_eligible']&calls['Conversation path'].eq('Generic troubleshooting')
    calls['_complete']=calls['_eligible']&calls['Complete recovery']
    basecalls=calls[calls['Call date'].between(c['baseline_start'],c['baseline_end'])]
    totals=calls.groupby(['Queue','week']).size().rename('_total').reset_index()
    basetotals=basecalls.groupby('Queue').size().rename('_base_total').reset_index()
    parts=[]
    for fields in [['Queue'],['Queue','Product view'],['Queue','Reason view'],['Queue','Product view','Reason view']]:
        a=calls.groupby(fields+['week'],dropna=False).agg(sample_n=('Call ID','size'),mean_aht=('AHT minutes','mean'),
            eligible_n=('_eligible','sum'),generic_n=('_generic','sum'),complete_n=('_complete','sum')).reset_index()
        b=basecalls.groupby(fields,dropna=False).agg(baseline_n=('Call ID','size'),baseline_aht=('AHT minutes','mean')).reset_index()
        a=a.merge(b,on=fields,how='left',validate='many_to_one').merge(totals,on=['Queue','week'],validate='many_to_one').merge(basetotals,on='Queue',validate='many_to_one')
        a['share']=a.sample_n/a['_total'];a['baseline_share']=a.baseline_n.fillna(0)/a['_base_total']
        a['baseline_n']=a.baseline_n.fillna(0)
        a['Product']=a['Product view'] if 'Product view' in fields else 'All'
        a['Reason']=a['Reason view'] if 'Reason view' in fields else 'All'
        parts.append(a[['Queue','Product','Reason','week','sample_n','mean_aht','share','baseline_n','baseline_aht','baseline_share','eligible_n','generic_n','complete_n']])
    sample=pd.concat(parts,ignore_index=True)
    qa_rows=[]
    behaviors=['Acknowledged practical impact','Recognized recovery path','Recap complete']
    for (queue,week),d in D['qa_joined'].groupby(['Queue','week']):
        for behavior in behaviors:
            a=d[d[behavior].isin(['Yes','No'])]
            if behavior=='Recognized recovery path':a=a[a['Recovery available']&a['Eligible for recovery'].eq('Yes')]
            qa_rows.append({'Queue':queue,'week':week,'Behavior':behavior,'review_n':len(a),
                            'gap_n':int(a[behavior].eq('No').sum()),'gap_rate':a[behavior].eq('No').mean() if len(a) else np.nan})
    qa=pd.DataFrame(qa_rows,columns=['Queue','week','Behavior','review_n','gap_n','gap_rate'])
    feedback=group_apply(D['feedback_joined'],['Queue','week'],lambda d:pd.Series({
        'response_n':len(d),'mean_score':pd.to_numeric(d['Satisfaction score']).mean(),
        'low_n':pd.to_numeric(d['Satisfaction score']).le(2).sum(),
        'low_rate':pd.to_numeric(d['Satisfaction score']).le(2).mean()}))
    if D['feedback_joined'].empty:feedback=pd.DataFrame(columns=['Queue','week','response_n','mean_score','low_n','low_rate'])
    return op,baselines,sample,qa,feedback


def detect(D,c,op,base,sample,qa,feedback):
    # Only consecutive Monday–Sunday weeks with complete daily operations support a flag.
    # Partial latest weeks remain visible in charts but are not used for sustained alerts.
    rows=[];evaluations=[]
    now=pd.Timestamp.now(tz='UTC')
    for queue,full in op[op.complete_week].groupby('Queue'):
        last=full.week.max()
        weeks=pd.date_range(end=last,periods=c['consecutive_weeks'],freq='7D')
        recent=op[op.Queue.eq(queue)&op.week.isin(weeks)].sort_values('week')
        latest_source=D['ops'].loc[D['ops'].Queue.eq(queue),'Date'].max()
        def check(metric,frame,values,eligible,condition,scope='All',reason='All',priority='P2',owner='Learning + Care Quality',basis='Sampled calls',action='Review examples with Care Quality before choosing an intervention'):
            aligned=frame.assign(_value=values,_eligible=eligible,_condition=condition).set_index('week').reindex(weeks)
            ready=(aligned['_eligible'].eq(True)&aligned['_value'].notna()).all()
            ready=ready and len(recent)==len(weeks) and recent.complete_week.all()
            expected_end=latest_source if latest_source.weekday()==6 else latest_source-pd.Timedelta(days=latest_source.weekday()+1)
            ready=ready and last+pd.Timedelta(days=6)==expected_end
            ready=ready and weeks.min()>pd.Timestamp(c['baseline_end'])
            ready=ready and (pd.Timestamp(c['as_of'])-latest_source).days<=c['max_source_age_days']
            flagged=bool(ready and aligned['_condition'].eq(True).all())
            evaluations.append({'Queue':queue,'Product':scope,'Reason':reason,'Signal':metric,
                'Status':'INVESTIGATE' if flagged else 'Not triggered' if ready else 'INSUFFICIENT / STALE',
                'Latest evaluated week ending':last+pd.Timedelta(days=6),'Evidence type':basis})
            if not flagged:return
            raw='|'.join([c['mode'],queue,scope,reason,metric])
            values=aligned['_value'].tolist()
            evidence=[]
            for week,value in zip(weeks,values):
                rawrow=aligned.loc[week]
                if 'percentage points' in metric or metric=='Callers leaving before help increase':
                    meaning=f'{value:+.1f} percentage points from baseline'
                elif metric in ['Queue handling time increase','Arriving calls increase','Sample handling time increase']:
                    meaning=f'{value:+.1%} from baseline'
                else:meaning=f'{value:.1%} of assessed observations'
                if basis=='Full daily population':
                    number=rawrow['answered'] if metric=='Queue handling time increase' else rawrow['offered']
                    count=f'{int(number):,} '+('answered calls' if metric=='Queue handling time increase' else 'arriving calls')
                elif basis=='Selected QA reviews':count=f'{int(rawrow.review_n)} assessed reviews'
                elif basis=='Voluntary selected responses':count=f'{int(rawrow.response_n)} responses'
                elif metric=='Eligible calls using generic troubleshooting':count=f'{int(rawrow.eligible_n)} eligible sampled calls'
                elif 'percentage points' in metric:
                    total=round(rawrow.sample_n/rawrow['share']) if rawrow['share'] else 0
                    count=f'{int(rawrow.sample_n)} of {total} sampled calls'
                else:count=f'{int(rawrow.sample_n)} sampled calls; baseline {int(rawrow.baseline_n)}'
                evidence.append(f'Week ending {(week+pd.Timedelta(days=6)).date()}: {meaning} ({count})')
            rows.append({'issue_id':hashlib.sha256(raw.encode()).hexdigest()[:14],
                'priority':priority,'queue':queue,'product':scope,'reason':reason,'signal':metric,
                'evidence_type':basis,'evidence':'; '.join(evidence),
                'supported_week_start':weeks.min().date().isoformat(),
                'supported_week_end':(weeks.max()+pd.Timedelta(days=6)).date().isoformat(),
                'suggested_owner':owner,'next_step':action,'mode':c['mode'],'observed_at':now.isoformat()})
        b=base.loc[queue]
        for field,label,limit,unit in [('AHT_min','Queue handling time increase',c['aht_increase_fraction'],'relative'),
            ('offered_per_day','Arriving calls increase',c['volume_increase_fraction'],'relative'),
            ('abandonment','Callers leaving before help increase',c['abandonment_increase_pp'],'points')]:
            values=recent[field]/b[field]-1 if unit=='relative' else (recent[field]-b[field])*100
            check(label,recent,values,pd.Series(True,index=recent.index),values.ge(limit),priority='P1',
                  owner='Care Operations + Workforce + Learning',basis='Full daily population',
                  action='Check coverage and contact mix with Workforce; ask Product and Quality for issue evidence')
        qs=sample[sample.Queue.eq(queue)]
        for (product,reason),d in qs.groupby(['Product','Reason']):
            d=d[d.week.isin(weeks)].sort_values('week')
            values=d.mean_aht/d.baseline_aht-1
            check('Sample handling time increase',d,values,d.sample_n.ge(c['min_sample_per_week'])&d.baseline_n.ge(c['min_baseline_sample']),values.ge(c['aht_increase_fraction']),product,reason)
            if (product!='All') != (reason!='All'):
                values=(d['share']-d.baseline_share)*100
                # Baseline denominator is ALL sampled calls in the queue, not the rare segment.
                base_n=len(D['calls'][D['calls'].Queue.eq(queue)&D['calls']['Call date'].between(c['baseline_start'],c['baseline_end'])])
                check('Sample contact mix increase (percentage points)',d,values,d.sample_n.ge(c['min_sample_per_week'])&(base_n>=c['min_baseline_sample']),values.ge(c['segment_share_increase_pp']),product,reason,
                      action='Inspect product and reason tags; verify pattern with Product and Quality. Sample mix is not total demand')
            if product=='All' and reason=='All':
                values=d.generic_n/d.eligible_n.replace(0,np.nan)
                check('Eligible calls using generic troubleshooting',d,values,d.eligible_n.ge(c['min_sample_per_week']),values.ge(c['generic_troubleshooting_fraction']))
        for behavior,d in qa[qa.Queue.eq(queue)].groupby('Behavior'):
            d=d[d.week.isin(weeks)].sort_values('week')
            check('Selected QA gap: '+behavior,d,d.gap_rate,d.review_n.ge(c['min_qa_per_week']),d.gap_rate.ge(c['qa_gap_fraction']),basis='Selected QA reviews',
                  action='Calibrate reviewed examples; distinguish missing tools, unclear policy, system failures and practice needs')
        d=feedback[feedback.Queue.eq(queue)&feedback.week.isin(weeks)].sort_values('week')
        check('Low ratings among responding customers',d,d.low_rate,d.response_n.ge(c['min_feedback_per_week']),d.low_rate.ge(c['low_feedback_fraction']),basis='Voluntary selected responses',
              action='Read comments alongside QA; do not generalize response rates to all customers')
    columns=['issue_id','priority','queue','product','reason','signal','evidence_type','evidence','supported_week_start','supported_week_end','suggested_owner','next_step','mode','observed_at']
    return pd.DataFrame(rows,columns=columns).sort_values(['priority','queue','signal']),pd.DataFrame(evaluations,columns=['Queue','Product','Reason','Signal','Status','Latest evaluated week ending','Evidence type'])


LOG_FIELDS=['issue_id','mode','signal','queue','product','reason','first_detected_at','last_flagged_at',
 'first_supported_week_start','status','owner','notes','validated_onset_at','escalated_at','intervention_agreed_at']


def update_register(flags,log_path):
    p=Path(log_path)
    log=pd.read_csv(p,keep_default_na=False,dtype=str) if p.exists() else pd.DataFrame(columns=LOG_FIELDS)
    if set(LOG_FIELDS)-set(log):raise ValueError('Issue log is missing fields; restore its documented schema')
    if log.issue_id.duplicated().any():raise ValueError('Duplicate issue IDs in investigation log')
    for row in flags.to_dict('records'):
        mask=log.issue_id.eq(row['issue_id'])
        if mask.any():log.loc[mask,'last_flagged_at']=row['observed_at']
        else:
            new={k:'' for k in LOG_FIELDS}
            new.update({k:row[k] for k in ['issue_id','mode','signal','queue','product','reason']})
            new.update(first_detected_at=row['observed_at'],last_flagged_at=row['observed_at'],
                first_supported_week_start=row['supported_week_start'],status='Needs investigation',owner=row['suggested_owner'])
            log=pd.concat([log,pd.DataFrame([new])],ignore_index=True)
    active=log.merge(flags[['issue_id','priority','evidence_type','evidence','next_step']],how='left',on='issue_id',validate='one_to_one')
    active['Signal this run']=np.where(active.issue_id.isin(flags.issue_id),'Flagged','Not flagged / not enough current evidence')
    # Preserve human status. A flag disappearing does not prove resolution or close an issue.
    return log,active.sort_values(['priority','first_detected_at'],na_position='last')


def success_metrics(log):
    d=log[log['mode'].eq('pilot')].copy()
    for k in ['first_detected_at','validated_onset_at','escalated_at','intervention_agreed_at']:
        parsed=pd.to_datetime(d[k].replace('',pd.NA),utc=True,errors='coerce')
        if (d[k].ne('')&parsed.isna()).any():raise ValueError(f'Invalid {k} date in issue log')
        d[k]=parsed
    rows=[]
    for title,col in [('Days from validated onset to detection','validated_onset_at'),('Days from detection to agreed intervention','intervention_agreed_at')]:
        span=(d.first_detected_at-d[col] if col=='validated_onset_at' else d[col]-d.first_detected_at).dt.total_seconds()/86400
        valid=span.notna()&span.ge(0)
        rows.append({'Measure':title,'Result':f'{span[valid].median():.1f} median days' if valid.any() else 'Not measurable yet',
                     'Eligible issues':int(valid.sum()),'Invalid date order':int((span.notna()&span.lt(0)).sum())})
    eligible=d.first_detected_at.notna()&d.escalated_at.notna()
    n=int(eligible.sum())
    rows.append({'Measure':'Detected before recorded escalation','Result':f'{(d.loc[eligible,"first_detected_at"]<d.loc[eligible,"escalated_at"]).mean():.0%}' if n else 'Not measurable yet',
                 'Eligible issues':n,'Invalid date order':0})
    return pd.DataFrame(rows)


def guide_view(D,c):
    if not c['guide_view_approved']:return pd.DataFrame(columns=['Guide ID','Calls in sample','Weeks observed','Selected reviews','Sample average minutes'])
    calls=D['calls'][D['calls']['Call date'].between(c['baseline_start'],c['as_of'])]
    a=calls.groupby('Guide ID').agg(**{'Calls in sample':('Call ID','size'),'Weeks observed':('week','nunique'),'Sample average minutes':('AHT minutes','mean')})
    reviews=D['qa_joined'][D['qa_joined']['Call date'].between(c['baseline_start'],c['as_of'])].groupby('Guide ID')['Call ID'].nunique()
    a['Selected reviews']=reviews.reindex(a.index,fill_value=0)
    return a[a['Calls in sample'].ge(c['min_guide_calls'])&a['Weeks observed'].ge(c['min_guide_weeks'])&a['Selected reviews'].ge(c['min_guide_reviews'])].reset_index()


def interactive_html(sample,qa,feedback,op,flags,c):
    # Only aggregated values go into the browser; no Guide IDs, call IDs or free-text comments.
    views=sample.copy();views['Week']=views.week.dt.strftime('%Y-%m-%d')
    payload=views[['Queue','Product','Reason','Week','sample_n','mean_aht','share','eligible_n','complete_n']].to_json(orient='records')
    payload=payload.replace('<','\\u003c')
    flagtable=flags[['priority','queue','product','reason','signal','evidence_type','next_step']].rename(columns={'priority':'Priority','queue':'Queue','product':'Product','reason':'Issue type','signal':'Signal to review','evidence_type':'Evidence source','next_step':'First action'}).to_html(index=False,escape=True)
    extra={}
    for key,frame in [('operations',op),('qa',qa),('feedback',feedback)]:
        frame=frame.copy();frame['week']=frame.week.dt.strftime('%Y-%m-%d')
        extra[key]=json.loads(frame.to_json(orient='records'))
    context=json.dumps(extra).replace('<','\\u003c')
    return '''<!doctype html><html><head><meta charset="utf-8"><title>Learning early-warning dashboard</title>
<style>body{font:16px system-ui;max-width:1200px;margin:32px auto;padding:12px;color:#172b4d}select{padding:8px;margin:8px}th,td{text-align:left;padding:8px;border-bottom:1px solid #ddd}table{border-collapse:collapse;width:100%}.note{background:#eff6ff;padding:16px}svg{max-width:100%;height:auto}button{padding:8px}</style></head><body>
<h1>Learning early-warning pilot</h1><p class="note">Manual snapshot • report date '''+escape(c['as_of'])+''' • '''+escape(c['mode'])+'''. Flags prompt investigation, never a Guide rating. Changing a filter does not reload source data.</p>
<h2>Explore sampled calls</h2><p>Queue, product group and reason filters affect this sample view only. Counts are sampled calls, not total demand. Unknown means the code was missing. All means the combined group. Weeks may be partial; flags require complete weeks.</p>
<label>Queue <select id="q"></select></label><label>Product group <select id="p"></select></label><label>Reason <select id="r"></select></label>
<h2>Full queue context — queue filter only</h2><div id="operations"></div><h2>Quality and feedback — queue filter only</h2><div id="quality"></div><p>QA reviews and voluntary responses are selected unevenly. Rates below describe only assessed reviews or responding customers.</p><h3>Sample average handling time by week</h3><div id="chart"></div><div id="table"></div>
<h2>Investigation flags for this snapshot</h2><p>This backlog stays visible for all queues; filters above do not change the detection rules. No flag can mean insufficient evidence. Full operational and selected QA/feedback evidence appears above; the notebook and exported tables provide the full history.</p>'''+flagtable+'''
<script>
const data='''+payload+''';
const context='''+context+''';
const el=id=>document.getElementById(id);
function options(id,key){const select=el(id);for(const v of [...new Set(data.map(d=>d[key]))].sort()){const o=document.createElement('option');o.value=v;o.textContent=v;select.appendChild(o)}if(id!=='q')select.value='All';select.onchange=render}
function render(){const rows=data.filter(d=>d.Queue===el('q').value&&d.Product===el('p').value&&d.Reason===el('r').value).sort((a,b)=>a.Week.localeCompare(b.Week));
const wrap=el('table');wrap.replaceChildren();const table=document.createElement('table');const head=table.insertRow();['Week starting','Calls in sample','Average minutes','Share of queue sample','Eligible calls','Both recovery steps'].forEach(x=>{const t=document.createElement('th');t.textContent=x;head.appendChild(t)});
for(const d of rows){const r=table.insertRow();[d.Week,d.sample_n,d.mean_aht.toFixed(1),(d.share*100).toFixed(1)+'%',d.eligible_n,d.complete_n].forEach(x=>r.insertCell().textContent=x)}wrap.appendChild(table);
const chosenQueue=el('q').value;const weeks=context.operations.filter(d=>d.Queue===chosenQueue&&d.complete_week).sort((a,b)=>a.week.localeCompare(b.week));const current=weeks[weeks.length-1];
const operations=el('operations');operations.replaceChildren();const quality=el('quality');quality.replaceChildren();
if(current){const p=document.createElement('p');p.textContent='Latest complete week starting '+current.week+': '+current.AHT_min.toFixed(1)+' minutes per answered call; '+Math.round(current.offered_per_day).toLocaleString()+' arriving calls/day; '+(current.abandonment*100).toFixed(1)+'% left before help. Repeat contacts: not measurable from supplied data.';operations.appendChild(p);
const qt=document.createElement('table');for(const d of context.qa.filter(d=>d.Queue===chosenQueue&&d.week===current.week)){const r=qt.insertRow();[d.Behavior,d.gap_n+' gaps / '+d.review_n+' assessed reviews',d.gap_rate===null?'Not assessed':(100*d.gap_rate).toFixed(0)+'% gap'].forEach(v=>r.insertCell().textContent=v)}quality.appendChild(qt);const f=context.feedback.find(d=>d.Queue===chosenQueue&&d.week===current.week);const fp=document.createElement('p');fp.textContent=f?'Voluntary feedback: '+f.response_n+' responses; '+f.mean_score.toFixed(1)+'/5 average; '+(100*f.low_rate).toFixed(0)+'% rated 1 or 2.':'No feedback for this queue/week.';quality.appendChild(fp)}else{operations.textContent='No complete operating week available.';quality.textContent='No comparable complete-week view.'}
const ns='http://www.w3.org/2000/svg';const svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 1000 280');svg.setAttribute('role','img');svg.setAttribute('aria-label','Sample average handling time in minutes by week');
const max=Math.max(1,...rows.map(d=>d.mean_aht));const first=rows.length?Date.parse(rows[0].Week):0;const last=rows.length?Date.parse(rows[rows.length-1].Week):0;const width=900/Math.max(1,1+(last-first)/604800000);rows.forEach((d,i)=>{const position=60+(Date.parse(d.Week)-first)/604800000*width;const h=180*d.mean_aht/max;const rect=document.createElementNS(ns,'rect');rect.setAttribute('x',position);rect.setAttribute('y',210-h);rect.setAttribute('width',Math.max(1,width-3));rect.setAttribute('height',h);rect.setAttribute('fill','#246b8e');const title=document.createElementNS(ns,'title');title.textContent=d.Week+': '+d.mean_aht.toFixed(1)+' minutes; '+d.sample_n+' sampled calls';rect.appendChild(title);svg.appendChild(rect);if(i%Math.max(1,Math.ceil(rows.length/8))===0){const text=document.createElementNS(ns,'text');text.setAttribute('x',position);text.setAttribute('y',240);text.setAttribute('font-size',12);text.textContent=d.Week;svg.appendChild(text)}});
for(const [y,t] of [[210,'0'],[30,max.toFixed(1)+' min']]){const text=document.createElementNS(ns,'text');text.setAttribute('x',2);text.setAttribute('y',y);text.setAttribute('font-size',12);text.textContent=t;svg.appendChild(text)}el('chart').replaceChildren(svg);if(!rows.length)wrap.prepend('No sampled calls match these filters.');}
options('q','Queue');options('p','Product');options('r','Reason');render();
</script></body></html>'''


def atomic_text(path,text):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp');tmp.write_text(text);os.replace(tmp,path)


def run(c):
    D,coverage=prepare(c)
    op,base,sample,qa,feedback=build_metrics(D,c)
    flags,evaluations=detect(D,c,op,base,sample,qa,feedback)
    log,register=update_register(flags,c['issue_log'])
    success=success_metrics(log)
    guides=guide_view(D,c)
    stamp=pd.Timestamp.now(tz='UTC').strftime('%Y%m%dT%H%M%S%fZ')
    out=Path(c['output_folder'])/stamp;out.mkdir(parents=True)
    tables={'queue_weekly':op,'population_baseline':base.reset_index(),'sample_segments':sample,
            'qa_weekly':qa,'feedback_weekly':feedback,'investigation_flags':flags,'rule_evaluations':evaluations,
            'issue_register':register,'pilot_success':success,'source_coverage':coverage,'cleaning_audit':D['audit'],'guide_view':guides}
    for name,table in tables.items():table.to_csv(out/f'{name}.csv',index=False)
    digest=[f'# Weekly learning insight digest — {c["as_of"]}',f'\nMode: **{c["mode"]}**. Historical runs are retrospective examples, not evidence of early detection.',
      f'\n{len(flags)} sustained investigation flags; {c["consecutive_weeks"]} complete weeks required. Baseline: {c["baseline_start"]} to {c["baseline_end"]}.',
      '\n## What to investigate first']
    if flags.empty:digest+=['No rules triggered with sufficient sustained evidence. Check stale sources and insufficient-sample statuses; this is not an all-clear.']
    for r in flags.head(12).to_dict('records'):
        digest+=[f'- **{r["priority"]} · {r["queue"]} · {r["signal"]}** ({r["product"]} / {r["reason"]}; {r["evidence_type"]}). {r["next_step"]}. Evidence: {r["evidence"]}.']
    digest+=['\n## Interpretation and next action',
      'Sampled calls are not total demand. QA and feedback are nonrandom. Signals can reflect case mix, tagging, staffing, search or tool problems; investigate with Product and Care Quality before assigning learning.',
      'Repeat contacts are unavailable: no stable household/account identifier or complete contact history was supplied. Guide views are off unless explicitly approved and sufficiently supported; minimum counts do not eliminate selection bias.',
      f'Inspect all {len(evaluations)} rule evaluations and source coverage in the exported CSVs. Priority is a proposed investigation order, not a performance score.',
      '\n## Human follow-up',f'Update status, owner, notes and validated timing fields in `{c["issue_log"]}`. Do not overwrite existing issue IDs or auto timestamps. A disappearing flag does not close an investigation.']
    (out/'weekly_digest.md').write_text('\n'.join(digest))
    (out/'dashboard.html').write_text(interactive_html(sample,qa,feedback,op,flags,c))
    manifest={'completed_at_utc':stamp,'report_date':c['as_of'],'mode':c['mode'],'settings':c,
      'source_sha256':{f:hashlib.sha256((Path(c['input_folder'])/f).read_bytes()).hexdigest() for f in ['Orbit_operations.xlsx','Quality_and_feedback.xlsx']},
      'output_directory':str(out),'flags':len(flags)}
    (out/'run_manifest.json').write_text(json.dumps(manifest,indent=2))
    # Human fields are saved only after all computations and artifacts succeed.
    atomic_text(c['issue_log'],log.to_csv(index=False))
    atomic_text(Path(c['output_folder'])/'latest_run.json',json.dumps(manifest,indent=2))
    return {'data':D,'coverage':coverage,'op':op,'baseline':base,'sample':sample,'qa':qa,'feedback':feedback,
            'flags':flags,'evaluations':evaluations,'register':register,'success':success,'guides':guides,'out':out}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',default=str(ROOT/'learning_settings.json'))
    parser.add_argument('--as-of',help='Explicit reporting date YYYY-MM-DD; overrides config')
    args=parser.parse_args()
    cfg=read_settings(args.config)
    if args.as_of:cfg['as_of']=args.as_of
    result=run(cfg)
    print('Learning report complete:',result['out'])
