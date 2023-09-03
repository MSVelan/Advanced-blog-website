from flask import Flask, render_template, redirect, url_for, flash, abort, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from flask_mail import Mail, Message
from functools import wraps
import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRETKEY")
app.config['MAIL_SERVER'] = "smtp.googlemail.com"
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_DEFAULT_SENDER']=os.environ.get("MYEMAIL")
app.config['MAIL_USERNAME'] = os.environ.get("SECONDARYEMAIL")
app.config['MAIL_PASSWORD'] = os.environ.get("MAILPASSWORD")

mail = Mail(app)

ckeditor = CKEditor(app)
Bootstrap(app)

gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

login_manager = LoginManager()
login_manager.init_app(app)

##CONNECT TO DB
currDir = os.path.dirname(__file__)
fullPath1 = os.path.join(currDir,"blog.db")
app.config['SQLALCHEMY_DATABASE_URI']="sqlite:///"+fullPath1
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


def admin_only(f):
    @wraps(f)
    def decorated_function(*args,**kwargs):
        if current_user.id!=1:
            abort(403) 

        return f(*args,**kwargs)
    return decorated_function



##CONFIGURE TABLES

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)

    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")

    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments = relationship("Comment", back_populates="parent_post")

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    posts = relationship("BlogPost",back_populates="author")
    comments = relationship("Comment", back_populates="author")
    
    def __init__(self, name, email, password):
        self.name = name
        self.email = email
        self.password = password

class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = relationship("User", back_populates="comments")
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")

    def __init__(self, text, post):
        self.text = text
        self.author = current_user
        self.parent_post = post

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/', methods=["GET","POST"])
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)

def validate_email(email):
    user = db.session.query(User).filter_by(email=email).first()
    if(user):
        return True
    return False

@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
            email = form.email.data
            name = form.name.data
            password = form.password.data

            if(validate_email(email)):
                flash("You've already signed up with that email, log in instead!")
                return redirect(url_for("login"))

            passwordHash = generate_password_hash(password,"pbkdf2:sha256",8)
            new_user = User(name,email,passwordHash)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for("get_all_posts"))
    return render_template("register.html", form=form)


@app.route('/login', methods=["GET","POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = db.session.query(User).filter_by(email=email).first()
        if(user):
            if(check_password_hash(user.password,password)):
                login_user(user)
                return redirect(url_for("get_all_posts"))
            else:
                flash("Incorrect Password!")
        else:
            flash("Email is not registered!")

    return render_template("login.html", form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>",methods=["GET","POST"])
def show_post(post_id):
    
    form = CommentForm()
    requested_post = BlogPost.query.get(post_id)
    if form.validate_on_submit():
        if(current_user.is_authenticated):
            comment_text = form.comment_text.data
            new_comment = Comment(comment_text, requested_post)
            db.session.add(new_comment)
            db.session.commit()
        else:
            flash("Login Required")
            return redirect(url_for("login"))
    
    comments_on_post = db.session.query(Comment).filter_by(post_id=post_id).all()
    return render_template("post.html", post=requested_post, form=form, comments=comments_on_post)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact", methods=["GET","POST"])
def contact():
    if(request.method=="POST"):
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        msg = request.form.get("message")

        msg_title = "User from Blog Post project contacting..."
        sender = email
        adminEmail = "muthiahsivavelan2026@gmail.com"
        data = {
            "app_name": "MSV Blog",
            "user_name": name,
            "user_email": email,
            "user_phNo": phone,
            "user_message": msg
        }
        msg_body = "An user is trying to reach out.. check the below data for info\n"
        message = Message(subject=msg_title,recipients=[adminEmail],sender=sender,body=msg_body)

        message.html = render_template("email.html",data=data)
        try:
            mail.send(message)
            flash("Email sent..")
        except Exception as e:
            print(e)
            flash("Error occurred, the email wasn't sent\n\n{e}")
            
        return redirect(url_for("contact"))
        
    return render_template("contact.html")


@app.route("/new-post", methods=["GET","POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            author_id=current_user.id,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", methods=["GET","POST"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        author_id = post.author_id,
        body=post.body,
        date = post.date
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))

@app.route("/sendmail", methods=["GET","POST"])
def sendMail():
    if(request.method=="POST"):
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        msg = request.form.get("message")

        print(name)
        print(email)
        print(phone)
        print(msg)

        msg_title = "User from Blog Post project contacting..."
        sender = email
        adminEmail = "muthiahsivavelan2026@gmail.com"
        data = {
            "app_name": "MSV Blog",
            "user_name": name,
            "user_email": email,
            "user_phNo": phone,
            "user_message": msg
        }
        msg_body = "An user is trying to reach out.. check the below data for info\n"
        message = Message(subject=msg_title,recipients=[adminEmail],sender=sender,body=msg_body)

        message.html = render_template("email.html",data=data)
        try:
            mail.send(message)
            return "Email sent.."
        except Exception as e:
            print(e)
            return f"Error occurred, the email wasn't sent\n{e}"


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False)
