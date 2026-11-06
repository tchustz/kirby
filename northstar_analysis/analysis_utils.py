"""Shared, auditable cleaning and metrics for the Northstar case notebooks."""
from pathlib import Path
import hashlib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'data' / 'raw'
OUT = ROOT / 'outputs'
CASE_AS_OF = pd.Timestamp('2026-10-02')

def load_data(raw=RAW, as_of=CASE_AS_OF, call_through='2026-09-30'):
    as_of, call_through = pd.Timestamp(as_of), pd.Timestamp(call_through)
    specs = {
        'daily': ('Orbit_operations.xlsx', 'Daily operations', 'Date'),
        'calls': ('Orbit_operations.xlsx', 'Call sample', 'Call ID'),
        'staff': ('Orbit_operations.xlsx', 'Staffing', 'Date'),
        'catalog': ('Orbit_operations.xlsx', 'Product catalog', 'Product code'),
        'qa': ('Quality_and_feedback.xlsx', 'QA reviews', 'QA review ID'),
        'feedback': ('Quality_and_feedback.xlsx', 'Customer feedback', 'Feedback ID'),
    }
    data, audit = {}, []
    for name, (file, sheet, key) in specs.items():
        # Find the real table header; do not mistake the title/notes for field names.
        frame = pd.read_excel(raw / file, sheet_name=sheet, header=None)
        matches = frame.index[frame.eq(key).any(axis=1)].tolist()
        if len(matches) != 1:
            raise ValueError(f'{sheet}: expected one header containing {key}, found {matches}')
        i = matches[0]
        frame.columns = frame.iloc[i].astype(str).str.strip()
        frame = frame.iloc[i+1:].dropna(how='all').reset_index(drop=True)
        frame.columns.name = None
        for col in frame.select_dtypes(include='object'):
            frame[col] = frame[col].map(lambda x: x.strip() if isinstance(x, str) else x)
            frame[col] = frame[col].replace('', pd.NA)
        for col in frame:
            if col == 'Date' or col.endswith('date'):
                frame[col] = pd.to_datetime(frame[col], errors='raise')
        audit.append({'table':name,'raw_rows':len(frame),'header_excel_row':i+1,
                      'missing_key':int(frame[key].isna().sum())})
        if frame[key].isna().any():
            raise ValueError(f'{sheet}: null key')
        data[name] = frame
    calls = data['calls']
    dup = calls[calls.duplicated('Call ID', keep=False)]
    substantive = [c for c in calls if c not in ['Sample row','Sample status']]
    if not dup.empty and dup.groupby('Call ID')[substantive].nunique(dropna=False).gt(1).any().any():
        raise ValueError('Conflicting duplicate call records require review')
    if calls.loc[calls.duplicated('Call ID'), 'Sample status'].ne('Duplicate export row').any():
        raise ValueError('Unexpected unlabeled duplicate call')
    data['duplicate_rows'] = calls[calls.duplicated('Call ID')].copy()
    calls = calls.drop_duplicates('Call ID',keep='first').copy()
    data['calls'] = calls
    for name, keys in [('daily',['Date','Queue']),('staff',['Date','Queue']),
                       ('catalog',['Product code']),('qa',['QA review ID']),('feedback',['Feedback ID'])]:
        if data[name].duplicated(keys).any(): raise ValueError(f'{name}: duplicate keys')
    for name in ['daily','staff']:
        for col in data[name]:
            if col not in ['Date','Queue','Population status','Coverage note']:
                data[name][col] = pd.to_numeric(data[name][col],errors='raise')
    for col in ['Talk minutes','Hold minutes','Wrap minutes','AHT minutes']:
        calls[col] = pd.to_numeric(calls[col],errors='raise')
        if (calls[col] < 0).any(): raise ValueError('Negative call duration')
    if not np.allclose(calls['AHT minutes'],calls[['Talk minutes','Hold minutes','Wrap minutes']].sum(axis=1),atol=.151):
        raise ValueError('AHT component mismatch')
    d = data['daily']
    if not d['Offered contacts'].eq(d['Answered contacts']+d['Abandoned contacts']).all():
        raise ValueError('Offered/answered/abandoned mismatch')
    if (d['Answered contacts'] <= 0).any() or (d['Offered contacts'] <= 0).any():
        raise ValueError('Invalid operations denominators')
    if not np.allclose(d['Abandonment rate'],d['Abandoned contacts']/d['Offered contacts'],atol=.00001):
        raise ValueError('Source abandonment-rate mismatch')
    if not np.allclose(d['Average handle minutes'],d[['Average talk minutes','Average hold minutes','Average wrap minutes']].sum(axis=1),atol=.11):
        raise ValueError('Daily AHT components mismatch')
    data['ops'] = d.merge(data['staff'],on=['Date','Queue'],how='outer',validate='one_to_one',indicator=True)
    if not data['ops']['_merge'].eq('both').all(): raise ValueError('Unmatched staffing day')
    data['ops'] = data['ops'].drop(columns='_merge')
    calls['WN7 code'] = calls['Product code'].isin(['WN7','WNM-7'])
    calls['Product segment'] = np.select([calls['Product code'].isna(),calls['WN7 code']],['Unknown','WN7-containing'],default='Other products')
    calls['Complete recovery'] = calls['Replacement arranged'].eq('Yes') & calls['Northstar Plus attached'].eq('Yes')
    calls['Recovery available'] = ((calls['Queue'].eq('Specialist Care') & calls['Call date'].ge('2026-09-12')) |
                                  (calls['Queue'].eq('General Care') & calls['Call date'].ge('2026-09-21')))
    calls['Phase'] = np.select([calls['Call date'].lt('2026-09-10'),calls['Call date'].lt('2026-09-12'),calls['Call date'].lt('2026-09-21')],
                              ['Before approval','Approved; before pilot','Specialist pilot only'],default='General article available')
    for name in ['qa','feedback']:
        data[name+'_joined'] = data[name].merge(calls,on='Call ID',how='left',validate='many_to_one',suffixes=('_review',''),indicator=True)
        if not data[name+'_joined']['_merge'].eq('both').all(): raise ValueError(f'Unmatched {name} calls')
        data[name+'_joined'] = data[name+'_joined'].drop(columns='_merge')
        for col in ['Call date','Queue']:
            if not data[name+'_joined'][col].eq(data[name+'_joined'][col+'_review']).all():
                raise ValueError(f'{name}: inconsistent {col}')
    known_codes = set(calls['Product code'].dropna())
    calls['Catalog matched'] = calls['Product code'].isin(data['catalog']['Product code'])
    data['catalog_unmatched'] = calls.loc[calls['Product code'].notna() & ~calls['Catalog matched'], 'Product code'].value_counts().rename_axis('Product code').reset_index(name='sample_calls')
    if calls['Call date'].max() > call_through: raise ValueError('Unexpected future call')
    if data['qa']['Review date'].max() > as_of or data['feedback']['Response date'].max() > as_of:
        raise ValueError('Future QA or response relative to case as-of')
    for a in audit:
        a['clean_rows'] = len(data[a['table']]); a['removed_rows'] = a['raw_rows']-a['clean_rows']
    data['audit'] = pd.DataFrame(audit)
    return data

def population_metrics(frame):
    answered = frame['Answered contacts'].sum()
    offered = frame['Offered contacts'].sum()
    weights = frame['Answered contacts']
    return pd.Series({
        'days':frame['Date'].nunique(),'offered':offered,'answered':answered,
        'offered_per_day':offered/frame['Date'].nunique(),
        'AHT_min':np.average(frame['Average handle minutes'],weights=weights),
        # Offered weighting is a proxy: no underlying wait numerator is supplied.
        'wait_min_proxy':np.average(frame['Average wait minutes'],weights=frame['Offered contacts']),
        'abandonment':frame['Abandoned contacts'].sum()/offered,
        'WN7_contact_share':frame[['WN7-related calls','WNM-7-related calls']].sum().sum()/answered,
        'actual_planned':frame['Actual Guides'].sum()/frame['Planned Guides'].sum(),
        'occupancy_proxy':np.average(frame['Occupancy'],weights=frame['Scheduled hours']),
    })

def recovery_metrics(frame):
    e = frame[frame['Eligible for recovery'].eq('Yes')]
    return pd.Series({'eligible_n':len(e),'serial_n':e['Serial verified'].eq('Yes').sum(),
        'replacement_n':e['Replacement arranged'].eq('Yes').sum(),
        'plus_n':e['Northstar Plus attached'].eq('Yes').sum(),
        'complete_n':e['Complete recovery'].sum(),
        'complete_rate':e['Complete recovery'].mean() if len(e) else np.nan,
        'incomplete_n':(~e['Complete recovery']).sum()})

def export_clean(data):
    OUT.mkdir(exist_ok=True)
    for name in ['daily','staff','calls','qa','feedback','audit','duplicate_rows','catalog_unmatched']:
        data[name].to_csv(OUT / f'{name}_clean.csv',index=False)
    manifest = [{'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(RAW.iterdir()) if p.is_file()]
    pd.DataFrame(manifest).to_csv(OUT/'source_manifest.csv',index=False)
