import os
import random
import time
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

# --- CONFIGURATION ---
app = Flask(__name__)
app.secret_key = 'kisan_secure_key' # Keep this secret
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

# --- MOCK DATA FOR "NO API" AI ---
# This mimics the Plantix AI database
DISEASE_DB = [
    {
        "name": "Late Blight",
        "crop": "Tomato/Potato",
        "symptoms": "Brown blotches on leaves, white mold on undersides.",
        "treatment_organic": "Spray Neem Oil or Copper Fungicide.",
        "treatment_chemical": "Apply Mancozeb every 7 days.",
        "risk": "High"
    },
    {
        "name": "Powdery Mildew",
        "crop": "Vegetables",
        "symptoms": "White flour-like powder on leaves.",
        "treatment_organic": "Mix milk and water (1:10) and spray.",
        "treatment_chemical": "Use Sulphur-based fungicides.",
        "risk": "Medium"
    },
    {
        "name": "Stem Borer",
        "crop": "Rice/Maize",
        "symptoms": "Holes in stems, drying of central shoot.",
        "treatment_organic": "Install Pheromone traps.",
        "treatment_chemical": "Apply Cartap Hydrochloride granules.",
        "risk": "High"
    },
    {
        "name": "Healthy Crop",
        "crop": "General",
        "symptoms": "Leaves are green and vibrant. No spots.",
        "treatment_organic": "Continue usage of Jeevamrut.",
        "treatment_chemical": "Maintain NPK balance.",
        "risk": "None"
    }
]

# --- HTML/CSS GENERATOR (APP BUILDER) ---
def create_assets():
    # 1. CSS (Plantix Style - Green & Clean)
    css = """
    :root {
        --primary: #008f51; /* Plantix Green */
        --dark: #00361f;
        --light-bg: #f4f7f6;
        --accent: #ffc107;
    }
    body { font-family: 'Roboto', sans-serif; background: var(--light-bg); padding-bottom: 70px; }
    
    /* Navbar */
    .top-nav { background: var(--primary); color: white; padding: 15px; border-radius: 0 0 20px 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
    
    /* Bottom Nav (App Feel) */
    .bottom-nav {
        position: fixed; bottom: 0; width: 100%; background: white;
        display: flex; justify-content: space-around; padding: 10px 0;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.1); z-index: 1000;
    }
    .nav-item { text-align: center; color: #888; text-decoration: none; font-size: 0.8rem; }
    .nav-item i { font-size: 1.4rem; display: block; margin-bottom: 2px; }
    .nav-item.active { color: var(--primary); font-weight: bold; }
    
    /* Center Scan Button */
    .scan-btn {
        background: var(--primary); color: white; width: 65px; height: 65px;
        border-radius: 50%; display: flex; align-items: center; justify-content: center;
        margin-top: -35px; border: 5px solid white; box-shadow: 0 4px 10px rgba(0,00,0,0.2);
    }
    
    /* Cards */
    .custom-card { border: none; border-radius: 15px; background: white; box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 15px; overflow: hidden; }
    .weather-card { background: linear-gradient(135deg, #008f51, #4caf50); color: white; }
    
    /* Animations */
    .scanner-line {
        height: 2px; width: 100%; background: #00ff00;
        position: absolute; top: 0; animation: scan 2s infinite;
    }
    @keyframes scan { 0% {top:0} 50% {top:100%} 100% {top:0} }
    """
    with open('static/style.css', 'w') as f: f.write(css)

    # 2. MASTER LAYOUT
    layout = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
        <title>Kisan Doctor</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
    </head>
    <body>
        {% block content %}{% endblock %}
        
        {% if session.get('user') %}
        <div class="bottom-nav">
            <a href="{{ url_for('dashboard') }}" class="nav-item {% if active=='home' %}active{% endif %}">
                <i class="fas fa-home"></i> Home
            </a>
            <a href="{{ url_for('community') }}" class="nav-item {% if active=='comm' %}active{% endif %}">
                <i class="fas fa-users"></i> Community
            </a>
            <a href="{{ url_for('scan_crop') }}" class="scan-btn">
                <i class="fas fa-camera fa-lg"></i>
            </a>
            <a href="{{ url_for('weather') }}" class="nav-item {% if active=='weather' %}active{% endif %}">
                <i class="fas fa-cloud-sun"></i> Weather
            </a>
            <a href="{{ url_for('logout') }}" class="nav-item">
                <i class="fas fa-user"></i> Profile
            </a>
        </div>
        {% endif %}
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
        {% block scripts %}{% endblock %}
    </body>
    </html>
    """
    with open('templates/layout.html', 'w') as f: f.write(layout)

    # 3. LOGIN PAGE
    login = """
    {% extends "layout.html" %}
    {% block content %}
    <div class="container d-flex flex-column justify-content-center align-items-center" style="height:100vh; background:white;">
        <img src="https://img.icons8.com/fluency/96/tractor.png" alt="Logo">
        <h2 class="mt-3 text-success fw-bold">Kisan Doctor</h2>
        <p class="text-muted">Heal your crop, improve your yield.</p>
        
        <form method="POST" class="w-100 p-4">
            <div class="mb-3">
                <label class="form-label fw-bold">Mobile Number</label>
                <input type="tel" name="phone" class="form-control form-control-lg" placeholder="98765xxxxx" required>
            </div>
            <button type="submit" class="btn btn-success w-100 btn-lg rounded-pill shadow">Login / Signup</button>
        </form>
    </div>
    {% endblock %}
    """
    with open('templates/login.html', 'w') as f: f.write(login)

    # 4. DASHBOARD (HOME)
    dash = """
    {% extends "layout.html" %}
    {% block content %}
    <div class="top-nav">
        <div class="d-flex justify-content-between align-items-center">
            <h4 class="m-0">👋 Hello, Farmer</h4>
            <span class="badge bg-light text-success">Online</span>
        </div>
    </div>

    <div class="container mt-3">
        <div class="custom-card weather-card p-3" id="weather-box">
            <div class="d-flex justify-content-between">
                <div>
                    <h2 class="m-0" id="temp">--°C</h2>
                    <p class="m-0" id="city">Locating...</p>
                </div>
                <i class="fas fa-cloud-sun fa-3x"></i>
            </div>
        </div>

        <h5 class="fw-bold text-secondary mt-4">Your Tools</h5>
        <div class="row g-3">
            <div class="col-6">
                <a href="{{ url_for('scan_crop') }}" class="text-decoration-none">
                    <div class="custom-card p-3 text-center">
                        <i class="fas fa-leaf fa-2x text-success mb-2"></i>
                        <h6 class="text-dark">Heal Crop</h6>
                    </div>
                </a>
            </div>
            <div class="col-6">
                <div class="custom-card p-3 text-center">
                    <i class="fas fa-calculator fa-2x text-warning mb-2"></i>
                    <h6 class="text-dark">Fertilizer Calc</h6>
                </div>
            </div>
            <div class="col-6">
                <a href="{{ url_for('community') }}" class="text-decoration-none">
                    <div class="custom-card p-3 text-center">
                        <i class="fas fa-comments fa-2x text-primary mb-2"></i>
                        <h6 class="text-dark">Community</h6>
                    </div>
                </a>
            </div>
            <div class="col-6">
                <div class="custom-card p-3 text-center">
                    <i class="fas fa-store fa-2x text-danger mb-2"></i>
                    <h6 class="text-dark">Mandi Rates</h6>
                </div>
            </div>
        </div>
        
        <h5 class="fw-bold text-secondary mt-4">Trending Tips</h5>
        <div class="custom-card p-3 d-flex align-items-center">
            <img src="https://img.icons8.com/color/48/wheat.png" class="me-3">
            <div>
                <h6 class="m-0 fw-bold">Protect Wheat</h6>
                <small class="text-muted">Irrigate within 20 days of sowing.</small>
            </div>
        </div>
    </div>

    <script>
        // Open-Meteo Free Weather Logic
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(async position => {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                // Fetch from Open-Meteo (No Key Required)
                const res = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current_weather=true`);
                const data = await res.json();
                document.getElementById('temp').innerText = data.current_weather.temperature + "°C";
                document.getElementById('city').innerText = "Local Farm Area";
            });
        }
    </script>
    {% endblock %}
    """
    with open('templates/dashboard.html', 'w') as f: f.write(dash)

    # 5. SCAN/DETECT PAGE (The "Plantix" Core)
    scan = """
    {% extends "layout.html" %}
    {% block content %}
    <div class="container mt-4 text-center">
        <h3 class="fw-bold text-success">Crop Doctor</h3>
        <p class="text-muted">Take a photo of the affected leaf</p>

        <form action="{{ url_for('analyze') }}" method="POST" enctype="multipart/form-data" id="scanForm">
            <div class="custom-card p-5 border border-success border-2 border-dashed" onclick="document.getElementById('fileIn').click()">
                <i class="fas fa-camera fa-4x text-success"></i>
                <p class="mt-2 fw-bold">Tap to Upload Photo</p>
                <input type="file" name="file" id="fileIn" hidden accept="image/*" onchange="previewImage(this)">
            </div>
            <img id="preview" src="#" style="max-width:100%; display:none; border-radius:15px;" class="mb-3">
            
            <div id="loading" style="display:none;" class="mt-3">
                <div class="spinner-border text-success" role="status"></div>
                <p>Analyzing leaf patterns...</p>
            </div>
        </form>
    </div>

    <script>
        function previewImage(input) {
            if (input.files && input.files[0]) {
                var reader = new FileReader();
                reader.onload = function(e) {
                    document.getElementById('preview').src = e.target.result;
                    document.getElementById('preview').style.display = 'block';
                    // Auto submit after 1 second for effect
                    document.getElementById('loading').style.display = 'block';
                    setTimeout(() => document.getElementById('scanForm').submit(), 1500);
                }
                reader.readAsDataURL(input.files[0]);
            }
        }
    </script>
    {% endblock %}
    """
    with open('templates/scan.html', 'w') as f: f.write(scan)

    # 6. RESULT PAGE
    result = """
    {% extends "layout.html" %}
    {% block content %}
    <div class="container mt-4">
        <a href="{{ url_for('scan_crop') }}" class="text-decoration-none text-secondary"><i class="fas fa-arrow-left"></i> Back</a>
        
        <div class="custom-card p-0 mt-3">
            <div style="background: #ffc107; padding: 20px; text-align: center;">
                <h1 class="display-4 fw-bold">{{ diagnosis.confidence }}%</h1>
                <p class="fw-bold text-dark">Match Confidence</p>
            </div>
            <div class="p-4">
                <h2 class="text-success fw-bold">{{ diagnosis.name }}</h2>
                <span class="badge bg-danger mb-3">{{ diagnosis.risk }} Risk</span>
                
                <h5 class="mt-3"><i class="fas fa-search-plus"></i> Symptoms</h5>
                <p class="text-muted">{{ diagnosis.symptoms }}</p>
                <hr>
                
                <h5 class="mt-3 text-primary"><i class="fas fa-leaf"></i> Organic Treatment</h5>
                <div class="alert alert-success">{{ diagnosis.treatment_organic }}</div>
                
                <h5 class="mt-3 text-danger"><i class="fas fa-flask"></i> Chemical Control</h5>
                <div class="alert alert-secondary">{{ diagnosis.treatment_chemical }}</div>
            </div>
        </div>
    </div>
    {% endblock %}
    """
    with open('templates/result.html', 'w') as f: f.write(result)

    # 7. COMMUNITY PAGE
    comm = """
    {% extends "layout.html" %}
    {% block content %}
    <div class="top-nav">
        <h4><i class="fas fa-users"></i> Farmer Community</h4>
    </div>
    <div class="container mt-3">
        <form method="POST" class="mb-4">
            <div class="input-group">
                <input type="text" name="content" class="form-control" placeholder="Ask a question..." required>
                <select name="tag" class="form-select" style="max-width:100px;">
                    <option value="General">Gen</option>
                    <option value="Wheat">Wheat</option>
                    <option value="Rice">Rice</option>
                </select>
                <button class="btn btn-success"><i class="fas fa-paper-plane"></i></button>
            </div>
        </form>

        {% for post in posts %}
        <div class="custom-card p-3">
            <div class="d-flex justify-content-between">
                <h6 class="fw-bold text-success">{{ post.user_name }}</h6>
                <small class="text-muted">{{ post.timestamp.strftime('%d %b') }}</small>
            </div>
            <p class="mt-2">{{ post.content }}</p>
            <span class="badge bg-light text-dark border">#{{ post.crop_tag }}</span>
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
        user = User.query.filter_by(phone=phone).first()
        if not user:
            user = User(phone=phone)
            db.session.add(user)
            db.session.commit()
        session['user'] = user.phone
        session['name'] = user.name
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template('dashboard.html', active='home')

@app.route('/community', methods=['GET', 'POST'])
def community():
    if 'user' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        content = request.form['content']
        tag = request.form['tag']
        new_post = CommunityPost(user_name=session.get('name'), content=content, crop_tag=tag)
        db.session.add(new_post)
        db.session.commit()
    posts = CommunityPost.query.order_by(CommunityPost.timestamp.desc()).all()
    return render_template('community.html', posts=posts, active='comm')

@app.route('/weather')
def weather():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template('dashboard.html', active='weather') # Reuses dashboard for now

@app.route('/scan', methods=['GET'])
def scan_crop():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template('scan.html', active='scan')

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'file' not in request.files: return redirect(url_for('scan_crop'))
    file = request.files['file']
    if file.filename == '': return redirect(url_for('scan_crop'))
    
    # Save file (Simulation of processing)
    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    # AI SIMULATION ENGINE (Logic to avoid API Key)
    # In a real app, you would use: model.predict(image)
    # Here we randomly select a disease to demonstrate UI flow
    diagnosis = random.choice(DISEASE_DB)
    diagnosis['confidence'] = random.randint(85, 99)
    
    return render_template('result.html', diagnosis=diagnosis)

# --- EXECUTION ---
if __name__ == '__main__':
    create_assets() # Create HTML/CSS files automatically
    with app.app_context():
        db.create_all() # Create local Database
    
    print("------------------------------------------------")
    print(" KISAN DOCTOR IS RUNNING")
    print(" Open http://127.0.0.1:5000 in your browser")
    print(" No API Keys needed. Database is local.")
    print("------------------------------------------------")
    
    app.run(debug=True, port=5000)
