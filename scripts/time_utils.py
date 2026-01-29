from datetime import datetime, timedelta
import sqlite3
import os

DB_PATH = os.path.join("data", "database.db")

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def get_all_periods():
    """Returns all periods that are less than 15 hours old."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # SQLite logic to filter by 15 hours
    cursor.execute("""
        SELECT id, subject, start_time, end_time, created_at 
        FROM periods 
        WHERE datetime(created_at) >= datetime('now', '-15 hours', 'localtime')
    """)
    periods = cursor.fetchall()
    conn.close()
    
    # Return formatted for the UI (excluding created_at unless needed)
    return [(p[0], p[1], p[2], p[3]) for p in periods]

def add_period(subject, start_time, end_time):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO periods (subject, start_time, end_time) VALUES (?, ?, ?)", (subject, start_time, end_time))
    conn.commit()
    conn.close()

def delete_period(pid):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM periods WHERE id = ?", (pid,))
    conn.commit()
    conn.close()

def get_current_active_period():
    """
    Returns (period_id, subject) if current time is within 
    period_start and period_start + 15 minutes.
    Only checks unexpired periods.
    """
    now = datetime.now()
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
    now = datetime.now()
    current_time = now.time()
    periods = get_all_periods()
    for pid, subject, start_str, end_str in periods:
        start_time = datetime.strptime(start_str, "%H:%M").time()
        end_time = datetime.strptime(end_str, "%H:%M").time()
        if start_time <= current_time <= end_time:
            return f"🔴 {subject} in progress - Entry Closed (15m elapsed)"
            
    return "⚪ No Active Period"
