from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
import google_sheets_service as sheets

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cssd_database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key' # Change this in production

# --- Constants ---
# User Roles
ROLE_CSSD = 'CSSD'
ROLE_UNIT = 'Unit'
ROLE_MANAGEMENT = 'Management'
USER_ROLES = [ROLE_CSSD, ROLE_UNIT, ROLE_MANAGEMENT]

# Instrument Statuses
STATUS_DECONTAMINATION = 'Decontamination'
STATUS_STERILIZED = 'Sterilized'
STATUS_DISTRIBUTION = 'Ready for Distribution'
STATUS_IN_USE = 'In Use'
INSTRUMENT_STATUSES = [STATUS_DECONTAMINATION, STATUS_STERILIZED, STATUS_DISTRIBUTION, STATUS_IN_USE]


db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(50), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class InstrumentSet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(50), default=STATUS_DECONTAMINATION)

class SterilizationCycle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    set_id = db.Column(db.Integer, db.ForeignKey('instrument_set.id'), nullable=False)
    instrument_set = db.relationship('InstrumentSet', backref=db.backref('cycles', lazy=True))
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
    status_from = db.Column(db.String(50))
    status_to = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('actions', lazy=True))

# Routes
@app.route('/')
@login_required
def index():
    sets = InstrumentSet.query.all()
    # Create a summary of set counts by status
    status_counts = db.session.query(InstrumentSet.status, db.func.count(InstrumentSet.status)).group_by(InstrumentSet.status).all()
    status_summary = dict(status_counts)

    # Ensure all possible statuses are present in the summary
    for status in INSTRUMENT_STATUSES:
        if status not in status_summary:
            status_summary[status] = 0

    return render_template('index.html', sets=sets, status_summary=status_summary,
                           status_decon=STATUS_DECONTAMINATION,
                           status_ster=STATUS_STERILIZED,
                           status_dist=STATUS_DISTRIBUTION,
                           status_use=STATUS_IN_USE,
                           ROLE_CSSD=ROLE_CSSD)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        if role not in USER_ROLES:
            flash(f'Invalid role selected.')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('Username already exists.')
            return redirect(url_for('register'))

        new_user = User(username=username, role=role)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', roles=USER_ROLES)


@app.route('/set', methods=['POST'])
@login_required
def add_set():
    if current_user.role != ROLE_CSSD:
        flash('You are not authorized to perform this action.', 'error')
        return redirect(url_for('index'))
    name = request.form['name']
    new_set = InstrumentSet(name=name)
    db.session.add(new_set)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/update_status/<int:set_id>', methods=['POST'])
@login_required
def update_status(set_id):
    if current_user.role != ROLE_CSSD:
        flash('You are not authorized to perform this action.', 'error')
        return redirect(url_for('index'))

    instrument_set = InstrumentSet.query.get_or_404(set_id)
    old_status = instrument_set.status
    new_status = request.form['status']

    if new_status not in INSTRUMENT_STATUSES:
        flash(f'Invalid status "{new_status}".', 'error')
        return redirect(url_for('index'))

    if old_status != new_status:
        cycle_log = SterilizationCycle(
            set_id=instrument_set.id,
            status_from=old_status,
            status_to=new_status,
            user_id=current_user.id
        )
        db.session.add(cycle_log)

        instrument_set.status = new_status
        db.session.commit()
        flash(f'Status for set "{instrument_set.name}" updated to {new_status}.', 'success')
    else:
        flash('No change in status.', 'info')

    return redirect(url_for('index'))

@app.route('/set_history/<int:set_id>')
@login_required
def set_history(set_id):
    instrument_set = InstrumentSet.query.get_or_404(set_id)
    history = SterilizationCycle.query.filter_by(set_id=set_id).order_by(SterilizationCycle.timestamp.desc()).all()
    return render_template('set_history.html', instrument_set=instrument_set, history=history)

@app.route('/import', methods=['GET', 'POST'])
@login_required
def import_from_sheet():
    if current_user.role != ROLE_CSSD:
        flash('You are not authorized to perform this action.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        spreadsheet_id = request.form['spreadsheet_id']
        range_name = request.form['range_name']

        try:
            values, error = sheets.read_sheet(spreadsheet_id, range_name)
            if error:
                flash(f'Error reading from Google Sheet: {error}', 'error')
                return redirect(url_for('import_from_sheet'))

            imported_count = 0
            for row in values:
                if not row: continue # Skip empty rows
                set_name = row[0]

                # Check if set already exists
                existing_set = InstrumentSet.query.filter_by(name=set_name).first()
                if not existing_set:
                    new_set = InstrumentSet(name=set_name)
                    db.session.add(new_set)
                    imported_count += 1

            db.session.commit()
            flash(f'Successfully imported {imported_count} new instrument sets.', 'success')
            return redirect(url_for('index'))

        except Exception as e:
            flash(f'An unexpected error occurred: {e}', 'error')
            return redirect(url_for('import_from_sheet'))

    return render_template('import.html')

@app.route('/export')
@login_required
def export_to_sheet():
    try:
        # 1. Fetch all data
        all_sets = InstrumentSet.query.all()

        # 2. Prepare data for export
        header = ['Set ID', 'Set Name', 'Current Status', 'Last Update', 'User', 'Action']
        data_to_export = [header]

        for s in all_sets:
            last_cycle = SterilizationCycle.query.filter_by(set_id=s.id).order_by(SterilizationCycle.timestamp.desc()).first()
            if last_cycle:
                row = [
                    s.id,
                    s.name,
                    s.status,
                    last_cycle.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    last_cycle.user.username,
                    f"From '{last_cycle.status_from}' to '{last_cycle.status_to}'"
                ]
                data_to_export.append(row)
            else:
                data_to_export.append([s.id, s.name, s.status, 'No history', '', ''])

        # 3. Create a new Google Sheet
        from datetime import datetime
        sheet_title = f"CSSD_Export_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        spreadsheet_id, spreadsheet_url, error = sheets.create_new_sheet(sheet_title)

        if error:
            flash(f'Could not create Google Sheet: {error}', 'error')
            return redirect(url_for('index'))

        # 4. Write data to the new sheet
        success, error = sheets.write_to_sheet(spreadsheet_id, data_to_export)

        if error:
            flash(f'Error writing to Google Sheet: {error}', 'error')
            return redirect(url_for('index'))

        flash(f'Successfully exported data. <a href="{spreadsheet_url}" target="_blank">Open Google Sheet</a>', 'success')

    except Exception as e:
        flash(f'An error occurred during export: {e}', 'error')

    return redirect(url_for('index'))


def seed_database():
    """Seeds the database with an initial admin user if no users exist."""
    if User.query.first() is None:
        print("No users found. Seeding database with admin user...")
        admin_user = User(username='admin', role=ROLE_CSSD)
        admin_user.set_password('admin')
        db.session.add(admin_user)
        db.session.commit()
        print("Admin user created with username 'admin' and password 'admin'.")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_database()
    app.run(debug=True, host='0.0.0.0', port=8080)