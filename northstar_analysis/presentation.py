"""Plain-language presentation helpers; calculations live in analysis_utils.py."""
from html import escape
import pandas as pd
from IPython.display import display, HTML
from matplotlib.ticker import PercentFormatter, StrMethodFormatter


def table(frame, title, note=''):
    display(HTML('<h3>'+escape(title)+'</h3>'+frame.to_html(index=False, border=0, escape=True)+
                 '<p style="color:#475569">'+escape(note)+'</p>'))


def cards(items):
    parts=[]
    for title, value, note in items:
        parts.append('<div style="border:1px solid #cbd5e1;border-left:5px solid #246b8e;padding:16px;margin:8px;flex:1;min-width:190px">'
                     '<div>'+escape(title)+'</div><div style="font-size:28px;font-weight:bold">'+escape(value)+'</div>'
                     '<div>'+escape(note)+'</div></div>')
    display(HTML('<div style="display:flex;flex-wrap:wrap">'+''.join(parts)+'</div>'))


def comparison(a,b):
    rows=[]
    for key,label,fmt in [
        ('offered_per_day','Calls arriving each day',',.0f'),
        ('AHT_min','Average time spent handling an answered call','.2f'),
        ('abandonment','Callers who hung up before reaching a Guide','.1%'),
        ('WN7_contact_share','Answered calls tagged WN7 or WNM-7','.1%'),
        ('actual_planned','Staff present compared with planned staffing','.1%')]:
        unit=' minutes' if key=='AHT_min' else ''
        change=(f'{100*(b[key]-a[key]):+.1f} percentage points' if '%' in fmt else
                f'{b[key]-a[key]:+,.2f} minutes' if key=='AHT_min' else f'{b[key]-a[key]:+,.0f} calls/day')
        rows.append({'What we measured':label,'Earlier period':format(a[key],fmt)+unit,
                     'Later period':format(b[key],fmt)+unit,'Change':change})
    return pd.DataFrame(rows)
