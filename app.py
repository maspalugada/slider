from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cssd_database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key' # Change this in production

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(50), nullable=False)  # e.g., 'CSSD', 'Unit', 'Management'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class InstrumentSet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(50), default='Decontamination')  # e.g., 'Decontamination', 'Sterilized', 'In Use'

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
    all_statuses = ['Decontamination', 'Sterilized', 'Ready for Distribution', 'In Use']
    for status in all_statuses:
        if status not in status_summary:
            status_summary[status] = 0

    return render_template('index.html', sets=sets, status_summary=status_summary)

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

        # Check if username already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists.')
            return redirect(url_for('register'))

        new_user = User(username=username, role=role)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/set', methods=['POST'])
@login_required
def add_set():
    if current_user.role != 'CSSD':
        flash('You are not authorized to perform this action.')
        return redirect(url_for('index'))
    name = request.form['name']
    new_set = InstrumentSet(name=name)
    db.session.add(new_set)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/update_status/<int:set_id>', methods=['POST'])
@login_required
def update_status(set_id):
    if current_user.role != 'CSSD':
        flash('You are not authorized to perform this action.')
        return redirect(url_for('index'))

    instrument_set = InstrumentSet.query.get_or_404(set_id)
    old_status = instrument_set.status
    new_status = request.form['status']

    if old_status != new_status:
        # Create a record of the status change
        cycle_log = SterilizationCycle(
            set_id=instrument_set.id,
            status_from=old_status,
            status_to=new_status,
            user_id=current_user.id
        )
        db.session.add(cycle_log)

        # Update the instrument set's status
        instrument_set.status = new_status
        db.session.commit()
        flash(f'Status for set "{instrument_set.name}" updated to {new_status}.')
    else:
        flash('No change in status.')

    return redirect(url_for('index'))

@app.route('/set_history/<int:set_id>')
@login_required
def set_history(set_id):
    instrument_set = InstrumentSet.query.get_or_404(set_id)
    history = SterilizationCycle.query.filter_by(set_id=set_id).order_by(SterilizationCycle.timestamp.desc()).all()
    return render_template('set_history.html', instrument_set=instrument_set, history=history)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=8080)