import os
from datetime import date, datetime
from functools import wraps

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY",
    "dev-secret-key-change-in-production"
)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:1234@localhost/attendance_db"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

class Employee(db.Model):
    __tablename__ = "employee"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    department = db.Column(db.String(100), nullable=False, default="General")
    role = db.Column(db.String(20), nullable=False, default="employee")
    join_date = db.Column(db.Date, nullable=False, default=date.today)

    attendances = db.relationship(
        "Attendance",
        backref="employee",
        lazy=True,
        cascade="all, delete-orphan"
    )

    leaves = db.relationship(
        "Leave",
        backref="employee",
        lazy=True,
        cascade="all, delete-orphan"
    )

class Attendance(db.Model):
    __tablename__ = "attendance"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(
        db.Integer,
        db.ForeignKey("employee.id"),
        nullable=False
    )
    attendance_date = db.Column(
        db.Date,
        nullable=False,
        default=date.today
    )
    check_in = db.Column(db.DateTime, nullable=True)
    check_out = db.Column(db.DateTime, nullable=True)
    working_hours = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(30), nullable=False, default="Present")

class Leave(db.Model):
    __tablename__ = "leave"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(
        db.Integer,
        db.ForeignKey("employee.id"),
        nullable=False
    )
    leave_type = db.Column(db.String(50), nullable=False, default="Casual")
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    days = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(300), nullable=True)
    status = db.Column(db.String(30), nullable=False, default="Pending")

def get_current_employee():
    employee_id = session.get("employee_id")
    if not employee_id:
        return None
    return db.session.get(Employee, employee_id)

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "employee_id" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))

        employee = get_current_employee()
        if not employee:
            session.clear()
            flash("Your session is invalid. Please login again.", "warning")
            return redirect(url_for("login"))

        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        employee = get_current_employee()
        if not employee:
            session.clear()
            return redirect(url_for("login"))

        if employee.role != "admin":
            flash("Super Admin access required.", "danger")
            return redirect(url_for("index"))

        return f(*args, **kwargs)
    return wrapper

def hr_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        employee = get_current_employee()
        if not employee:
            session.clear()
            return redirect(url_for("login"))

        if employee.role not in ["hr", "admin"]:
            flash("HR access required.", "danger")
            return redirect(url_for("index"))

        return f(*args, **kwargs)
    return wrapper

@app.route("/")
def index():
    employee = get_current_employee()
    if not employee:
        session.clear()
        return redirect(url_for("login"))

    if employee.role == "admin":
        return redirect(url_for("admin_dashboard"))
    if employee.role == "hr":
        return redirect(url_for("hr_dashboard"))
    return redirect(url_for("dashboard"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        department = request.form.get("department", "General").strip()

        if not name or not email or not password:
            flash("Name, email, and password are required.", "danger")
            return redirect(url_for("register"))

        if Employee.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return redirect(url_for("register"))

        employee = Employee(
            name=name,
            email=email,
            password=generate_password_hash(password),
            department=department or "General",
            role="employee",
            join_date=date.today()
        )

        try:
            db.session.add(employee)
            db.session.commit()
            flash("Registration successful. Please login.", "success")
            return redirect(url_for("login"))
        except Exception as error:
            db.session.rollback()
            flash("Registration failed. Please try again.", "danger")
            return redirect(url_for("register"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Email and password are required.", "danger")
            return render_template("login.html")

        employee = Employee.query.filter_by(email=email).first()
        password_valid = False

        if employee:
            try:
                password_valid = check_password_hash(employee.password, password)
            except Exception:
                password_valid = False

        if employee and password_valid:
            session.clear()
            session["employee_id"] = employee.id
            session["name"] = employee.name
            session["role"] = employee.role

            if employee.role == "admin":
                return redirect(url_for("admin_dashboard"))
            if employee.role == "hr":
                return redirect(url_for("hr_dashboard"))
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    employee = get_current_employee()

    if employee.role == "admin":
        return redirect(url_for("admin_dashboard"))
    if employee.role == "hr":
        return redirect(url_for("hr_dashboard"))

    today = date.today()
    today_attendance = Attendance.query.filter_by(
        employee_id=employee.id,
        attendance_date=today
    ).first()

    records = (
        Attendance.query.filter_by(employee_id=employee.id)
        .order_by(Attendance.attendance_date.desc())
        .limit(10)
        .all()
    )

    approved_leaves = Leave.query.filter_by(
        employee_id=employee.id,
        status="Approved"
    ).all()

    leave_used = sum(leave.days for leave in approved_leaves)
    leave_balance = max(12 - leave_used, 0)

    total_present = Attendance.query.filter(
        Attendance.employee_id == employee.id,
        Attendance.status == "Present"
    ).count()

    total_hours = sum(
        attendance.working_hours or 0.0 for attendance in employee.attendances
    )

    return render_template(
        "employee_dashboard.html",
        emp=employee,
        today_att=today_attendance,
        records=records,
        leave_balance=leave_balance,
        leave_used=leave_used,
        total_present=total_present,
        total_hours=round(total_hours, 2)
    )

@app.route("/check-in", methods=["POST"])
@login_required
def check_in():
    employee = get_current_employee()
    if not employee or employee.role != "employee":
        flash("Only employees can mark attendance.", "warning")
        return redirect(url_for("index"))

    today = date.today()
    attendance = Attendance.query.filter_by(
        employee_id=employee.id,
        attendance_date=today
    ).first()

    if attendance and attendance.check_in:
        flash("You have already checked in today.", "warning")
        return redirect(url_for("dashboard"))

    if not attendance:
        attendance = Attendance(
            employee_id=employee.id,
            attendance_date=today,
            working_hours=0,
            status="Present"
        )
        db.session.add(attendance)

    attendance.check_in = datetime.now()
    attendance.status = "Present"

    try:
        db.session.commit()
        flash("Check-in recorded successfully.", "success")
    except Exception:
        db.session.rollback()
        flash("Unable to record check-in.", "danger")

    return redirect(url_for("dashboard"))

@app.route("/check-out", methods=["POST"])
@login_required
def check_out():
    employee = get_current_employee()
    if not employee or employee.role != "employee":
        flash("Only employees can mark attendance.", "warning")
        return redirect(url_for("index"))

    today = date.today()
    attendance = Attendance.query.filter_by(
        employee_id=employee.id,
        attendance_date=today
    ).first()

    if not attendance or not attendance.check_in:
        flash("Please check in first.", "danger")
        return redirect(url_for("dashboard"))

    if attendance.check_out:
        flash("You have already checked out today.", "warning")
        return redirect(url_for("dashboard"))

    attendance.check_out = datetime.now()
    seconds = max((attendance.check_out - attendance.check_in).total_seconds(), 0)
    attendance.working_hours = round(seconds / 3600, 2)

    try:
        db.session.commit()
        total_minutes = round(seconds / 60)
        hours, minutes = divmod(total_minutes, 60)
        flash(f"Check-out recorded. Time: {hours}h {minutes:02d}m.", "success")
    except Exception:
        db.session.rollback()
        flash("Unable to record check-out.", "danger")

    return redirect(url_for("dashboard"))

@app.route("/leave", methods=["GET", "POST"])
@login_required
def leave():
    employee = get_current_employee()
    if not employee or employee.role != "employee":
        flash("Only employees can request leave.", "warning")
        return redirect(url_for("index"))

    if request.method == "POST":
        try:
            start_date = datetime.strptime(
                request.form.get("start_date", ""), "%Y-%m-%d"
            ).date()
            end_date = datetime.strptime(
                request.form.get("end_date", ""), "%Y-%m-%d"
            ).date()
        except ValueError:
            flash("Please enter valid dates.", "danger")
            return redirect(url_for("leave"))

        if end_date < start_date:
            flash("End date cannot be before start date.", "danger")
            return redirect(url_for("leave"))

        days = (end_date - start_date).days + 1
        leave_type = request.form.get("leave_type", "Casual").strip()
        reason = request.form.get("reason", "").strip()

        approved_leaves = Leave.query.filter_by(
            employee_id=employee.id, status="Approved"
        ).all()
        used_leave = sum(item.days for item in approved_leaves)
        leave_balance = max(12 - used_leave, 0)

        if days > leave_balance:
            flash(f"Insufficient leave balance. Available: {leave_balance} day(s).", "danger")
            return redirect(url_for("leave"))

        overlapping_leave = Leave.query.filter(
            Leave.employee_id == employee.id,
            Leave.status.in_(["Pending", "Approved"]),
            Leave.start_date <= end_date,
            Leave.end_date >= start_date
        ).first()

        if overlapping_leave:
            flash("You already have a leave request for selected dates.", "warning")
            return redirect(url_for("leave"))

        leave_obj = Leave(
            employee_id=employee.id,
            leave_type=leave_type or "Casual",
            start_date=start_date,
            end_date=end_date,
            days=days,
            reason=reason,
            status="Pending"
        )

        try:
            db.session.add(leave_obj)
            db.session.commit()
            flash("Leave request submitted successfully.", "success")
        except Exception:
            db.session.rollback()
            flash("Unable to submit leave request.", "danger")

        return redirect(url_for("leave"))

    leaves = Leave.query.filter_by(employee_id=employee.id).order_by(Leave.id.desc()).all()
    approved_leaves = Leave.query.filter_by(employee_id=employee.id, status="Approved").all()
    leave_used = sum(item.days for item in approved_leaves)
    leave_balance = max(12 - leave_used, 0)

    return render_template(
        "leave.html",
        leaves=leaves,
        emp=employee,
        leave_balance=leave_balance,
        leave_used=leave_used
    )

@app.route("/hr")
@hr_required
def hr_dashboard():
    employee = get_current_employee()
    today = date.today()

    employees = Employee.query.filter_by(role="employee").order_by(Employee.id.asc()).all()
    today_records = (
        db.session.query(Attendance, Employee)
        .join(Employee, Attendance.employee_id == Employee.id)
        .filter(Attendance.attendance_date == today, Employee.role == "employee")
        .order_by(Employee.id.asc())
        .all()
    )
    leaves = (
        db.session.query(Leave, Employee)
        .join(Employee, Leave.employee_id == Employee.id)
        .order_by(Leave.id.desc())
        .all()
    )

    total_employees = Employee.query.filter_by(role="employee").count()
    total_hr = Employee.query.filter_by(role="hr").count()
    present = sum(1 for att, _ in today_records if att.status == "Present")
    checked_out = sum(1 for att, _ in today_records if att.check_out is not None)

    pending = Leave.query.filter_by(status="Pending").count()
    approved = Leave.query.filter_by(status="Approved").count()
    rejected = Leave.query.filter_by(status="Rejected").count()

    return render_template(
        "hr_dashboard.html",
        emp=employee,
        employees=employees,
        today_records=today_records,
        leaves=leaves,
        total_employees=total_employees,
        total_hr=total_hr,
        present=present,
        checked_out=checked_out,
        pending=pending,
        approved=approved,
        rejected=rejected,
        today=today
    )

@app.route("/hr/leave/<int:leave_id>/<action>", methods=["POST"])
@hr_required
def update_leave(leave_id, action):
    leave_obj = db.session.get(Leave, leave_id)
    if not leave_obj or action not in ["approve", "reject"]:
        flash("Invalid request.", "danger")
        return redirect(url_for("hr_dashboard"))

    if leave_obj.status != "Pending":
        flash("Leave request already processed.", "warning")
        return redirect(url_for("hr_dashboard"))

    if action == "approve":
        approved_leaves = Leave.query.filter(
            Leave.employee_id == leave_obj.employee_id,
            Leave.status == "Approved",
            Leave.id != leave_obj.id
        ).all()
        used_days = sum(item.days for item in approved_leaves)

        if used_days + leave_obj.days > 12:
            flash("Leave cannot be approved: Exceeds balance limit.", "danger")
            return redirect(url_for("hr_dashboard"))

        leave_obj.status = "Approved"
    else:
        leave_obj.status = "Rejected"

    try:
        db.session.commit()
        flash(f"Leave {leave_obj.status.lower()} successfully.", "success")
    except Exception:
        db.session.rollback()
        flash("Unable to update leave request.", "danger")

    return redirect(url_for("hr_dashboard"))

@app.route("/admin")
@admin_required
def admin_dashboard():
    employee = get_current_employee()
    today = date.today()

    employees = Employee.query.order_by(Employee.id.asc()).all()
    today_records = (
        db.session.query(Attendance, Employee)
        .join(Employee, Attendance.employee_id == Employee.id)
        .filter(Attendance.attendance_date == today)
        .order_by(Employee.id.asc())
        .all()
    )
    leaves = (
        db.session.query(Leave, Employee)
        .join(Employee, Leave.employee_id == Employee.id)
        .order_by(Leave.id.desc())
        .all()
    )

    total_employees = Employee.query.filter_by(role="employee").count()
    total_hr = Employee.query.filter_by(role="hr").count()
    total_admin = Employee.query.filter_by(role="admin").count()

    present = sum(1 for att, _ in today_records if att.status == "Present")
    checked_out = sum(1 for att, _ in today_records if att.check_out is not None)

    pending = Leave.query.filter_by(status="Pending").count()
    approved = Leave.query.filter_by(status="Approved").count()
    rejected = Leave.query.filter_by(status="Rejected").count()

    return render_template(
        "admin_dashboard.html",
        emp=employee,
        employees=employees,
        today_records=today_records,
        leaves=leaves,
        total_employees=total_employees,
        total_hr=total_hr,
        total_admin=total_admin,
        present=present,
        checked_out=checked_out,
        pending=pending,
        approved=approved,
        rejected=rejected,
        today=today
    )

@app.route("/admin/add-employee", methods=["GET", "POST"])
@admin_required
def add_employee():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        department = request.form.get("department", "General").strip()
        role = request.form.get("role", "employee").strip().lower()

        if role not in ["employee", "hr", "admin"]:
            role = "employee"

        if not name or not email or not password:
            flash("Name, email, and password are required.", "danger")
            return redirect(url_for("add_employee"))

        if Employee.query.filter_by(email=email).first():
            flash("This email is already registered.", "danger")
            return redirect(url_for("add_employee"))

        new_employee = Employee(
            name=name,
            email=email,
            password=generate_password_hash(password),
            department=department or "General",
            role=role,
            join_date=date.today()
        )

        try:
            db.session.add(new_employee)
            db.session.commit()
            flash(f"{role.upper()} account created successfully.", "success")
            return redirect(url_for("admin_dashboard"))
        except Exception:
            db.session.rollback()
            flash("Unable to create account.", "danger")
            return redirect(url_for("add_employee"))

    return render_template("add_employee.html")

@app.route("/admin/change-role/<int:employee_id>/<new_role>", methods=["POST"])
@admin_required
def change_role(employee_id, new_role):
    admin = get_current_employee()
    target = db.session.get(Employee, employee_id)

    if not target:
        flash("Employee not found.", "danger")
        return redirect(url_for("admin_dashboard"))

    new_role = new_role.lower()
    valid_roles = ["employee", "hr", "admin"]

    if new_role not in valid_roles:
        flash("Invalid role specified.", "danger")
        return redirect(url_for("admin_dashboard"))

    if target.id == admin.id and new_role != "admin":
        flash("You cannot change your own admin role directly.", "warning")
        return redirect(url_for("admin_dashboard"))

    target.role = new_role

    try:
        db.session.commit()
        flash(f"Role updated to {new_role.upper()} for {target.name}.", "success")
    except Exception as error:
        db.session.rollback()
        flash("Failed to update role.", "danger")

    return redirect(url_for("admin_dashboard"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)