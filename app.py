from flask import Flask, url_for, escape, render_template, request, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)
import os
import sys
import click

WIN = sys.platform.startswith("win")
if WIN:  # 如果是 Windows 系统，使用三个斜线
    prefix = "sqlite:///"
else:  # 否则使用四个斜线
    prefix = "sqlite:////"

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev"
app.config["SQLALCHEMY_DATABASE_URI"] = prefix + os.path.join(app.root_path, "data.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False  # 关闭对模型修改的监控
# 在扩展类实例化前加载配置
db = SQLAlchemy(app)
# 实例化用户认证拓展类
login_manager = LoginManager(app)
login_manager.login_view = "please login"


@login_manager.user_loader
def load(user_id):
    user = User.query.get(int(user_id))
    return user


class User(db.Model, UserMixin):  # 表名将会是 user（自动生成，小写处理）
    id = db.Column(db.Integer, primary_key=True)  # 主键
    name = db.Column(db.String(20))  # 名字
    username = db.Column(db.String(20))  # 用户名
    password_hash = db.Column(db.String(128))  # 密码散列值

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def validate_password(self, password):
        return check_password_hash(self.password_hash, password)


class Movie(db.Model):  # 表名将会是 movie
    id = db.Column(db.Integer, primary_key=True)  # 主键
    title = db.Column(db.String(60))  # 电影标题
    year = db.Column(db.String(4))  # 电影年份


@app.cli.command()  # 注册为命令
@click.option("--drop", is_flag=True, help="Create after drop.")  # 设置选项
def initdb(drop):
    """Initialize the database."""
    if drop:  # 判断是否输入了选项
        db.drop_all()
    db.create_all()
    click.echo("Initialized database.")  # 输出提示信息


@app.cli.command()
def forge():
    """Generate fake data."""
    db.create_all()

    # 全局的两个变量移动到这个函数内
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

    for m in movies:
        movie = Movie(title=m["title"], year=m["year"])
        db.session.add(movie)

    db.session.commit()
    click.echo("Done.")


@app.context_processor
def inject_user():
    user = User.query.first()
    return dict(user=user)


@app.errorhandler(404)
def page_not_found(e):  # 接受异常对象
    return render_template("404.html")


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":  # 判断是否是POST请求
        if not current_user.is_authenticated:
            return redirect(url_for("index"))
        # 获取表单数据
        title = request.form.get("title")
        year = request.form.get("year")
        # 验证数据
        if not title or not year or len(year) != 4 or len(title) > 60:
            flash("输入错误，年份必须完整，题目不能超过60个字符")
            return redirect(url_for("index"))
        movie = Movie(title=title, year=year)
        db.session.add(movie)
        db.session.commit()
        flash("创建成功")
        return redirect(url_for("index"))

    movies = Movie.query.all()
    return render_template("index.html", movies=movies)


@app.route("/movie/edit/<int:movie_id>", methods=["GET", "POST"])
@login_required
def edit(movie_id):
    movie = Movie.query.get_or_404(movie_id)

    if request.method == "POST":  # 处理编辑表单的提交请求
        title = request.form["title"]
        year = request.form["year"]

        if not title or not year or len(year) != 4 or len(title) > 60:
            flash("输入错误，年份必须完整，题目不能超过60个字符")
            return redirect(url_for("edit", movie_id=movie_id))  # 重定向回对应的编辑页面

        movie.title = title  # 更新标题
        movie.year = year  # 更新年份
        db.session.commit()  # 提交数据库会话
        flash("更新成功")
        return redirect(url_for("index"))  # 重定向回主页

    return render_template("edit.html", movie=movie)  # 传入被编辑的电影记录


@app.route("/movie/delete/<int:movie_id>", methods=["POST"])
@login_required
def delete(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    db.session.delete(movie)
    db.session.commit()
    flash("删除成功")
    return redirect(url_for("index"))


@app.cli.command()
@click.option("--username", prompt=True, help="The username used to login.")
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    help="The password used to login.",
)
def admin(username, password):
    """Create user."""
    db.create_all()

    user = User.query.first()
    if user is not None:
        click.echo("Updating user...")
        user.username = username
        user.set_password(password)  # 设置密码
    else:
        click.echo("Creating user...")
        user = User(username=username, name="Admin")
        user.set_password(password)  # 设置密码
        db.session.add(user)

    db.session.commit()  # 提交数据库会话
    click.echo("Done.")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if not username or not password:
            flash("Invalid input.")
            return redirect(url_for("login"))

        user = User.query.first()
        # 验证用户名和密码是否一致
        if username == user.username and user.validate_password(password):
            login_user(user)  # 登入用户
            flash("Login success.")
            return redirect(url_for("index"))  # 重定向到主页

        flash("Invalid username or password.")  # 如果验证失败，显示错误消息
        return redirect(url_for("login"))  # 重定向回登录页面

    return render_template("login.html")


@app.route("/logout")
@login_required  # 用于视图保护，后面会详细介绍
def logout():
    logout_user()  # 登出用户
    flash("Goodbye.")
    return redirect(url_for("index"))  # 重定向回首页


@login_required
@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        name = request.form["name"]

        if not name or len(name) > 20:
            flash("Invalid input.")
            return redirect(url_for("settings"))

        current_user.name = name
        # current_user 会返回当前登录用户的数据库记录对象
        # 等同于下面的用法
        # user = User.query.first()
        # user.name = name
        db.session.commit()
        flash("Settings updated.")
        return redirect(url_for("index"))

    return render_template("settings.html")
