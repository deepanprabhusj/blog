from flask import Flask, render_template, redirect, url_for, flash,abort
from flask_pymongo import PyMongo
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from forms import PostForm, RegistrationForm, LoginForm
import markdown
from bson.objectid import ObjectId  # Import ObjectId for MongoDB

app = Flask(__name__)
app.config.from_object('config.Config')

# Debug print to check if the configuration is loaded properly
print("MONGO_URI:", app.config['MONGO_URI'])  # Debug print

mongo = PyMongo(app)  # Initialize PyMongo
print("Mongo initialized:", mongo)  # Debug print

login_manager = LoginManager(app)

@login_manager.user_loader
def load_user(user_id):
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})  # Convert user_id to ObjectId
    return User(user['username'], user['email'], user['password'], user['_id']) if user else None

class User(UserMixin):
    def __init__(self, username, email, password, user_id):
        self.username = username
        self.email = email
        self.password = password
        self.id = user_id

@app.route('/')
def index():
    try:
        posts = list(mongo.db.posts.find())  # This line retrieves posts from MongoDB
        return render_template('index.html', posts=posts)
    except Exception as e:
        print("Error retrieving posts:", str(e))  # Debug print for error
        flash('An error occurred while retrieving posts.', 'danger')
        return render_template('index.html', posts=[])

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        existing_user = mongo.db.users.find_one({"email": form.email.data})
        if existing_user:
            flash('Email address already exists.', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(form.password.data)
        mongo.db.users.insert_one({
            "username": form.username.data,
            "email": form.email.data,
            "password": hashed_password
        })
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = mongo.db.users.find_one({"email": form.email.data})
        if user and check_password_hash(user['password'], form.password.data):
            login_user(User(user['username'], user['email'], user['password'], user['_id']))
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        flash('Login unsuccessful. Check email and password', 'danger')
    return render_template('login.html', form=form)

@app.route('/create_post', methods=['GET', 'POST'])
@login_required
def create_post():
    form = PostForm()
    if form.validate_on_submit():
        tags = form.tags.data.split(',') if form.tags.data else []
        mongo.db.posts.insert_one({
            "title": form.title.data,
            "content": form.content.data,
            "user_id": current_user.id,
            "tags": tags
        })
        flash('Post created successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('create_post.html', form=form)
@app.route('/post/<post_id>')
def view_post(post_id):
    try:
        # Convert post_id to ObjectId
        post = mongo.db.posts.find_one({"_id": ObjectId(post_id)})
    except Exception as e:
        print(f"Error retrieving post: {e}")  # Log any error
        flash('Post not found.', 'danger')
        return redirect(url_for('index'))

    if post is None:
        flash('Post not found.', 'danger')
        return redirect(url_for('index'))

    # Retrieve the author's details using the user_id from the post
    author = mongo.db.users.find_one({"_id": post['user_id']}) if 'user_id' in post else None
    
    # Convert Markdown content to HTML
    post['content'] = markdown.markdown(post['content'])  
    return render_template('view_post.html', post=post, author=author)
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
