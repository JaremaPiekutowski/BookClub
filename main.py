# TODO - v3.0:
#  Add user ranking
#  Add table sorting and filtering - dropdown
#  Add book search - form
#  Add user stats - form + search
#  Add book adding - dropdown for genre
#  Book adding - add new user
#  Make the table more responsive - add column labels in small version https://css-tricks.com/responsive-data-tables

# TODO - v4.0:
#  Logging in


# DONE:
#  Create basic frontend for the app (index.html)
#  Create database - Pandas
#  Book display - table
#  Better book display. Make the table responsive: https://css-tricks.com/responsive-data-tables
#  Book adding - form
#  Add book ID (index)
#  Adding book_database - dropdown with users and genre
#  Table sorting with Polish letters
#  FIXED: Table sorting
#  Add info that a book's been added BELOW the form - add.html/main.py
#  Prevent adding the same book another time (check [author and title] duplicates)
#  Installed and imported firebase (NO COMMIT YET)
#  Created a firebase of books
#  Complete migration to Firebase
#  Security issue 1: Flask SECRET_KEY to env
#  Adding books to firebase
#  Replace "1899-12-31" by "brak"
#  Book add route: date to serial number
#  Authentication to env/Heroku config variables
#  Heroku deployment
#  Heroku config vars setting: https://devcenter.heroku.com/articles/config-vars


import os
import json
from flask import Flask, render_template, redirect, url_for
from flask_wtf import FlaskForm
import wtforms
from wtforms.validators import DataRequired
import pandas as pd
import datetime as dt
import functools
import locale
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import xlrd

# Set locale
locale.setlocale(locale.LC_ALL, '')


# Set Firebase credentials
my_credentials = {
    "type": "service_account",
    "project_id": "bookclub-b2db5",
    "private_key_id": os.environ.get("PRIVATE_KEY_ID"),
    "private_key": os.environ.get("PRIVATE_KEY").replace(r'\n', '\n'),
    "client_email": os.environ.get("CLIENT_EMAIL"),
    "client_id": os.environ.get("CLIENT_ID"),
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-teiie%40bookclub-b2db5.iam.gserviceaccount.com"}

cred = credentials.Certificate(my_credentials)

# Initialize app
firebase_admin.initialize_app(cred, {'databaseURL': 'https://bookclub-b2db5-default-rtdb.europe-west1.firebasedatabase.app/'})

# Set reference to the database
REF = db.reference("/books")

# APP
# Create the app
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FORM_SECRET_KEY")


# Get book_database
def get_books() -> pd.DataFrame:
    # Get data
    data = REF.get()
    all_books = pd.DataFrame()
    if isinstance(data, list):
        all_books = pd.DataFrame(data[1:])
    elif isinstance(data, dict):
        all_books = pd.DataFrame([value for key, value in data.items()])
    # Clean the data, dealing with ''
    all_books['data'] = [upload_date if len(str(upload_date)) == 5 else 0 for upload_date in all_books['data']]
    # Convert serial number to date
    all_books['data'] = [xlrd.xldate_as_datetime(upload_date, 0).date() for upload_date in all_books['data']]
    all_books['tytul'] = all_books['tytul'].astype(str)
    return all_books


# Get users
def get_users() -> list:
    return sorted(get_books()['wrzucajacy'].dropna().unique().tolist())


# Prepare data to display
def prepare_to_display(data: pd.DataFrame) -> dict:
    data_to_display = data.fillna(value="brak").iloc[:, :7].drop_duplicates(subset='tytul').copy()
    data_to_display = data_to_display.set_index('tytul')
    data_to_display['data'] = [upload_date if upload_date > dt.date(1900, 1, 1) else "brak" for upload_date in data_to_display['data']]
    data_to_display = data_to_display.reindex(sorted(data_to_display.index,
                                                     key=functools.cmp_to_key(locale.strcoll))).reset_index()
    data_to_display = data_to_display.iloc[:, [0, 1, 2, 3, 5, 4]]
    print(data_to_display.columns)
    return {'columns': ['Tytuł', 'Autor', 'Data', 'Dziedzina', 'Wrzucający/a', 'Recenzja'],
            'values': data_to_display.values.tolist()}


# Get users who didn't add a book in current half-year
def get_users_to_warn(book_database: pd.DataFrame):
    current_month = dt.datetime.now().month
    current_year = dt.datetime.now().year
    start_month = 7 if current_month > 6 else 1
    start_date = dt.date(current_year, start_month, 1)
    all_users = book_database.dropna(subset=['wrzucajacy'], axis=0)['wrzucajacy'].unique()
    current_halfyear_data = book_database[book_database['data'] > start_date]
    current_halfyear_users = current_halfyear_data['wrzucajacy'].unique()
    raw_users = [user for user in all_users if user not in current_halfyear_users]
    users_to_warn = sorted([str(user) for user in raw_users])
    return users_to_warn


# Get newest book_database
def get_newest_books(book_database: pd.DataFrame):
    return book_database.sort_values(by='data', axis=0, ascending=False).head()[['tytul', 'autor']].values


# Date to serial number for feeding JSON
def serialize_date(date: dt.datetime):
    temp = dt.datetime(1899, 12, 30)
    delta = date - temp
    return int(float(delta.days) + (float(delta.seconds) / 86400))


# Book adding form
class BookForm(FlaskForm):
    author = wtforms.StringField(label='Autor')
    title = wtforms.StringField(label='Tytuł', validators=[DataRequired(message="Proszę wypełnić pole")])
    genre = wtforms.StringField(label='Dziedzina (np. powieść, poezja)')
    user = wtforms.SelectField(label='Wrzucający', choices=get_users())
    review = wtforms.StringField(label='Recenzja (link)')
    submit = wtforms.SubmitField(label="Dodaj")


# ROUTES
# Home route
@app.route('/')
def home():
    return render_template('index.html',
                           newest_books=get_newest_books(get_books()),
                           users_to_warn=get_users_to_warn(get_books()))


# Book view route
@app.route('/books')
def books():
    return render_template('books.html',
                           books=prepare_to_display(get_books())['values'],
                           columns=prepare_to_display(get_books())['columns'])


# Book add route
@app.route('/add', methods=['GET', 'POST'])
def submit_book():
    # Instantiate BookForm class
    form = BookForm()
    # Get book_database for checking
    book_database = get_books()
    # Validate the form
    if form.validate_on_submit():
        if form.author.data in book_database['autor'].values and \
                form.title.data in book_database['tytul'].values:
            return render_template('add.html', form=form, info='Ta książka już jest w bazie')
        else:
            new_book = {'autor': form.author.data,
                        'data': serialize_date(dt.datetime.now()),
                        'dziedzina': form.genre.data,
                        'recenzja': form.review.data,
                        'tytul': form.title.data,
                        'wrzucajacy': form.user.data}
            REF.push(new_book)
        return redirect(url_for('home'))
    # Render template
    return render_template('add.html', form=form, info='')


# Book search route
@app.route('/search')
def search_book():
    return render_template('search.html')


# Stats route
@app.route('/stats')
def stats():
    return render_template('stats.html')


# Ranking route
@app.route('/ranking')
def ranking():
    return render_template('ranking.html')


# RUN
if __name__ == "__main__":
    app.run(debug=False)
