import pandas as pd
import numpy as np
import mysql.connector
import bcrypt

# === Step 1: Load EEG Data ===
def load_eeg_data(file_path):
    df = pd.read_csv(file_path)
    
    # If multiple channels, flatten into one signal
    df = df.select_dtypes(include=[np.number])
    flat_signal = df.values.flatten()

    return pd.DataFrame(flat_signal, columns=["EEG_Signal"])

# === Step 2: Normalize EEG data ===
def normalize_signal(df):
    signal = df["EEG_Signal"].values
    normalized = (signal - np.min(signal)) / (np.max(signal) - np.min(signal))
    return normalized

# === Step 3: Convert to binary ===
def signal_to_binary(normalized_signal):
    return np.array(normalized_signal, dtype=np.float32).tobytes()

# === Step 4: Save to MySQL Database ===
import pandas as pd
import numpy as np
import mysql.connector
import bcrypt

def save_to_database(emp_id, name, password, csv_path):
    # Read and flatten EEG CSV
    df = pd.read_csv(csv_path)
    flat_array = df.values.flatten().astype(np.float64)
    
    # Convert to binary safely
    brainwave_binary = flat_array.tobytes()

    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="yourpassword",
        database="neurolock"
    )
    cursor = conn.cursor()
    query = """
        INSERT INTO neuro_users (emp_id, name, password, brainwave)
        VALUES (%s, %s, %s, %s)
    """
    cursor.execute(query, (emp_id, name, password_hash, brainwave_binary))
    conn.commit()
    cursor.close()
    conn.close()
    print(f"✅ Inserted user {emp_id} successfully.")

# === Step 5: Run the pipeline ===
if __name__ == "__main__":
    file_path = r"C:\Users\jan23\Downloads\archive (1)\s27.csv"

    df = load_eeg_data(file_path)
    normalized_signal = normalize_signal(df)
    binary_data = signal_to_binary(normalized_signal)

    # Example user data
    emp_id = "E001"
    name = "klaus"
    password = "123"

    save_to_database(emp_id, name, password, binary_data)
