# TODO - v1.0:
#  Testing

# TODO - v2.0:
#  User ranking
#  Table sorting and filtering - dropdown
#  Book search - form
#  User stats - form + search
#  Book adding - dropdown for genre
#  Book adding - add new user
#  Better responsive table - column labels
#  Database to SQL?

# DONE:
#  Create basic frontend for the app (index.html)
#  Create database - Pandas
#  Book display - table
#  Better book display. Make the table responsive: https://css-tricks.com/responsive-data-tables
#  Book adding - form
#  Add book ID (index)
#  Adding books - dropdown with users and genre
#  Table sorting with Polish letters

from flask import Flask, render_template, request, redirect, url_for
from flask_wtf import FlaskForm
import wtforms
from wtforms.validators import DataRequired
import pandas as pd
import datetime as dt
import functools
import locale


# Set locale
locale.setlocale(locale.LC_ALL, '')

# APP
# Create the app
app = Flask(__name__)
app.config["SECRET_KEY"] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'


# Get books
def get_books() -> pd.DataFrame:
    data = pd.read_excel("static/data/bookdata.xlsx", index_col=0)
    data['Tytuł'] = data['Tytuł'].astype(str)
    data['Data'] = pd.to_datetime(data['Data']).dt.date
    return data


# Get users
def get_users() -> list:
    return sorted(get_books()['Wrzucający'].dropna().unique().tolist())


# Prepare data to display
def prepare_to_display(data):
    data_to_display = data.fillna(value="brak").iloc[:,:7].drop_duplicates(subset='Tytuł').copy()
    data_to_display = data_to_display.set_index('Tytuł')
    data_to_display = data_to_display.reindex(sorted(data_to_display.index, key=functools.cmp_to_key(locale.strcoll))).reset_index()
    return {'columns': data.columns, 'values': data.values.tolist()}


# Add book
def add_book(book):
    data = pd.read_excel("static/data/bookdata.xlsx", index_col=0)
    data.loc[len(data)+1] = book
    data.to_excel("static/data/bookdata.xlsx")


# Get users who didn't add a book in current half-year
def get_users_to_warn(books: pd.DataFrame):
    current_month = dt.datetime.now().month
    current_year = dt.datetime.now().year
    start_month = 7 if current_month > 6 else 1
    start_date = dt.date(current_year, start_month, 1)
    all_users = books.dropna(subset=['Wrzucający'], axis=0)['Wrzucający'].unique()
    current_halfyear_data = books[books['Data'] > start_date]
    current_halfyear_users = current_halfyear_data['Wrzucający'].unique()
    raw_users = [user for user in all_users if user not in current_halfyear_users]
    users_to_warn = sorted([str(user) for user in raw_users])
    return users_to_warn


# Get newest books
def get_newest_books(books: pd.DataFrame):
    return books.sort_values(by='Data', axis=0, ascending=False).head()[['Tytuł', 'Autor']].values


# Book adding form
class BookForm(FlaskForm):
    author = wtforms.StringField(label='Autor (nazwisko, imię)')
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
                           newest_books = get_newest_books(get_books()),
                           users_to_warn = get_users_to_warn(get_books()))


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
    # Validate the form
    if form.validate_on_submit():
        new_book = [form.author.data,
                    form.title.data,
                    form.genre.data,
                    form.user.data,
                    dt.datetime.now().date(),
                    form.review.data]
        add_book(new_book)
        return render_template('add.html', form=form, info=f'Dodano książkę pt. {form.title.data}')
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
