import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import numpy as np
import mysql.connector
import bcrypt

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "2006",
    "database": "neurolock"
}

# ---------- Database setup ----------
def create_table_if_not_exists():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS neuro_users (
            emp_id VARCHAR(20) PRIMARY KEY,
            name VARCHAR(100),
            password_hash VARCHAR(255),
            brainwave LONGBLOB
        );
    """)
    conn.commit()
    cursor.close()
    conn.close()

# ---------- Save new user ----------
def register_user(emp_id, name, password, csv_path):
    try:
        df = pd.read_csv(csv_path)
        flat_array = df.values.flatten().astype(np.float64)
        brainwave_binary = flat_array.tobytes()
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO neuro_users (emp_id, name, password_hash, brainwave)
            VALUES (%s, %s, %s, %s)
        """, (emp_id, name, password_hash, brainwave_binary))
        conn.commit()
        cursor.close()
        conn.close()
        messagebox.showinfo("Success", f"User {name} registered successfully!")
    except Exception as e:
        messagebox.showerror("Error", f"Registration failed:\n{e}")

# ---------- Authenticate user ----------
def authenticate_user(emp_id, password, csv_path):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash, brainwave FROM neuro_users WHERE emp_id = %s", (emp_id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if not result:
            messagebox.showerror("Login Failed", "Employee ID not found.")
            return

        db_password_hash, db_brainwave = result
        if not bcrypt.checkpw(password.encode('utf-8'), db_password_hash.encode('utf-8')):
            messagebox.showerror("Login Failed", "Incorrect password.")
            return

        df = pd.read_csv(csv_path)
        test_array = df.values.flatten().astype(np.float64)
        stored_array = np.frombuffer(db_brainwave, dtype=np.float64)

        min_len = min(len(test_array), len(stored_array))
        corr = np.corrcoef(test_array[:min_len], stored_array[:min_len])[0, 1]

        if corr > 0.85:
            messagebox.showinfo("Access Granted", f"Welcome, {emp_id}! Brainwave matched ({corr:.2f})")
        else:
            messagebox.showerror("Access Denied", f"Brainwave mismatch ({corr:.2f})")

    except Exception as e:
        messagebox.showerror("Error", f"Authentication failed:\n{e}")

# ---------- UI Helper ----------
def open_file_dialog(entry_widget):
    file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
    if file_path:
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, file_path)

# ---------- Styling ----------
def style_widget(widget):
    widget.configure(bg="#0b0c10", fg="#66fcf1", insertbackground="#66fcf1", relief="flat")
    widget.config(font=("Poppins", 10))
    return widget

def create_button(parent, text, command=None):
    btn = tk.Button(
        parent, text=text, command=command,
        bg="#1f2833", fg="#66fcf1",
        activebackground="#45a29e", activeforeground="white",
        relief="flat", font=("Poppins", 10, "bold"), width=20
    )
    return btn

# ---------- Register window ----------
def register_screen():
    win = tk.Toplevel(root)
    win.title("Register User")
    win.configure(bg="#0b0c10")
    win.geometry("400x350")

    tk.Label(win, text="Employee ID", bg="#0b0c10", fg="#66fcf1", font=("Poppins", 10)).pack(pady=5)
    emp_entry = style_widget(tk.Entry(win))
    emp_entry.pack(pady=3)

    tk.Label(win, text="Name", bg="#0b0c10", fg="#66fcf1", font=("Poppins", 10)).pack(pady=5)
    name_entry = style_widget(tk.Entry(win))
    name_entry.pack(pady=3)

    tk.Label(win, text="Password", bg="#0b0c10", fg="#66fcf1", font=("Poppins", 10)).pack(pady=5)
    pwd_entry = style_widget(tk.Entry(win, show="*"))
    pwd_entry.pack(pady=3)

    tk.Label(win, text="EEG CSV File", bg="#0b0c10", fg="#66fcf1", font=("Poppins", 10)).pack(pady=5)
    file_entry = style_widget(tk.Entry(win, width=40))
    file_entry.pack(pady=3)
    create_button(win, "Browse", lambda: open_file_dialog(file_entry)).pack(pady=5)

    create_button(win, "Register",
        lambda: register_user(emp_entry.get(), name_entry.get(), pwd_entry.get(), file_entry.get())
    ).pack(pady=15)

# ---------- Login window ----------
def login_screen():
    win = tk.Toplevel(root)
    win.title("Login")
    win.configure(bg="#0b0c10")
    win.geometry("400x300")

    tk.Label(win, text="Employee ID", bg="#0b0c10", fg="#66fcf1", font=("Poppins", 10)).pack(pady=5)
    emp_entry = style_widget(tk.Entry(win))
    emp_entry.pack(pady=3)

    tk.Label(win, text="Password", bg="#0b0c10", fg="#66fcf1", font=("Poppins", 10)).pack(pady=5)
    pwd_entry = style_widget(tk.Entry(win, show="*"))
    pwd_entry.pack(pady=3)

    tk.Label(win, text="EEG CSV File", bg="#0b0c10", fg="#66fcf1", font=("Poppins", 10)).pack(pady=5)
    file_entry = style_widget(tk.Entry(win, width=40))
    file_entry.pack(pady=3)
    create_button(win, "Browse", lambda: open_file_dialog(file_entry)).pack(pady=5)

    create_button(win, "Login",
        lambda: authenticate_user(emp_entry.get(), pwd_entry.get(), file_entry.get())
    ).pack(pady=15)

# ---------- Main ----------
create_table_if_not_exists()

root = tk.Tk()
root.title("NeuroLock Authentication")
root.geometry("350x250")
root.configure(bg="#0b0c10")

tk.Label(root, text="🔐 NeuroLock", font=("Poppins", 16, "bold"), bg="#0b0c10", fg="#66fcf1").pack(pady=20)
create_button(root, "Register", register_screen).pack(pady=5)
create_button(root, "Login", login_screen).pack(pady=5)
create_button(root, "Exit", root.destroy).pack(pady=10)

root.mainloop()
