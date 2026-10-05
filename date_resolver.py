"""Resolve structured model date requests with deterministic calendar arithmetic."""
import calendar
from datetime import date,datetime,timedelta,timezone

def today_pakistan():
    return datetime.now(timezone(timedelta(hours=5))).date()

def resolve_date_spec(spec,reference,data_start,data_end):
    if not spec or spec.get('kind')=='none':return None
    kind=spec.get('kind')
    if kind=='all':start,end=date.fromisoformat(data_start),date.fromisoformat(data_end)
    elif kind=='date':start=end=date.fromisoformat(spec['date'])
    elif kind=='range':start,end=date.fromisoformat(spec['start']),date.fromisoformat(spec['end'])
    elif kind=='relative_day':
        offset=spec['offset']
        if type(offset)!=int or abs(offset)>3660:raise ValueError('Invalid day offset.')
        start=end=reference+timedelta(days=offset)
    elif kind=='weekday':
        weekday=spec['weekday'];occurrence=spec.get('occurrence',1);direction=spec['direction']
        if type(weekday)!=int or not 0<=weekday<=6 or type(occurrence)!=int or not 1<=occurrence<=52:raise ValueError('Invalid weekday request.')
        # Last/next are strictly before/after reference date, even if today matches.
        if direction=='previous':
            distance=(reference.weekday()-weekday)%7 or 7
            start=end=reference-timedelta(days=distance+7*(occurrence-1))
        elif direction=='next':
            distance=(weekday-reference.weekday())%7 or 7
            start=end=reference+timedelta(days=distance+7*(occurrence-1))
        else:raise ValueError('Unknown weekday direction.')
    elif kind=='year':
        year=spec['year'];start,end=date(year,1,1),date(year,12,31)
    elif kind=='month':
        year,month=spec['year'],spec['month'];start=date(year,month,1);end=date(year,month,calendar.monthrange(year,month)[1])
    else:raise ValueError('Unsupported date request; ask for an explicit date range.')
    if end<start:raise ValueError('End date is before start date.')
    return {'start':start.isoformat(),'end':end.isoformat(),'reference':reference.isoformat()}
