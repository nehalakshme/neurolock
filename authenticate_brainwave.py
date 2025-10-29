import tkinter as tk
from tkinter import filedialog, messagebox
import mysql.connector
import pandas as pd
import bcrypt
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# ------------------- Database Config -------------------
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '2006',   # change this
    'database': 'neurolock'
}

# ------------------- Database Fetch -------------------
def get_user_from_db(emp_id):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT emp_id, password_hash, brainwave FROM neuro_users WHERE emp_id = %s", (emp_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result

# ------------------- Authentication -------------------
def authenticate(emp_id, password, uploaded_csv_path):
    user_data = get_user_from_db(emp_id)
    if not user_data:
        return "User not found!"

    db_emp_id, db_hashed_pwd, db_brainwave = user_data

    # check password
    if not bcrypt.checkpw(password.encode('utf-8'), db_hashed_pwd.encode('utf-8')):
        return "Invalid password!"

    # brainwave check
    try:
        uploaded_df = pd.read_csv(uploaded_csv_path)
        uploaded_vector = uploaded_df.values.flatten()[:1000]  # limit length
        uploaded_vector = uploaded_vector.reshape(1, -1)

        stored_vector = np.frombuffer(db_brainwave, dtype=np.float64)
        stored_vector = stored_vector[:1000].reshape(1, -1)

        similarity = cosine_similarity(uploaded_vector, stored_vector)[0][0]

        if similarity > 0.9:
            return f"✅ Login Successful! Brainwave match: {similarity:.3f}"
        else:
            return f"❌ Brainwave mismatch! Similarity: {similarity:.3f}"

    except Exception as e:
        return f"Error processing EEG file: {e}"

# ------------------- GUI Setup -------------------
def open_file():
    file_path = filedialog.askopenfilename(title="Select EEG CSV", filetypes=[("CSV Files", "*.csv")])
    csv_path_var.set(file_path)

def login_action():
    emp_id = emp_id_var.get().strip()
    pwd = pwd_var.get().strip()
    csv_path = csv_path_var.get().strip()

    if not emp_id or not pwd or not csv_path:
        messagebox.showerror("Error", "Please fill all fields!")
        return

    result = authenticate(emp_id, pwd, csv_path)
    messagebox.showinfo("Result", result)

# ------------------- Main Window -------------------
root = tk.Tk()
root.title("NeuroLock - Brainwave Authentication")
root.geometry("400x300")

tk.Label(root, text="Employee ID:", font=('Arial', 12)).pack(pady=5)
emp_id_var = tk.StringVar()
tk.Entry(root, textvariable=emp_id_var, width=30).pack()

tk.Label(root, text="Password:", font=('Arial', 12)).pack(pady=5)
pwd_var = tk.StringVar()
tk.Entry(root, textvariable=pwd_var, show="*", width=30).pack()

tk.Label(root, text="EEG CSV File:", font=('Arial', 12)).pack(pady=5)
csv_path_var = tk.StringVar()
tk.Entry(root, textvariable=csv_path_var, width=30).pack()
tk.Button(root, text="Browse", command=open_file).pack(pady=3)

tk.Button(root, text="Login", command=login_action, bg="green", fg="white", width=15).pack(pady=20)

root.mainloop()
