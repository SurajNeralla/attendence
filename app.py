import streamlit as st
import cv2
import numpy as np
import os
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
from scripts.face_utils import add_user, get_user_name, detect_face, train_model, get_recognizer, get_student_info, delete_user_data
from scripts.time_utils import get_all_periods, add_period, delete_period, get_current_active_period, get_period_status

# Page configuration
st.set_page_config(page_title="GVP Attendance System", layout="wide")

# Header with Logo and Name
col1, col2 = st.columns([1, 5])
with col1:
    if os.path.exists("assets/logo.png"):
        st.image("assets/logo.png", width=120)
with col2:
    st.title("GAYATRI VIDHYA PARISHAD COLLEGE FOR DEGREE AND PG COURSES")
    st.subheader("Attendance Management System")

st.markdown("---")

# Ensure necessary directories exist
for folder in ["data/faces", "models"]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# Sidebar navigation
menu = ["Home", "Register User", "Mark Attendance", "View Records", "Admin: Schedule"]
choice = st.sidebar.selectbox("Navigation", menu)

if choice == "Home":
    st.subheader("Welcome to the AI Attendance System")
    st.write("This system uses OpenCV Haar Cascades for face detection and LBPH for recognition.")
    
    # Status display
    status = get_period_status()
    st.subheader("System Status")
    st.info(status)
    
    st.markdown("""
    ### How it works:
    1.  **Admin: Schedule**: Define subjects and times (e.g., Maths, 09:00 - 10:00).
    2.  **Register User**: Capture face samples for students.
    3.  **Mark Attendance**: Open the webcam during the **first 15 minutes** of a period to log attendance.
    """)

elif choice == "Admin: Schedule":
    st.subheader("🗓️ Period Management")
    
    with st.expander("➕ Add New Period"):
        subject = st.text_input("Subject Name")
        col1, col2 = st.columns(2)
        start_time = col1.time_input("Start Time", value=datetime.now().replace(minute=0))
        end_time = col2.time_input("End Time", value=(datetime.now() + timedelta(hours=1)).replace(minute=0))
        
        if st.button("Add Period"):
            if subject:
                add_period(subject, start_time.strftime("%H:%M"), end_time.strftime("%H:%M"))
                st.success(f"Added {subject}. This period will be valid for 15 hours.")
                st.rerun()
            else:
                st.error("Subject name is required")

    st.markdown("---")
    st.subheader("👥 Student Management")
    
    # Get all students for management
    conn = sqlite3.connect("data/database.db")
    df_students = pd.read_sql_query("SELECT id, name, roll_no, year, section FROM users", conn)
    conn.close()
    
    if not df_students.empty:
        st.dataframe(df_students, use_container_width=True)
        
        user_to_del = st.number_input("Enter Student ID to delete", min_value=1, step=1)
        if st.button("🗑️ Delete Student"):
            with st.spinner("Deleting student and retraining model..."):
                if delete_user_data(user_to_del):
                    st.success(f"Student {user_to_del} deleted and model updated!")
                    st.rerun()
                else:
                    st.error("Error during deletion or retraining.")
    else:
        st.info("No students registered yet.")

    st.markdown("---")
    st.subheader("Current Schedule")
    periods = get_all_periods()
    if periods:
        df_periods = pd.DataFrame(periods, columns=["ID", "Subject", "Start", "End"])
        st.table(df_periods)
        
        del_id = st.number_input("Enter Period ID to delete", min_value=1, step=1)
        if st.button("Delete Period"):
            delete_period(del_id)
            st.success(f"Deleted Period {del_id}")
            st.rerun()
    else:
        st.info("No periods scheduled yet.")

elif choice == "Register User":
    st.subheader("👤 Register New User")
    name = st.text_input("Enter Full Name")
    roll_no = st.text_input("Enter Roll Number")
    col1, col2 = st.columns(2)
    year = col1.selectbox("Year", [1, 2, 3])
    section = col2.selectbox("Section", ["A", "B", "C", "D"])
    img_file = st.camera_input("Capture Face")

    if img_file and name and roll_no:
        if st.button("Register & Train"):
            file_bytes = np.asarray(bytearray(img_file.read()), dtype=np.uint8)
            frame = cv2.imdecode(file_bytes, 1)
            face_gray, _ = detect_face(frame)
            
            if face_gray is not None:
                try:
                    user_id = add_user(name, roll_no, year, section)
                    user_folder = os.path.join("data", "faces", str(user_id))
                    os.makedirs(user_folder, exist_ok=True)
                    cv2.imwrite(os.path.join(user_folder, "1.jpg"), face_gray)
                    
                    with st.spinner("Training model..."):
                        if train_model():
                            st.success(f"User {name} registered and model trained!")
                        else:
                            st.error("Error during training.")
                except sqlite3.IntegrityError:
                    st.error("Roll Number already exists!")
            else:
                st.error("No face detected. Please ensure your face is clearly visible.")

elif choice == "Mark Attendance":
    st.subheader("📹 Real-time Attendance")
    
    status = get_period_status()
    st.markdown(f"Status: **{status}**")
    
    pid, subject, times = get_current_active_period()
    
    if not pid:
        st.warning("Entry is closed. Attendance can only be marked within the first 15 minutes of a scheduled period.")
    else:
        recognizer = get_recognizer()
        if recognizer is None:
            st.error("Model not found. Please register users first.")
        else:
            run = st.checkbox('Start Webcam')
            FRAME_WINDOW = st.image([])
            camera = cv2.VideoCapture(0)
            
            while run:
                ret, frame = camera.read()
                if not ret: break
                
                face_gray, bbox = detect_face(frame)
                if face_gray is not None:
                    (x, y, w, h) = bbox
                    id_, confidence = recognizer.predict(face_gray)
                    name = "Unknown"
                    
                    if confidence < 80:
                        info = get_student_info(id_)
                        if info:
                            name = info["name"]
                            roll_no = info["roll_no"]
                            year = info["year"]
                            section = info["section"]
                            
                            date_str = datetime.now().strftime("%Y-%m-%d")
                            time_str = datetime.now().strftime("%H:%M:%S")
                            log_file = os.path.join("data", f"attendance_{date_str}.csv")
                            
                            cols = ["Roll_No", "Name", "Year", "Section", "Time", "Subject", "Period_ID"]
                            if not os.path.exists(log_file):
                                pd.DataFrame(columns=cols).to_csv(log_file, index=False)
                            
                            df = pd.read_csv(log_file)
                            
                            # Robust check: if file exists but lacks columns, reset it
                            if 'Roll_No' not in df.columns:
                                df = pd.DataFrame(columns=cols)
                                df.to_csv(log_file, index=False)

                            # Robust type-safe comparison
                            already_marked = False
                            if not df.empty:
                                df['Roll_No'] = df['Roll_No'].astype(str)
                                df['Period_ID'] = df['Period_ID'].astype(int)
                                already_marked = ((df['Roll_No'] == str(roll_no)) & (df['Period_ID'] == int(pid))).any()

                            if not already_marked:
                                new_entry = pd.DataFrame([[roll_no, name, year, section, time_str, subject, pid]], 
                                                         columns=cols)
                                df = pd.concat([df, new_entry], ignore_index=True)
                                df.to_csv(log_file, index=False)
                                st.toast(f"✅ Attendance marked for {name} ({subject})")
                                # Optional: Add a delay or sound here if needed
                    else:
                        name = "Unknown"
                    
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    cv2.putText(frame, f"{name}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

                FRAME_WINDOW.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            else:
                camera.release()

elif choice == "View Records":
    st.subheader("📊 Attendance History")
    log_files = [f for f in os.listdir("data") if f.startswith("attendance_") and f.endswith(".csv")]
    if not log_files:
        st.info("No attendance records found.")
    else:
        selected_file = st.selectbox("Select Date", log_files)
        df = pd.read_csv(os.path.join("data", selected_file))
        
        st.markdown("### Filters")
        f_col1, f_col2 = st.columns(2)
        year_filter = f_col1.multiselect("Filter by Year", options=[1, 2, 3], default=[1, 2, 3])
        section_filter = f_col2.multiselect("Filter by Section", options=["A", "B", "C", "D"], default=["A", "B", "C", "D"])
        
        # Robust filtering: check if columns exist
        filtered_df = df
        if 'Year' in df.columns and 'Section' in df.columns:
            filtered_df = df[df['Year'].isin(year_filter) & df['Section'].isin(section_filter)]
        else:
            st.warning("This record file uses an older format and cannot be filtered by Year or Section.")
        
        st.dataframe(filtered_df, use_container_width=True)
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", csv, selected_file, "text/csv")

        st.markdown("---")
        st.subheader("📋 Detailed Cohort Report (P/A Status)")
        st.write("Generate a full attendance sheet for a specific section and roll range.")
        
        c_col1, c_col2 = st.columns(2)
        rpt_year = c_col1.selectbox("Target Year", [1, 2, 3], key="rpt_yr")
        rpt_sec = c_col2.selectbox("Target Section", ["A", "B", "C", "D"], key="rpt_sec")
        
        # Predefined ranges based on user input
        default_start = "5241411001"
        default_end = "5241411059"
        
        if rpt_year == 2 and rpt_sec == "B":
            default_start = "5241411062"
            default_end = "5241411123"
        elif rpt_year == 2 and rpt_sec == "A":
            default_start = "5241411001"
            default_end = "5241411059"
        else:
            default_start = ""
            default_end = ""

        r_col1, r_col2 = st.columns(2)
        roll_start = r_col1.text_input("Roll No Start", value=default_start)
        roll_end = r_col2.text_input("Roll No End", value=default_end)
        
        # Get active periods for the selected date to filter by
        active_pids = df['Period_ID'].unique().tolist() if 'Period_ID' in df.columns else []
        selected_pid = st.selectbox("Select Period ID for Report", options=active_pids)
        
        if st.button("Generate P/A Report"):
            # 1. Parse roll range as integers if possible
            try:
                start_r = int(roll_start)
                end_r = int(roll_end)
                full_range = [str(r) for r in range(start_r, end_r + 1)]
            except ValueError:
                st.error("Roll Number range must be numeric for automatic sequence generation.")
                st.stop()

            # 2. Fetch all registered students in this cohort to get names
            conn = sqlite3.connect("data/database.db")
            query = "SELECT roll_no, name FROM users WHERE year = ? AND section = ?"
            db_students = pd.read_sql_query(query, conn, params=(rpt_year, rpt_sec))
            conn.close()
            
            # Create a mapping for quick name lookup
            name_map = dict(zip(db_students['roll_no'].astype(str), db_students['name']))
            
            # 3. Get present students from the CSV for the selected period
            present_roll_nos = []
            if not df.empty and 'Period_ID' in df.columns and 'Roll_No' in df.columns:
                present_roll_nos = df[df['Period_ID'] == selected_pid]['Roll_No'].astype(str).tolist()
            
            # 4. Construct the full report
            report_data = []
            for r_no in full_range:
                status = 'P' if r_no in present_roll_nos else 'A'
                name = name_map.get(r_no, "Not Registered")
                report_data.append([r_no, name, status])
            
            report_df = pd.DataFrame(report_data, columns=["Roll_No", "Name", "Status"])
            
            st.write(f"**Full Class Report for Period {selected_pid} | {rpt_year} Year Section {rpt_sec}**")
            st.write(f"Showing range {roll_start} to {roll_end}")
            
            # Summary metrics
            p_count = (report_df['Status'] == 'P').sum()
            a_count = (report_df['Status'] == 'A').sum()
            st.info(f"Summary: {p_count} Present, {a_count} Absent")
            
            st.dataframe(report_df, use_container_width=True)
            
            report_csv = report_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Download P/A Report", 
                report_csv, 
                f"Full_Report_{rpt_year}{rpt_sec}_P{selected_pid}.csv", 
                "text/csv"
            )
