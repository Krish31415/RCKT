import json

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

APP_ROOT = os.path.join(os.path.dirname(__file__), '.')
dotenv_path = os.path.join(APP_ROOT, '.env')
load_dotenv(dotenv_path)

app = Flask(__name__)

jwt = JWTManager(app)
CORS(app)

def my_convert(o):
    if isinstance(o, ObjectId):
        return str(o)


app.permament_session_lifetime = timedelta(minutes=2)
app.session_type = 'mongodb'
app.secret_key = os.environ['FLASK_KEY']

client = MongoClient(
    "mongodb+srv://krish:krishkalra@cluster0.zgr19.mongodb.net/myFirstDatabase?retryWrites=true&w=majority", ssl=True,
    ssl_cert_reqs=ssl.CERT_NONE)
db = client.website

app.config['SESSION_MONGODB'] = client
# Session(app)


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        post_data = request.form.to_dict(flat=True)
        if 'login' in post_data:
            user = db.users.find_one({'email': post_data['email']})
            if user:
                if sha256_crypt.verify(post_data['password'], user['password']):
                    print('success')
                    session['email'] = user['email']
                    session['first name'] = user['first name']
                    session.permament = True
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
            db.users.insert_one(post_data)
        else:
            flash('Unknown error')

        return redirect(url_for('login'))

    if request.method == 'GET':
        return render_template('login.html')


def login_required(func):
    @functools.wraps(func)
    def secure_function(*args, **kwargs):
        if "email" not in session:
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


@app.route('/home')
def home():
    try:
        ip = request.headers['X-Forwarded-For'].split(',')[0]
        if ip not in [a['ip'] for a in db.ips.find()]:
            db.ips.insert_one({'ip': ip, 'time': datetime.now()})
    except:
        print('website running locally')
    return render_template('home.html')


@app.route('/about_us')
def about_me():
    return render_template('About us.html')



@app.route('/minesweeper')
def minesweeper():
    return render_template('minesweeper.html')


@login_required
@app.route('/admin/users', methods=['POST'])
def users():
    if request.method == 'POST':
        post_data = request.get_json()
        print(post_data)

        user = db.users.find_one({'email': post_data['email']})
        if user:
            if sha256_crypt.verify(post_data['password'], user['password']):
                print('success')
                access_token = create_access_token(identity=user['email'])
                return jsonify({'message': 'Valid', 'jwt': access_token}), 200
            else:
                return jsonify({'message': 'Password is incorrect'}), 401
        else:
            return jsonify({'message': 'Email not found'}), 401


@app.route('/admin/storage', methods=['POST'])
def storage():
    if request.method == 'POST':
        post_data = request.get_json()
        print(post_data)

        if post_data['type'] == 'getEntries':
            del post_data['type']
            entries = list(db.to_do_entries.find(post_data))
            print(entries)
            return json.loads(json.dumps({'entries': entries}, default=my_convert)), 200
        if post_data['type'] == 'addEntry':
            db.to_do_entries.insert_one(post_data['entry'])
            return jsonify({'message': 'Success'}), 200
        if post_data['type'] == 'updateStatus':
            db.to_do_entries.update_one({'_id': ObjectId(post_data['id']), 'user': post_data['user']},
                                        {'$set': {'status': post_data['status']}})
            return jsonify({'message': 'Success'}), 200
        if post_data['type'] == 'addList':
            _id = db.to_do_lists.insert_one(post_data['entry']).inserted_id
            return json.loads(json.dumps({'message': 'Success', '_id': _id}, default=my_convert)), 200
        if post_data['type'] == 'getLists':
            del post_data['type']
            entries = list(db.to_do_lists.find(post_data))
            print(entries)
            return json.loads(json.dumps({'entries': entries}, default=my_convert)), 200


if __name__ == '__main__':
    app.run(debug=True)
