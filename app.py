from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cssd_database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key' # Change this in production

db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    role = db.Column(db.String(50), nullable=False)  # e.g., 'CSSD', 'Unit', 'Management'

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

@app.route('/')
def index():
    sets = InstrumentSet.query.all()
    return render_template('index.html', sets=sets)

@app.route('/set', methods=['POST'])
def add_set():
    name = request.form['name']
    new_set = InstrumentSet(name=name)
    db.session.add(new_set)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/update_status/<int:set_id>', methods=['POST'])
def update_status(set_id):
    new_status = request.form['status']
    instrument_set = InstrumentSet.query.get(set_id)
    instrument_set.status = new_status
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=8080)