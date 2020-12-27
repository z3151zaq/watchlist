from flask import Flask, url_for, escape,render_template

app = Flask(__name__)

name = "xny"
movies = [
    {"title": "My Neighbor Totoro", "year": "1988"},
    {"title": "Dead Poets Society", "year": "1989"},
    {"title": "A Perfect World", "year": "1993"},
    {"title": "Leon", "year": "1994"},
    {"title": "Mahjong", "year": "1996"},
    {"title": "Swallowtail Butterfly", "year": "1996"},
    {"title": "King of Comedy", "year": "1999"},
    {"title": "Devils on the Doorstep", "year": "1999"},
    {"title": "WALL-E", "year": "2008"},
    {"title": "The Pork of Music", "year": "2012"},
]


@app.route("/<name>")
@app.route("/index")
@app.route("/home")
def hello():
    return "<h1>Hello Totoro!</h1><img src='http://helloflask.com/totoro.gif'>"

@app.route("/")
def index():
    return render_template('index.html', name=name, movies=movies)