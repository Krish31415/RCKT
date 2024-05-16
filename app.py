import json

import certifi
from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify
from datetime import datetime, timedelta, date, timezone
from pymongo import MongoClient
from bson.objectid import ObjectId
from passlib.hash import sha256_crypt
from flask_session import Session
from dotenv import load_dotenv
import random, functools, re, ssl, os
from flask_cors import CORS
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, JWTManager
from pymongo.server_api import ServerApi

APP_ROOT = os.path.join(os.path.dirname(__file__), '.')
dotenv_path = os.path.join(APP_ROOT, '.env')
load_dotenv(dotenv_path)

app = Flask(__name__)

jwt = JWTManager(app)
CORS(app)


def my_convert(o):
    if isinstance(o, ObjectId):
        return str(o)


app.permanent_session_lifetime = timedelta(minutes=5)
app.session_type = 'mongodb'
app.secret_key = os.environ['FLASK_KEY']

uri = os.environ['MONGODB_URI']
# Create a new client and connect to the server
client = MongoClient(uri, tlsCAFile=certifi.where())
db = client.wasteland

app.config['SESSION_MONGODB'] = client


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        post_data = request.form.to_dict(flat=True)
        if 'login' in post_data:
            user = db.users.find_one({'email': post_data['email']})
            if user:
                if sha256_crypt.verify(post_data['password'], user['password']):
                    session['email'] = user['email']
                    session['first name'] = user['first name']
                    return redirect(url_for('home'))
                else:
                    flash('Password is incorrect')
            else:
                flash('Email not found')

        elif 'sign up' in post_data.keys():
            del post_data['sign up']

            # checks if email used for account
            if db.users.find_one({'email': post_data['email']}):
                flash('Account already exists')
                return redirect(url_for('login'))

            # regex checks email
            regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            if not (re.fullmatch(regex, post_data['email'])):
                flash('Invalid email')
                return redirect(url_for('login'))

            # password length must be 5 or more
            if len(post_data['password']) < 5:
                flash('Password must have atleast 5 characters')
                return redirect(url_for('login'))

            post_data['password'] = sha256_crypt.hash(post_data['password'])
            post_data['karma'] = 0
            db.users.insert_one(post_data)
        else:
            flash('Unknown error')

        return redirect(url_for('login'))

    if request.method == 'GET':
        if 'email' in session.keys():
            return redirect(url_for('dashboard'))
        return render_template('login.html')


def login_required(func):
    @functools.wraps(func)
    def secure_function(*args, **kwargs):
        if not ("email" in session.keys()):
            session.clear()
            flash('You must log in.')
            return redirect(url_for("login", next=request.path))
        return func(*args, **kwargs)

    return secure_function


@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('Logout successful')
    return redirect(url_for('login'))


@app.route('/')
def home():
    oui = 0.25 * (
            2.5 + 5 + 5.4 + 5.5 + 5.5 + 5.5 + 5.45 + 5.4 + 5.35 + 5.25 + 5.15 + 5 + 4.85 + 4.7 + 4.5 + 4.3 + 4.15 + 4 + 3.9 + 4 + 4.15 + 4.3 + 4.4 + 4.5 + 4.6)
    return render_template('home.html')


@app.route('/about_us')
def about_us():
    return render_template('about us.html')


# POSTER
@app.route('/poster', methods=['GET', 'POST'])
@login_required
def poster():
    if request.method == 'POST':
        print('recieved data')
        post_data: dict = request.form.to_dict(flat=True)

        print(post_data)

        post_data['user email'] = session['email']

        # Convert string of tuple of pos into latitude and longitude variables
        unfiltered_pos = post_data['pos'].split(',')
        pos = unfiltered_pos[0][1:], unfiltered_pos[1][:-1]
        post_data['lat'], post_data['lng'] = pos
        del post_data['pos']
        db.reports.insert_one(post_data)

        # Increase the user's karma by 1
        db.users.update_one(
            {'email': session['email']},
            {'$inc': {'karma': 1}}
        )

        return redirect(url_for('dashboard'))

    if request.method == 'GET':
        return render_template('poster.html')


@app.route('/receiver')
def receiver():
    reports = list(db.reports.find())
    print(reports)
    return render_template('receiver.html', reports=reports)


@app.route('/dashboard')
@login_required
def dashboard():
    user_karma = db.users.find_one({'email': session['email']})['karma']
    return render_template('dashboard.html', karma=user_karma)


@app.route('/minesweeper')
def minesweeper():
    return render_template('minesweeper.html')


if __name__ == '__main__':
    app.run(debug=True)
