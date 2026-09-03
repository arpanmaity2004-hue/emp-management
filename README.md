# Employee Attendance Management System

A Flask + MYSQL Workbench 8.0CE Database employee attendance management system.

## Features

- Employee registration and login
- Secure password hashing
- HR login and dashboard
- Employee dashboard
- Attendance check-in/check-out
- Automatic working-hours calculation
- Leave request system
- Leave approval/rejection by HR
- Leave deduction calculation
- Attendance status tracking
## stack 
Python, Flask, MySQL, HTML, CSS, Jinja2, Werkzeug.
## Installation

Open PowerShell/Command Prompt in this project folder:

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

Install packages:

```bash
pip install -r requirements.txt
```

Run:

```bash
python app.py
```

Open:

http://127.0.0.1:5000


## Super Admin LOGIN
- Username: arpanmaity2601@gmail.com
- Password: admin123

## Demo HR Login

EThe HR user enters their registered credentials on the login page.

Example:

Username: Email 
Password: ********
Change the demo password/secret key before using this in production.

## Database

MYSQL Workbench 8.0CE Database `attendance.db` is automatically created the first time the application runs.
## business Rule
- Annual leave quota: 12 calendar days.
- Leave calculation is inclusive: 10 Sep–12 Sep = 3 days.
- Pending leave is not deducted.
- Approved leave is deducted.
- Overlapping pending/approved leave is blocked.
- Check-out calculates working minutes on the server.
- Less than 4 hours = Half Day; 4 hours or more = Present.
- Approved leave dates are automatically marked On Leave.
