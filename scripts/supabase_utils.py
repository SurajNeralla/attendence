import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    supabase = None
else:
    supabase: Client = create_client(url, key)

def get_supabase_client():
    return supabase

# User Operations
def db_add_user(name, roll_no, year, section):
    if not supabase: return None
    data = {
        "name": name,
        "roll_no": roll_no,
        "year": year,
        "section": section
    }
    response = supabase.table("users").insert(data).execute()
    return response.data[0]["id"] if response.data else None

def db_get_student_info(roll_no):
    if not supabase: return None
    response = supabase.table("users").select("*").eq("roll_no", roll_no).execute()
    return response.data[0] if response.data else None

def db_get_student_info_by_id(user_id):
    if not supabase: return None
    response = supabase.table("users").select("*").eq("id", user_id).execute()
    return response.data[0] if response.data else None

def db_get_all_students():
    if not supabase: return []
    response = supabase.table("users").select("*").execute()
    return response.data if response.data else []

def db_delete_user(user_id):
    if not supabase: return False
    supabase.table("users").delete().eq("id", user_id).execute()
    return True

# Period Operations
def db_add_period(subject, start_time, end_time):
    if not supabase: return None
    data = {
        "subject": subject,
        "start_time": start_time,
        "end_time": end_time
    }
    response = supabase.table("periods").insert(data).execute()
    return response.data[0]["id"] if response.data else None

def db_get_active_periods():
    if not supabase: return []
    # Fetch periods from the last 15 hours
    # Calculate the timestamp manually in Python for better compatibility
    from datetime import datetime, timedelta
    expiry_limit = (datetime.now() - timedelta(hours=15)).isoformat()
    
    response = supabase.table("periods").select("*").gte("created_at", expiry_limit).execute()
    return response.data if response.data else []

def db_delete_period(period_id):
    if not supabase: return False
    supabase.table("periods").delete().eq("id", period_id).execute()
    return True

# Attendance Operations
def db_mark_attendance(roll_no, name, year, section, subject, period_id):
    if not supabase: return False
    # Check if already marked for this period
    existing = supabase.table("attendance").select("*").eq("roll_no", roll_no).eq("period_id", period_id).execute()
    if existing.data:
        return False # Already marked
        
    data = {
        "roll_no": roll_no,
        "name": name,
        "year": year,
        "section": section,
        "subject": subject,
        "period_id": period_id
    }
    supabase.table("attendance").insert(data).execute()
    return True

def db_get_attendance_by_date(date_str):
    if not supabase: return []
    # date_str expected as YYYY-MM-DD
    response = supabase.table("attendance").select("*").gte("marked_at", f"{date_str} 00:00:00").lte("marked_at", f"{date_str} 23:59:59").execute()
    return response.data if response.data else []
