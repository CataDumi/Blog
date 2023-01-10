from flask import Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, URL
from flask_ckeditor import CKEditor, CKEditorField
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
import datetime
from forms import CreatePostForm, UserFormRegistration, LoginUser, CommentForm
from functools import wraps
from flask import abort
from flask_gravatar import Gravatar

app = Flask(__name__)
app.app_context().push()
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

##Gravatar
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


##CONFIGURE TABLES
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))

    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    posts = relationship("BlogPost", back_populates="author")

    # "comentator" refers to the comment_author property in the Comment class.
    comments = relationship('Comment', back_populates='comentator')


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)

    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object, the "posts" refers to the posts protperty in the User class.
    author = relationship("User", back_populates="posts")

    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    ###aici fac relatie intre BlogPost-parent si Comment-child
    post = relationship('Comment', back_populates='comment')


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(250), unique=True, nullable=False)

    # "users.id" The users refers to the tablename of the Users class.
    # "comments" refers to the comments property in the User class.
    comentator_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comentator = relationship("User", back_populates='comments')

    ###aici fac relatie intre BlogPost-parent si Comment-child
    blog_id = db.Column(db.Integer, db.ForeignKey('blog_posts.id'))
    comment = relationship('BlogPost', back_populates='post')


db.create_all()

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    if current_user.is_authenticated:  ### aici vad numele utilizatorului si id-ul celui care e logat/autentificat
        print(current_user.name, current_user.id)
    return render_template("index.html", all_posts=posts)


@app.route('/register', methods=['POST', 'GET'])
def register():
    form = UserFormRegistration()
    if request.method == 'POST':
        if form.validate_on_submit():
            if User.query.filter_by(email=request.form['email']).first():
                flash('This email is already registered')
                return redirect(url_for('login'))
            new_user = User(
                name=request.form['name'],
                email=request.form['email'],
                password=generate_password_hash(request.form['password'])
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=form)


@app.route('/login', methods=['POST', 'GET'])
def login():
    form = LoginUser()
    if request.method == 'POST':
        if not User.query.filter_by(email=request.form['email']).first():
            flash("This email is not valid, please try again.")
        elif not check_password_hash(User.query.filter_by(email=request.form['email']).first().password,
                                     request.form['password']):
            flash("Wrong password, try again.")
        else:
            user = User.query.filter_by(email=request.form['email']).first()
            # print(current_user)
            login_user(user)
            return redirect(url_for('get_all_posts'))

    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=['POST', 'GET'])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    form = CommentForm()
    if request.method == "POST":
        if form.validate_on_submit():
            # print(form.comment.data)
            if current_user.is_authenticated:
                new_comment = Comment(text=form.comment.data,
                                      comentator_id=current_user.id,
                                      blog_id=post_id

                                      )
                db.session.add(new_comment)
                db.session.commit()
            else:
                flash('You are not logged in')
                return redirect(url_for('login'))

    # print(requested_post.post)  ### aici tratez comentariile de la ficare postare drept un atribut al clasei BlogPost
    print(Comment.query.all()[1].comentator_id)  ### aici sunt toate atributele(comentariile) de la toate postarile
    # print(requested_post.author)
    return render_template("post.html",
                           post=requested_post,
                           form=form,
                           comments=requested_post.post,
                           gravatar=gravatar,
                           )


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


###decorator for admin only pages
def only_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            # If id is not 1 then return abort with 403 error
            return abort(403)
        # Otherwise continue with the route function
        return f(*args, **kwargs)

    return decorated_function


@app.route("/new-post", methods=['POST', 'GET'])
@login_required
@only_admin
def add_new_post():
    form = CreatePostForm()
    text = 'New post'

    if request.method == 'POST':

        if form.validate_on_submit():
            ###aici scot toate caracteristicile cp din wtform
            # print(form.title.data)
            # print(form.subtitle.data)
            # print(form.author.data)
            # print(form.img_url.data)
            print(form.body.data, type(form.body.data))
            date = datetime.datetime.now().strftime("%B %d, %Y")

            ###aici introduc caracteristicile din form intr o inregistrare in db

            new_item = BlogPost(
                title=form.title.data,
                subtitle=form.subtitle.data,
                date=date,
                body=form.body.data,
                author=current_user,
                img_url=form.img_url.data

            )

            db.session.add(new_item)
            db.session.commit()

            return redirect(url_for('get_all_posts'))

    return render_template('make-post.html', form=form, text=text)


@app.route("/edit-post<int:post_id>", methods=['POST', 'GET'])
@login_required
@only_admin
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=current_user,
        body=post.body
    )
    if request.method == 'POST':
        if edit_form.validate_on_submit():
            post.title = edit_form.title.data
            post.subtitle = edit_form.subtitle.data
            post.img_url = edit_form.img_url.data
            # post.author = edit_form.author.data ####bucata asta o scot ca mi da eroate ca nu stie cine e post.author in db BlogPost
            post.body = edit_form.body.data
            db.session.commit()
            return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@only_admin
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
