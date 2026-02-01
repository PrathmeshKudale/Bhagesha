import os
import random
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

# --- CONFIGURATION ---
app = Flask(__name__)
app.secret_key = 'kisan_secure_key' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///plantix_clone.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('templates', exist_ok=True)
os.makedirs('static', exist_ok=True)

db = SQLAlchemy(app)

# --- DATABASE MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(15), unique=True, nullable=False)
    name = db.Column(db.String(50), default="Farmer")

class CommunityPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(50))
    content = db.Column(db.Text)
    crop_tag = db.Column(db.String(20))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# --- MOCK DATA (No API Key Needed) ---
DISEASE_DB = [
    {"name": "Late Blight", "risk": "High", "symptoms": "Brown blotches on leaves.", "treatment_organic": "Spray Neem Oil.", "treatment_chemical": "Apply Mancozeb."},
    {"name": "Powdery Mildew", "risk": "Medium", "symptoms": "White powder on leaves.", "treatment_organic": "Milk/Water spray.", "treatment_chemical": "Sulphur fungicide."},
    {"name": "Healthy Crop", "risk": "None", "symptoms": "Green and vibrant.", "treatment_organic": "Continue care.", "treatment_chemical": "Maintain NPK."}
]

# --- ASSET GENERATOR (Creates HTML/CSS on run) ---
def create_assets():
    # 1. CSS
    css = """
    :root { --primary: #008f51; --light-bg: #f4f7f6; }
    body { font-family: sans-serif; background: var(--light-bg); padding-bottom: 70px; margin: 0; }
    .top-nav { background: var(--primary); color: white; padding: 15px; border-radius: 0 0 20px 20px; }
    .bottom-nav { position: fixed; bottom: 0; width: 100%; background: white; display: flex; justify-content: space-around; padding: 10px 0; border-top: 1px solid #ddd; }
    .nav-item { text-align: center; color: #888; text-decoration: none; font-size: 0.8rem; }
    .nav-item i { display: block; font-size: 1.4rem; margin-bottom: 2px; }
    .nav-item.active { color: var(--primary); font-weight: bold; }
    .scan-btn { background: var(--primary); color: white; width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-top: -30px; border: 4px solid white; }
    .card { background: white; border-radius: 15px; padding: 20px; margin: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .btn { background: var(--primary); color: white; border: none; padding: 12px; border-radius: 8px; width: 100%; font-size: 1rem; cursor: pointer; }
    input, select { width: 90%; padding: 10px; margin-bottom: 10px; border: 1px solid #ccc; border-radius: 5px; }
    """
    with open('static/style.css', 'w') as f: f.write(css)

    # 2. LAYOUT
    layout = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Kisan Doctor</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
    </head>
    <body>
        {% block content %}{% endblock %}
        {% if session.get('user') %}
        <div class="bottom-nav">
            <a href="{{ url_for('dashboard') }}" class="nav-item"><i class="fas fa-home"></i> Home</a>
            <a href="{{ url_for('community') }}" class="nav-item"><i class="fas fa-users"></i> Comm</a>
            <a href="{{ url_for('scan_crop') }}" class="scan-btn"><i class="fas fa-camera"></i></a>
            <a href="{{ url_for('weather') }}" class="nav-item"><i class="fas fa-cloud-sun"></i> Weather</a>
            <a href="{{ url_for('logout') }}" class="nav-item"><i class="fas fa-user"></i> Exit</a>
        </div>
        {% endif %}
    </body>
    </html>
    """
    with open('templates/layout.html', 'w') as f: f.write(layout)

    # 3. LOGIN
    login = """
    {% extends "layout.html" %}
    {% block content %}
    <div style="text-align:center; margin-top:100px;">
        <i class="fas fa-tractor fa-4x" style="color:var(--primary);"></i>
        <h2 style="color:var(--primary);">Kisan Doctor</h2>
        <form method="POST" style="margin: 30px;">
            <input type="tel" name="phone" placeholder="Mobile Number" required>
            <button type="submit" class="btn">Login</button>
        </form>
    </div>
    {% endblock %}
    """
    with open('templates/login.html', 'w') as f: f.write(login)

    # 4. DASHBOARD
    dash = """
    {% extends "layout.html" %}
    {% block content %}
    <div class="top-nav">
        <h3>👋 Namaste, Farmer</h3>
        <p>Your crops, our care.</p>
    </div>
    <div class="card" id="weather-box" style="background: linear-gradient(135deg, #008f51, #4caf50); color: white;">
        <h1 id="temp">--°C</h1>
        <p id="loc">Loading Weather...</p>
    </div>
    <div class="card" onclick="window.location='{{ url_for('scan_crop') }}'">
        <i class="fas fa-leaf fa-2x" style="color:var(--primary);"></i>
        <h3>Heal Your Crop</h3>
        <p>Take a photo to detect diseases.</p>
    </div>
    <div class="card" onclick="window.location='{{ url_for('community') }}'">
        <i class="fas fa-users fa-2x" style="color:orange;"></i>
        <h3>Community</h3>
        <p>Ask other farmers.</p>
    </div>
    <script>
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(async p => {
                const res = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${p.coords.latitude}&longitude=${p.coords.longitude}&current_weather=true`);
                const data = await res.json();
                document.getElementById('temp').innerText = data.current_weather.temperature + "°C";
                document.getElementById('loc').innerText = "Local Weather";
            });
        }
    </script>
    {% endblock %}
    """
    with open('templates/dashboard.html', 'w') as f: f.write(dash)

    # 5. SCAN & RESULT
    scan = """
    {% extends "layout.html" %}
    {% block content %}
    <div style="padding:20px; text-align:center;">
        <h2>Crop Doctor</h2>
        {% if diagnosis %}
            <div class="card" style="border: 2px solid orange;">
                <h1 style="color:var(--primary);">{{ diagnosis.name }}</h1>
                <p><strong>Risk:</strong> {{ diagnosis.risk }}</p>
                <div style="background:#fff3cd; padding:10px; margin:10px 0;">{{ diagnosis.treatment_organic }}</div>
                <a href="{{ url_for('scan_crop') }}" class="btn">Check Another</a>
            </div>
        {% else %}
            <div class="card" style="border: 2px dashed #ccc; padding: 40px;" onclick="document.getElementById('f').click()">
                <i class="fas fa-camera fa-4x" style="color:#ccc;"></i>
                <p>Tap to Upload</p>
                <form method="POST" enctype="multipart/form-data">
                    <input type="file" name="file" id="f" hidden onchange="this.form.submit()">
                </form>
            </div>
        {% endif %}
    </div>
    {% endblock %}
    """
    with open('templates/scan.html', 'w') as f: f.write(scan)

    # 6. COMMUNITY
    comm = """
    {% extends "layout.html" %}
    {% block content %}
    <div class="top-nav"><h3>Community</h3></div>
    <div style="padding:15px;">
        <form method="POST" style="display:flex; gap:5px;">
            <input type="text" name="content" placeholder="Ask a question..." required style="margin:0;">
            <button style="width:50px;"><i class="fas fa-paper-plane"></i></button>
        </form>
        {% for post in posts %}
        <div class="card" style="text-align:left; padding:15px;">
            <strong>{{ post.user_name }}</strong> <span style="float:right; color:#ccc; font-size:0.8rem;">Just now</span>
            <p>{{ post.content }}</p>
        </div>
        {% endfor %}
    </div>
    {% endblock %}
    """
    with open('templates/community.html', 'w') as f: f.write(comm)

# --- ROUTES ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form['phone']
        if not User.query.filter_by(phone=phone).first():
            db.session.add(User(phone=phone))
            db.session.commit()
        session['user'] = phone
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html') if 'user' in session else redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/weather')
def weather():
    return render_template('dashboard.html') # Re-use dash for simplicity

@app.route('/scan', methods=['GET', 'POST'])
def scan_crop():
    if 'user' not in session: return redirect(url_for('login'))
    diagnosis = None
    if request.method == 'POST':
        file = request.files.get('file')
        if file:
            # Save dummy file
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename)))
            # Mock AI Analysis
            diagnosis = random.choice(DISEASE_DB)
    return render_template('scan.html', diagnosis=diagnosis)

@app.route('/community', methods=['GET', 'POST'])
def community():
    if 'user' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        db.session.add(CommunityPost(user_name="Farmer " + session['user'][-4:], content=request.form['content']))
        db.session.commit()
    return render_template('community.html', posts=CommunityPost.query.order_by(CommunityPost.id.desc()).all())

if __name__ == '__main__':
    create_assets()
    with app.app_context(): db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
