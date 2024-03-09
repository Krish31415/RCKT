import json

from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify
from datetime import datetime, timedelta, date, timezone
from pymongo import MongoClient
from bson.objectid import ObjectId
from passlib.hash import sha256_crypt
from flask_session import Session
from nasapy import Nasa
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

# Setup nasa
nasa = Nasa(key=os.environ['NASA_KEY'])


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


@app.route('/about_me')
def about_me():
    return render_template('About me.html')


@app.route('/notepad', methods=['GET', 'POST'])
@login_required
def notepad():
    if request.method == 'POST':
        note = {
            'text': request.form['new note'],
            'email': session['email'],
            # 'ip': request.headers['X-Forwarded-For'].split(',')[0],
            'utc_time': datetime.now(timezone.utc) 
        }
        if len(list(db.notes.find())) < 10:
            db.notes.insert_one(note)
        return redirect(url_for('notepad'))

    if request.method == 'GET':
        notes = db.notes.find({'email': session['email']})
        return render_template('notepad.html', notes=notes)


@app.route('/delete_note/<note_id>')
@login_required
def delete_note(note_id):
    db.notes.delete_one({'_id': ObjectId(note_id)})
    return redirect(url_for('notepad'))


@app.route('/contact_manager', methods=['GET', 'POST'])
@login_required
def contact_manager():
    if request.method == 'POST':
        contact = {
            'name': request.form['new name'],
            'number': request.form['new number'],
            'email': session['email'],
            # 'ip': request.headers['X-Forwarded-For'].split(',')[0],
            'utc_time': datetime.now(timezone.utc) 
        }

        if contact['name'].strip() == '':
            flash('Name is empty')
            return redirect(url_for('contact_manager'))

        if contact['number'].strip() == '':
            flash('Number is empty')
            return redirect(url_for('contact_manager'))

        if not contact['number'].strip().isnumeric():
            flash('Number is not numeric')
            return redirect(url_for('contact_manager'))

        if len(list(db.contacts.find())) < 10:
            db.contacts.insert_one(contact)
            flash('Contact created')
        else:
            flash('Too many contacts')
        print(contact)
        return redirect(url_for('contact_manager'))

    if request.method == 'GET':
        contacts = db.contacts.find({'email': session['email']})
        return render_template('contact manager.html', contacts=contacts)


@app.route('/delete_contact/<contact_id>')
@login_required
def delete_contact(contact_id):
    db.contacts.delete_one({'_id': ObjectId(contact_id)})
    return redirect('/contact_manager')


@app.route('/jumbled_words', methods=['GET', 'POST'])
@login_required
def jumbled_words_menu():
    if request.method == 'POST':
        print(request.form['word'])
        word = {
            'word': request.form['word'],
            # 'ip': ip if (ip := request.headers['X-Forwarded-For'].split(',')[0]) else request.remote_addr,
            'utc': datetime.now(timezone.utc) 
        }
        if len(list(db.words.find())) > 20:
            flash('Too many words')
        elif ' ' in word['word']:
            flash('No spaces allowed')
        else:
            db.words.insert_one(word)
            flash('Word succesfully added')

        return redirect(url_for('jumbled_words_menu'))

    if request.method == 'GET':
        return render_template('jumbled words menu.html')


@app.route('/jumbled_words/play', methods=['GET', 'POST'])
@login_required
def jumbled_words():
    if request.method == 'POST':
        session['words'] = [request.form['word' + str(a)] for a in range(5)]
        return redirect(url_for('jumbled_words_results'))

    if request.method == 'GET':
        words = [a['word'] for a in db.words.find()]
        answers = [random.choice(words) for _ in range(5)]
        words = []
        for answer in answers:
            word = list(answer)
            random.shuffle(word)
            words.append(''.join(word))
        session['words'] = words
        session['answers'] = answers
        [print(a) for a in answers]
        return render_template('jumbled words.html')


@app.route('/jumbled_words/results')
@login_required
def jumbled_words_results():
    if request.method == 'GET':
        if not (session['words'] and session['answers']): return redirect(url_for('jumbled_words'))
        return render_template('jumbled words results.html')


@app.route('/nasa', methods=['GET', 'POST'])
def NASA():
    earth_date = request.args.get('date')
    print(f'{earth_date=}')
    data = nasa.mars_rover(earth_date=earth_date if earth_date else date.today().isoformat())
    return render_template('nasa.html', data=data, earth_date=earth_date)


@app.route('/school/spanish')
def spanish():
    sentences = [
        '1. Debes comer las frutas para mantener la salud.',
        '2. No debes comer los pasteles para tu salud.',
        '3. Prefiero beber el agua o la leche para tu salud.',
        '4. Debes caminar para mantenter la salud.',
        '5. Debes comer mucho las judías verdes y los guisantes para mantener la salud.',
        '6. El pollo es muy sabroso y bueno para mantener tu salud.',
        '7. Debes comer los zanahorias para mantener tu salud de tus ojos.',
        '8. Debes levantar pesas para la salud de tus brazos.',
        '9. Debes beber el jugo de manzana o el jugo de naranja pura mantener tu salud.',
        '10. La ensalada de verduras es may bueno parte mantener la salud.'
    ]
    images = [
        'https://www.thespruceeats.com/thmb/__ey243W9XIXQOboXZ8tMWzeibA=/5040x2835/smart/filters:no_upscale()/fruit-salad-98841227-5848619a5f9b5851e5f87d5c.jpg',
        'https://www.mashed.com/img/gallery/the-best-bakery-in-every-state/intro-1601499029.jpg',
        'https://loratis.files.wordpress.com/2012/01/milk-and-water.jpg',
        'https://post.healthline.com/wp-content/uploads/2020/05/woman-walking-dog-1200x628-facebook-1200x628.jpg',
        'https://morningchores.com/wp-content/uploads/2020/02/The-Difference-Between-Peas-and-Beans-and-Why-it-Matters-FB.jpg',
        'https://playswellwithbutter.com/wp-content/uploads/2021/10/Thanksgiving-Chicken-24-e1634775062172.jpg',
        'https://images.indianexpress.com/2019/12/carrots_759.jpg',
        'https://post.healthline.com/wp-content/uploads/2021/09/1389271-The-8-Best-Weightlifting-Shoes-According-to-a-Personal-Trainer-1200x628-facebook-1200x628.jpg',
        'https://media.istockphoto.com/photos/apple-juice-pouring-from-red-apples-into-a-glass-picture-id503096289?k=20&m=503096289&s=612x612&w=0&h=0Wn-pEg-r6tvjlFmgw60zp4Rzu0GaYXRotm8vhEFkU0=',
        'https://theviewfromgreatisland.com/wp-content/uploads/2018/06/Farmers-market-vegetable-salad-6117-June-21-2018.jpg'
    ]
    sentences = zip(sentences, images)
    return render_template('spanish summative.html', sentences=sentences)


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
