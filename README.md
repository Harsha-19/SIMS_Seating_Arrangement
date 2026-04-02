# 🏫 SOUNDARYA INSTITUTE - Smart Institutional Management System (SIMS)

A professional, high-fidelity SaaS-grade dashboard constructed for the management of educational session data, including students, examination halls, schedules, and automated seating arrangements.

---

## 🌟 Primary Features

- **Dynamic Student Management**: Reactive filtering by Department and Semester with live AJAX searching.
- **Automated Seating Engine**: High-fidelity, row-by-row seating allocation with fixed `[3, 2, 3]` section filling patterns for exam halls.
- **Academic Setup**: Configurable Departments and Semesters with dependent dropdown logic.
- **Attendance Management**: Automated PDF/Print-ready attendance list generation based on seating plans.
- **SaaS-Grade UI**: Modern dark/light mode aesthetics using Tailwind CSS and Lucide Icons.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.x, Django 5.x, Django REST Framework (DRF).
- **Frontend**: Vanilla JavaScript (AJAX/Fetch), Tailwind CSS (CDN), Lucide Icons.
- **Database**: SQLite (Development) / PostgreSQL (Production ready).
- **Environment**: Virtualenv (.venv).

---

## 🚀 How to Run the Project

### 1. Repository Location
Open your terminal and navigate to the project root directory:
```bash
cd "d:\My Things\PROJECTS\seating arrengement"
```

### 2. Activate Virtual Environment
Ensure you are using the local virtual environment to avoid dependency conflicts:
```powershell
.\.venv\Scripts\activate
```

### 3. Initialize & Run Server
To start the internal development server, execute the following command **inside the project root folder** (where `manage.py` is located):
```bash
python manage.py runserver
```

### 4. Access the Platform
Once the server is running, open your browser and go to:
- **Dashboard**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **API Root**: [http://127.0.0.1:8000/api/](http://127.0.0.1:8000/api/)

---

## 🔐 Administrative Access
Login directly to the dashboard to begin managing institutional data:
- **Support Contact**: Harsha (`harshamt2005@gmail.com`)
- **Main Office**: Soundarya Institute of Management and Science
