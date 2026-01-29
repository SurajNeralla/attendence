import cv2
import numpy as np
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join("data", "database.db")
TRAINER_PATH = os.path.join("models", "trainer.yml")

# Initialize OpenCV Haar Cascade for face detection
# Using the default frontal face cascade
face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
face_cascade = cv2.CascadeClassifier(face_cascade_path)

from scripts.supabase_utils import db_add_user, db_get_student_info, db_get_all_students, db_delete_user, db_get_student_info_by_id

def add_user(name, roll_no, year, section):
    """Registers user in Supabase and returns the assigned ID."""
    user_id = db_add_user(name, roll_no, year, section)
    return user_id

def get_student_info(user_id):
    """Retrieves student info from Supabase by user ID (integer)."""
    return db_get_student_info_by_id(user_id)

def get_student_info_by_roll(roll_no):
    """Retrieves student info from Supabase by roll number."""
    return db_get_student_info(roll_no)

def get_user_name(user_id):
    info = get_student_info(user_id)
    return info["name"] if info else "Unknown"

def detect_face(image):
    """Detects face using Haar Cascades and returns crop in grayscale."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5, minSize=(30, 30))
    
    if len(faces) == 0:
        return None, None
    
    # Get the first detection (x, y, w, h)
    (x, y, w, h) = faces[0]
    face_crop = gray[y:y+h, x:x+w]
    
    return face_crop, (x, y, w, h)

import shutil

def delete_user_data(user_id):
    """Deletes user from Supabase, removes face samples, and retrains the model."""
    # 1. Delete from Supabase
    if db_delete_user(user_id):
        # 2. Delete face samples folder
        user_folder = os.path.join("data", "faces", str(user_id))
        if os.path.exists(user_folder):
            try:
                shutil.rmtree(user_folder)
            except PermissionError:
                import time
                time.sleep(0.5)
                try:
                    shutil.rmtree(user_folder)
                except Exception as e:
                    print(f"Warning: Could not delete folder {user_folder}: {e}")
        
        # 3. Retrain model
        return train_model()
    return False

def train_model():
    """Trains LBPH recognizer based on images in data/faces."""
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    faces_dir = os.path.join("data", "faces")
    
    if not os.path.exists(faces_dir):
        return False
        
    face_samples = []
    ids = []
    
    for user_id_folder in os.listdir(faces_dir):
        user_path = os.path.join(faces_dir, user_id_folder)
        if not os.path.isdir(user_path):
            continue
            
        user_id = int(user_id_folder)
        for img_name in os.listdir(user_path):
            img_path = os.path.join(user_path, img_name)
            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            if img is not None:
                face_samples.append(img)
                ids.append(user_id)
            
    if not face_samples:
        return False
        
    recognizer.train(face_samples, np.array(ids))
    if not os.path.exists("models"):
        os.makedirs("models")
    recognizer.save(TRAINER_PATH)
    return True

def get_recognizer():
    if not os.path.exists(TRAINER_PATH):
        return None
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(TRAINER_PATH)
    return recognizer
