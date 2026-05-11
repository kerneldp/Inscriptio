<img width="112" height="43" alt="image" src="https://github.com/user-attachments/assets/4a406c0e-072f-486d-befe-4175e7b9834b" />

## 📝 AI-Powered Pre-Diagnostic Dysgraphia Screening Agent

---

## 🚀 Quick Start Guide

### ⚠️ Prerequisites
Before running the scripts, ensure you have a compatible version of Python installed:
* **Required:** Python 3.9, 3.10, or 3.11.
* **Not Supported:** Python 3.12 or higher (TensorFlow will crash).

---

### 🗄️ Database Setup (MySQL)
This application requires a MySQL database.
1. Install and start a local server environment like **WAMP** (Windows), **MAMP** (Mac), or **XAMPP**.
2. Open phpMyAdmin (or your preferred MySQL client) and create a new database named `inscriptio_db`.
3. Import the `inscriptio/inscriptio_db.sql` file into the newly created `inscriptio_db` database.
4. Open the `inscriptio/python/.env` file and ensure the correct `DATABASE_URL` is uncommented based on your environment:
   * **Mac (MAMP default port 8889):** Use the URL with port `8889`.
   * **Windows/Linux (WAMP/XAMPP default port 3306):** Use the URL with port `3306`. 
   *(Note: WAMP/XAMPP often uses an empty password by default, so you may need to change `root:root` to `root:@`)*.


---

### 🍏💻 Mac & Linux Instructions
1. Open your **Terminal**.
2. Navigate to the root folder of the project (`Inscriptio`).
3. Grant execution permissions to the script by running: chmod +x start.sh
4. Launch the application: ./start.sh

### 🪟 Windows Instructions
1. Open File Explorer and navigate to the root folder of the project (Inscriptio).
2. Launch the application: Simply double-click the start.bat file.
3. Alternatively, open Command Prompt, navigate to the folder, and run .\start.bat. 

---

### ✅ Go Signal Indicator
<img width="297" height="41" alt="image" src="https://github.com/user-attachments/assets/3c52f788-ef68-4009-b549-53dda56f3624" />
