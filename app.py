import streamlit as st
import sqlite3
import hashlib
import os
from datetime import datetime
import google.generativeai as genai
from PIL import Image
import io

# Page configuration
st.set_page_config(
    page_title="Krishi Mitra - AI Farming Assistant",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #2E7D32;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #558B2F;
        text-align: center;
        margin-bottom: 3rem;
    }
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.5rem 2rem;
        font-weight: bold;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    .feature-card {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
        margin: 1rem 0;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .user-message {
        background: #E3F2FD;
        margin-left: 20%;
    }
    .ai-message {
        background: #F3E5F5;
        margin-right: 20%;
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# Initialize Gemini AI
@st.cache_resource
def init_gemini():
    genai.configure(api_key=st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY")))
    return genai.GenerativeModel('gemini-1.5-flash')

model = init_gemini()
vision_model = init_gemini()

# Database setup
def get_db():
    conn = sqlite3.connect('farm.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        content TEXT NOT NULL,
        image BLOB,
        likes INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER,
        user_id INTEGER,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (post_id) REFERENCES posts (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT NOT NULL,
        description TEXT,
        price TEXT,
        location TEXT,
        contact TEXT,
        image BLOB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS schemes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        eligibility TEXT,
        type TEXT,
        link TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        market TEXT NOT NULL,
        crop TEXT NOT NULL,
        variety TEXT,
        min_price REAL,
        max_price REAL,
        modal_price REAL,
        date DATE DEFAULT CURRENT_DATE
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER,
        user_id INTEGER,
        UNIQUE(post_id, user_id)
    )''')
    
    # Seed data
    c.execute("SELECT COUNT(*) FROM schemes")
    if c.fetchone()[0] == 0:
        schemes = [
            ("PM-KISAN", "₹6000/year income support for farmers", "Small & marginal farmers", "government", "https://pmkisan.gov.in"),
            ("Soil Health Card", "Free soil testing and recommendations", "All farmers", "government", "https://soilhealth.dac.gov.in"),
            ("Kisan Credit Card", "Low interest short-term credit", "All farmers", "government", "https://www.nabard.org"),
            ("PM Fasal Bima Yojana", "Crop insurance against calamities", "All farmers", "government", "https://pmfby.gov.in"),
            ("Organic Certification", "Financial assistance for organic farming", "Organic farmers", "private", "#"),
            ("Drip Irrigation Subsidy", "50% subsidy on equipment", "All farmers", "government", "#")
        ]
        c.executemany("INSERT INTO schemes (name, description, eligibility, type, link) VALUES (?, ?, ?, ?, ?)", schemes)
    
    c.execute("SELECT COUNT(*) FROM prices")
    if c.fetchone()[0] == 0:
        prices = [
            ("Pune", "Wheat", "Lokwan", 2200, 2450, 2325),
            ("Pune", "Rice", "Basmati", 3500, 4200, 3850),
            ("Pune", "Onion", "Red", 1200, 1800, 1500),
            ("Pune", "Tomato", "Hybrid", 800, 1400, 1100),
            ("Pune", "Soybean", "Yellow", 3800, 4200, 4000),
            ("Mumbai", "Wheat", "Lokwan", 2250, 2500, 2375),
            ("Mumbai", "Rice", "Basmati", 3600, 4300, 3950),
            ("Mumbai", "Onion", "Red", 1300, 1900, 1600),
            ("Mumbai", "Tomato", "Hybrid", 900, 1500, 1200),
            ("Mumbai", "Soybean", "Yellow", 3900, 4300, 4100)
        ]
        c.executemany("INSERT INTO prices (market, crop, variety, min_price, max_price, modal_price) VALUES (?, ?, ?, ?, ?, ?)", prices)
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

# Session state
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'user_name' not in st.session_state:
    st.session_state.user_name = None
if 'page' not in st.session_state:
    st.session_state.page = 'home'

# Helper functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def speak_text(text):
    """Display text with TTS button"""
    st.audio(f"data:text/plain;base64,{hashlib.md5(text.encode()).hexdigest()}", format="text/plain")
    js = f"""
    <script>
        var msg = new SpeechSynthesisUtterance("{text.replace('"', '\\"')}");
        msg.rate = 0.8;
        msg.pitch = 1;
        msg.lang = 'en-IN';
        window.speechSynthesis.speak(msg);
    </script>
    """
    st.components.v1.html(js, height=0)

# Authentication pages
def login_page():
    st.markdown('<h1 class="main-header">🌾 Krishi Mitra</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">AI-Powered Farming Assistant</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### Login")
        contact = st.text_input("Email or Mobile Number", key="login_contact")
        password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login", use_container_width=True):
            conn = get_db()
            user = conn.execute("SELECT * FROM users WHERE contact = ? AND password = ?", 
                               (contact, hash_password(password))).fetchone()
            conn.close()
            
            if user:
                st.session_state.user_id = user['id']
                st.session_state.user_name = user['name']
                st.rerun()
            else:
                st.error("Invalid credentials")
        
        if st.button("Create Account", use_container_width=True):
            st.session_state.page = 'register'
            st.rerun()

def register_page():
    st.markdown('<h1 class="main-header">🌾 Krishi Mitra</h1>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### Create Account")
        name = st.text_input("Full Name")
        contact = st.text_input("Email or Mobile Number")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        
        if st.button("Register", use_container_width=True):
            if password != confirm_password:
                st.error("Passwords don't match")
                return
            
            conn = get_db()
            try:
                c = conn.cursor()
                c.execute("INSERT INTO users (name, contact, password) VALUES (?, ?, ?)", 
                         (name, contact, hash_password(password)))
                conn.commit()
                user_id = c.lastrowid
                st.session_state.user_id = user_id
                st.session_state.user_name = name
                st.success("Account created successfully!")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("Contact already registered")
            finally:
                conn.close()
        
        if st.button("Back to Login", use_container_width=True):
            st.session_state.page = 'home'
            st.rerun()

# Main application
def dashboard():
    # Sidebar navigation
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user_name}")
        st.markdown("---")
        
        if st.button("🏠 Dashboard", use_container_width=True):
            st.session_state.page = 'dashboard'
        if st.button("🤖 AI Assistant", use_container_width=True):
            st.session_state.page = 'assistant'
        if st.button("📷 Crop Analysis", use_container_width=True):
            st.session_state.page = 'analysis'
        if st.button("👥 Community", use_container_width=True):
            st.session_state.page = 'community'
        if st.button("🛒 Marketplace", use_container_width=True):
            st.session_state.page = 'products'
        if st.button("📜 Schemes", use_container_width=True):
            st.session_state.page = 'schemes'
        if st.button("💰 Market Prices", use_container_width=True):
            st.session_state.page = 'prices'
        
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.user_id = None
            st.session_state.user_name = None
            st.rerun()
    
    # Page routing
    if st.session_state.page == 'dashboard':
        show_dashboard()
    elif st.session_state.page == 'assistant':
        show_assistant()
    elif st.session_state.page == 'analysis':
        show_analysis()
    elif st.session_state.page == 'community':
        show_community()
    elif st.session_state.page == 'products':
        show_products()
    elif st.session_state.page == 'schemes':
        show_schemes()
    elif st.session_state.page == 'prices':
        show_prices()

def show_dashboard():
    st.markdown('<h1 class="main-header">Dashboard</h1>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="feature-card" onclick="window.location.href='#assistant'">
            <h2>🤖</h2>
            <h3>AI Assistant</h3>
            <p>Get farming advice</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Open Assistant", key="btn_assistant"):
            st.session_state.page = 'assistant'
            st.rerun()
    
    with col2:
        st.markdown("""
        <div class="feature-card">
            <h2>📷</h2>
            <h3>Crop Analysis</h3>
            <p>Diagnose crop issues</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Analyze Crop", key="btn_analysis"):
            st.session_state.page = 'analysis'
            st.rerun()
    
    with col3:
        st.markdown("""
        <div class="feature-card">
            <h2>👥</h2>
            <h3>Community</h3>
            <p>Connect with farmers</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("View Community", key="btn_community"):
            st.session_state.page = 'community'
            st.rerun()
    
    with col4:
        st.markdown("""
        <div class="feature-card">
            <h2>🛒</h2>
            <h3>Marketplace</h3>
            <p>Buy & sell products</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Visit Market", key="btn_products"):
            st.session_state.page = 'products'
            st.rerun()

def show_assistant():
    st.markdown('<h1 class="main-header">🤖 AI Farming Assistant</h1>', unsafe_allow_html=True)
    
    # Initialize chat history
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Display chat history
    for msg in st.session_state.chat_history:
        if msg['role'] == 'user':
            st.markdown(f'<div class="chat-message user-message"><b>You:</b> {msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-message ai-message"><b>Assistant:</b> {msg["content"]}</div>', unsafe_allow_html=True)
            if st.button("🔊 Listen", key=f"tts_{hash(msg['content'])}"):
                speak_text(msg['content'])
    
    # Input
    question = st.text_input("Ask your farming question...", key="chat_input")
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("Send", use_container_width=True):
            if question:
                # Add user message
                st.session_state.chat_history.append({"role": "user", "content": question})
                
                # Get AI response
                prompt = f"""You are Krishi Mitra, an expert farming assistant for Indian farmers. 
                Answer this question in simple, practical language: {question}
                Provide specific, actionable advice."""
                
                try:
                    response = model.generate_content(prompt)
                    answer = response.text
                except:
                    answer = "I apologize, but I'm having trouble connecting right now. Please try again in a moment."
                
                st.session_state.chat_history.append({"role": "assistant", "content": answer})
                st.rerun()

def show_analysis():
    st.markdown('<h1 class="main-header">📷 Crop Analysis</h1>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("Upload a photo of your crop", type=['jpg', 'jpeg', 'png'])
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image", use_column_width=True)
        
        if st.button("Analyze Crop", use_container_width=True):
            with st.spinner("Analyzing your crop..."):
                prompt = """Analyze this crop image. Identify:
                1. The crop type
                2. Any visible diseases or problems
                3. Specific treatment recommendations (prefer organic methods)
                4. Prevention tips
                Be specific and practical for farmers."""
                
                try:
                    response = vision_model.generate_content([prompt, image])
                    analysis = response.text
                    
                    st.success("Analysis Complete!")
                    st.markdown(f"### Results:\n{analysis}")
                    
                    if st.button("🔊 Listen to Results"):
                        speak_text(analysis)
                except Exception as e:
                    st.error(f"Analysis failed: {str(e)}")

def show_community():
    st.markdown('<h1 class="main-header">👥 Farmer Community</h1>', unsafe_allow_html=True)
    
    # Create post
    with st.expander("Create New Post"):
        content = st.text_area("Share your experience...")
        post_image = st.file_uploader("Add Image (optional)", type=['jpg', 'jpeg', 'png'], key="post_img")
        
        if st.button("Post", use_container_width=True):
            conn = get_db()
            image_bytes = None
            if post_image:
                image_bytes = post_image.read()
            
            conn.execute("INSERT INTO posts (user_id, content, image) VALUES (?, ?, ?)",
                        (st.session_state.user_id, content, image_bytes))
            conn.commit()
            conn.close()
            st.success("Posted successfully!")
            st.rerun()
    
    # Display posts
    conn = get_db()
    posts = conn.execute('''SELECT p.*, u.name as author FROM posts p 
                           JOIN users u ON p.user_id = u.id 
                           ORDER BY p.created_at DESC''').fetchall()
    
    for post in posts:
        with st.container():
            st.markdown(f"### {post['author']}")
            st.markdown(f"*{post['created_at']}*")
            st.markdown(post['content'])
            
            if post['image']:
                st.image(io.BytesIO(post['image']), use_column_width=True)
            
            # Like button
            col1, col2 = st.columns([1, 10])
            with col1:
                if st.button(f"❤️ {post['likes']}", key=f"like_{post['id']}"):
                    try:
                        conn.execute("INSERT INTO likes (post_id, user_id) VALUES (?, ?)", 
                                   (post['id'], st.session_state.user_id))
                        conn.execute("UPDATE posts SET likes = likes + 1 WHERE id = ?", (post['id'],))
                        conn.commit()
                        st.rerun()
                    except:
                        pass
            
            # Comments
            comments = conn.execute('''SELECT c.*, u.name as author FROM comments c 
                                      JOIN users u ON c.user_id = u.id 
                                      WHERE c.post_id = ? ORDER BY c.created_at''', (post['id'],)).fetchall()
            
            with st.expander(f"💬 Comments ({len(comments)})"):
                for comment in comments:
                    st.markdown(f"**{comment['author']}:** {comment['content']}")
                
                new_comment = st.text_input("Add comment...", key=f"comment_{post['id']}")
                if st.button("Post Comment", key=f"btn_comment_{post['id']}"):
                    conn.execute("INSERT INTO comments (post_id, user_id, content) VALUES (?, ?, ?)",
                               (post['id'], st.session_state.user_id, new_comment))
                    conn.commit()
                    st.rerun()
            
            st.markdown("---")
    
    conn.close()

def show_products():
    st.markdown('<h1 class="main-header">🛒 Organic Marketplace</h1>', unsafe_allow_html=True)
    
    # Add product
    with st.expander("List Your Product"):
        name = st.text_input("Product Name")
        description = st.text_area("Description")
        price = st.text_input("Price (e.g., ₹100/kg)")
        location = st.text_input("Your Location")
        contact = st.text_input("Contact Number")
        prod_image = st.file_uploader("Product Image", type=['jpg', 'jpeg', 'png'])
        
        if st.button("List Product", use_container_width=True):
            conn = get_db()
            image_bytes = None
            if prod_image:
                image_bytes = prod_image.read()
            
            conn.execute("""INSERT INTO products (user_id, name, description, price, location, contact, image) 
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (st.session_state.user_id, name, description, price, location, contact, image_bytes))
            conn.commit()
            conn.close()
            st.success("Product listed!")
            st.rerun()
    
    # Display products
    conn = get_db()
    products = conn.execute('''SELECT p.*, u.name as seller FROM products p 
                              JOIN users u ON p.user_id = u.id 
                              ORDER BY p.created_at DESC''').fetchall()
    
    cols = st.columns(3)
    for idx, product in enumerate(products):
        with cols[idx % 3]:
            st.markdown(f"### {product['name']}")
            if product['image']:
                st.image(io.BytesIO(product['image']), use_column_width=True)
            st.markdown(f"**Price:** {product['price']}")
            st.markdown(f"**Location:** {product['location']}")
            st.markdown(f"**Seller:** {product['seller']}")
            st.markdown(f"**Contact:** {product['contact']}")
            st.markdown(f"*{product['description']}*")
            st.markdown("---")
    
    conn.close()

def show_schemes():
    st.markdown('<h1 class="main-header">📜 Government & Private Schemes</h1>', unsafe_allow_html=True)
    
    conn = get_db()
    
    tab1, tab2 = st.tabs(["Government Schemes", "Private Schemes"])
    
    with tab1:
        schemes = conn.execute("SELECT * FROM schemes WHERE type = 'government'").fetchall()
        for scheme in schemes:
            with st.container():
                st.markdown(f"### {scheme['name']}")
                st.markdown(f"*{scheme['description']}*")
                st.markdown(f"**Eligibility:** {scheme['eligibility']}")
                if scheme['link'] != '#':
                    st.markdown(f"[Learn More]({scheme['link']})")
                st.markdown("---")
    
    with tab2:
        schemes = conn.execute("SELECT * FROM schemes WHERE type = 'private'").fetchall()
        for scheme in schemes:
            with st.container():
                st.markdown(f"### {scheme['name']}")
                st.markdown(f"*{scheme['description']}*")
                st.markdown(f"**Eligibility:** {scheme['eligibility']}")
                st.markdown("---")
    
    conn.close()

def show_prices():
    st.markdown('<h1 class="main-header">💰 Market Prices</h1>', unsafe_allow_html=True)
    
    market = st.selectbox("Select Market", ["Pune", "Mumbai"])
    
    conn = get_db()
    prices = conn.execute("SELECT * FROM prices WHERE market = ? ORDER BY crop", (market,)).fetchall()
    
    data = []
    for p in prices:
        data.append({
            "Crop": p['crop'],
            "Variety": p['variety'],
            "Min Price (₹/quintal)": f"₹{p['min_price']}",
            "Max Price (₹/quintal)": f"₹{p['max_price']}",
            "Modal Price (₹/quintal)": f"₹{p['modal_price']}"
        })
    
    st.table(data)
    conn.close()

# Main app logic
if st.session_state.user_id is None:
    if st.session_state.page == 'register':
        register_page()
    else:
        login_page()
else:
    dashboard()
