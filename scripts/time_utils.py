from datetime import datetime, timedelta
from scripts.supabase_utils import db_get_active_periods, db_add_period, db_delete_period, get_now_ist

def get_all_periods():
    """Returns all periods that are less than 15 hours old from Supabase."""
    periods = db_get_active_periods()
    # Return formatted for the UI
    return [(p["id"], p["subject"], p["start_time"], p["end_time"]) for p in periods]

def add_period(subject, start_time, end_time):
    """Adds a new period to Supabase."""
    return db_add_period(subject, start_time, end_time)

def delete_period(pid):
    """Deletes a period from Supabase."""
    return db_delete_period(pid)

def get_current_active_period():
    """
    Returns (period_id, subject) if current time is within 
    period_start and period_start + 15 minutes.
    Only checks unexpired periods.
    """
    now = get_now_ist()
    current_time = now.time()
    periods = get_all_periods()
    
    for pid, subject, start_str, end_str in periods:
        start_time_dt = datetime.strptime(start_str, "%H:%M")
        start_time = start_time_dt.time()
        
        # Strict 15-minute rule: only valid between Start and Start + 15m
        valid_start_dt = datetime.combine(now.date(), start_time)
        valid_end_dt = valid_start_dt + timedelta(minutes=15)
        
        if valid_start_dt.time() <= current_time <= valid_end_dt.time():
            return pid, subject, f"{start_str} - {end_str}"
            
    return None, None, None

def get_period_status():
    """Returns a string describing the current system status."""
    pid, subject, times = get_current_active_period()
    if pid:
        return f"🟢 Active: {subject} ({times}) - Attendance Open"
    
    # Check if we are in a period but after the 15m mark
    now = get_now_ist()
    current_time = now.time()
    periods = get_all_periods()
    for pid, subject, start_str, end_str in periods:
        start_time = datetime.strptime(start_str, "%H:%M").time()
        end_time = datetime.strptime(end_str, "%H:%M").time()
        if start_time <= current_time <= end_time:
            return f"🔴 {subject} in progress - Entry Closed (15m elapsed)"
            
    return "⚪ No Active Period"
