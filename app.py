import os
import sys
import requests
import random
import string
import threading
import asyncio
from datetime import datetime
from typing import List, Optional, Union

from flask import (
    Flask,
    render_template_string as rts,
    request,
    jsonify,
    redirect,
    url_for,
    session,
)
import discord
from discord.ext import commands
import psycopg2
from psycopg2.extras import RealDictCursor

# ==============================
# 기본 설정
# ==============================
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change")

DISCORD_CLIENT_ID = os.environ.get("DISCORD_CLIENT_ID", "1488342279029784768")
DISCORD_CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET", "S8wERVotwZOSpz2A_75KCIWeYbxMf9GP")
DISCORD_REDIRECT_URI = os.environ.get("DISCORD_REDIRECT_URI", "https://api.redkorea.store/auth/callback")
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "")

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres.cczcenhgureeamwjtkug:5P5iPdjnEMP7ZKDQ@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres?sslmode=require")

# 데이터베이스 연결
def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (id BIGINT PRIMARY KEY, points INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS orders (id SERIAL PRIMARY KEY, user_id BIGINT, product_name TEXT, price INTEGER, code TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    cur.execute("CREATE TABLE IF NOT EXISTS product_codes (id SERIAL PRIMARY KEY, product_id TEXT NOT NULL, code TEXT NOT NULL UNIQUE, used INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS charge_requests (id SERIAL PRIMARY KEY, order_number TEXT UNIQUE NOT NULL, user_id BIGINT NOT NULL, amount INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, processed INTEGER DEFAULT 0)")
    conn.commit()
    conn.close()

init_db()

# ==============================
# DB 함수
# ==============================
def to_int(value):
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except:
        return None

def get_points(user_id):
    user_id = to_int(user_id)
    if not user_id:
        return 0
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT points FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row["points"] if row else 0

def add_points(user_id, amount):
    user_id = to_int(user_id)
    if not user_id:
        return 0
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT points FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    if row:
        new_balance = row["points"] + amount
        cur.execute("UPDATE users SET points = %s WHERE id = %s", (new_balance, user_id))
    else:
        new_balance = amount
        cur.execute("INSERT INTO users (id, points) VALUES (%s, %s)", (user_id, new_balance))
    conn.commit()
    conn.close()
    return new_balance

def remove_points(user_id, amount):
    user_id = to_int(user_id)
    if not user_id:
        return None
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT points FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    if not row or row["points"] < amount:
        conn.close()
        return None
    new_balance = row["points"] - amount
    cur.execute("UPDATE users SET points = %s WHERE id = %s", (new_balance, user_id))
    conn.commit()
    conn.close()
    return new_balance

def insert_order(user_id, product_name, price, code):
    user_id = to_int(user_id)
    if not user_id:
        return
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO orders (user_id, product_name, price, code) VALUES (%s, %s, %s, %s)",
                (user_id, product_name, price, code))
    conn.commit()
    conn.close()

def get_user_orders(user_id, limit=10):
    user_id = to_int(user_id)
    if not user_id:
        return []
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT product_name, price, code, created_at FROM orders WHERE user_id = %s ORDER BY created_at DESC LIMIT %s",
                (user_id, limit))
    rows = cur.fetchall()
    conn.close()
    orders = []
    for row in rows:
        order = dict(row)
        if isinstance(order["created_at"], datetime):
            order["created_at"] = order["created_at"].strftime("%Y-%m-%d %H:%M:%S")
        orders.append(order)
    return orders

def get_unused_code(product_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT code FROM product_codes WHERE product_id = %s AND used = 0 LIMIT 1", (product_id,))
    row = cur.fetchone()
    if row:
        code = row["code"]
        cur.execute("UPDATE product_codes SET used = 1 WHERE code = %s", (code,))
        conn.commit()
        conn.close()
        return code
    conn.close()
    return None

def get_code_stock(product_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM product_codes WHERE product_id = %s AND used = 0", (product_id,))
    row = cur.fetchone()
    conn.close()
    return row["count"] if row else 0

def create_charge_request(user_id, amount):
    user_id = to_int(user_id)
    if not user_id:
        return ""
    order_num = ''.join(random.choices(string.digits, k=6))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO charge_requests (order_number, user_id, amount, processed) VALUES (%s, %s, %s, 0)",
                (order_num, user_id, amount))
    conn.commit()
    conn.close()
    return order_num

# ==============================
# 상품 데이터
# ==============================
PRODUCTS = [
    {"id": "wolf_lite", "name": "🔴 RED-WOLF-LITE", "desc": "라이트 버전으로 부담 없이 경험해보는 패키지", "price": 7000, "img": "https://i.imgur.com/Z3BhZ18.jpeg"},
    {"id": "wolf", "name": "🔴 RED-WOLF", "desc": "공격적인 운영을 위한 하이레벨 패키지", "price": 13000, "img": "https://i.imgur.com/0UBCMGR.jpeg"},
    {"id": "kd_dropper", "name": "🔴 RED-kd-dropper", "desc": "집중력과 몰입감을 높여주는 트레이닝 패키지", "price": 7000, "img": "https://i.imgur.com/ApGpo16.jpeg"},
    {"id": "owo", "name": "🔴 RED-OWO", "desc": "AIMBOT 가까운 뼈 혹은 타겟 지정! 가성비 !!", "price": 7000, "img": "https://i.imgur.com/7W1eg5S.png"},
]

# ==============================
# 디스코드 봇 (간소화)
# ==============================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=".", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ 디스코드 봇 로그인: {bot.user}")

@bot.command(name="충전")
@commands.has_permissions(administrator=True)
async def charge_cmd(ctx: commands.Context, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.reply("❌ 0원 이상 입력하세요.")
        return
    new_balance = add_points(member.id, amount)
    await ctx.reply(f"✅ {member.mention} 님에게 {amount:,}P 충전 완료. 현재 포인트: **{new_balance:,}P**")

def run_bot():
    """봇 실행"""
    if DISCORD_TOKEN:
        try:
            bot.run(DISCORD_TOKEN)
        except Exception as e:
            print(f"봇 실행 오류: {e}")
    else:
        print("⚠️ DISCORD_TOKEN 없음 - 봇 실행 안함")

# ==============================
# Flask 라우트
# ==============================
@app.before_request
def normalize_session():
    if session.get("user_id"):
        try:
            session["user_id"] = int(session["user_id"])
        except:
            session.pop("user_id", None)

@app.route("/")
def index():
    return rts(HTML_TEMPLATE, user_id=session.get("user_id"), username=session.get("username"), avatar=session.get("avatar"), PRODUCTS=PRODUCTS)

@app.route("/orders")
def orders():
    if not session.get("user_id"):
        return redirect(url_for("index"))
    return rts(ORDERS_TEMPLATE, user_id=session.get("user_id"), username=session.get("username"), avatar=session.get("avatar"))

@app.route("/api/points")
def api_points():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"points": 0})
    return jsonify({"points": get_points(user_id)})

@app.route("/api/stock")
def api_stock():
    stocks = {p["id"]: get_code_stock(p["id"]) for p in PRODUCTS}
    return jsonify(stocks)

@app.route("/api/buy", methods=["POST"])
def api_buy():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"ok": False, "error": "로그인 필요"}), 401
    
    data = request.get_json()
    if not data:
        return jsonify({"ok": False, "error": "잘못된 요청"}), 400
    
    product_id = data.get("product_id")
    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not product:
        return jsonify({"ok": False, "error": "상품 없음"}), 400
    
    price = product["price"]
    product_name = product["name"]
    
    new_balance = remove_points(user_id, price)
    if new_balance is None:
        current = get_points(user_id)
        return jsonify({"ok": False, "error": f"포인트 부족 (필요: {price:,}P / 보유: {current:,}P)"}), 400
    
    code = get_unused_code(product_id)
    if code is None:
        add_points(user_id, price)
        return jsonify({"ok": False, "error": f"재고 부족 - {product_name}"}), 400
    
    insert_order(user_id, product_name, price, code)
    
    return jsonify({"ok": True, "code": code, "new_balance": new_balance})

@app.route("/api/charge-request", methods=["POST"])
def api_charge_request():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"ok": False, "error": "로그인 필요"}), 401
    
    data = request.get_json()
    amount = data.get("amount")
    if not amount or amount < 1:
        return jsonify({"ok": False, "error": "1원 이상 입력"}), 400
    
    order_num = create_charge_request(user_id, amount)
    return jsonify({"ok": True, "order_number": order_num})

@app.route("/api/orders")
def api_orders():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"orders": []})
    return jsonify({"orders": get_user_orders(user_id, 50)})

@app.route("/auth/login")
def auth_login():
    return redirect(f"https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&redirect_uri={DISCORD_REDIRECT_URI}&response_type=code&scope=identify")

@app.route("/auth/callback")
def auth_callback():
    code = request.args.get("code")
    if not code:
        return redirect(url_for("index"))
    
    data = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": DISCORD_REDIRECT_URI,
    }
    resp = requests.post("https://discord.com/api/oauth2/token", data=data)
    if resp.status_code != 200:
        return redirect(url_for("index"))
    
    token_data = resp.json()
    user_resp = requests.get("https://discord.com/api/users/@me", headers={"Authorization": f"Bearer {token_data['access_token']}"})
    if user_resp.status_code == 200:
        user = user_resp.json()
        session["user_id"] = int(user["id"])
        session["username"] = f"{user['username']}#{user['discriminator']}"
        session["avatar"] = f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}.png" if user.get("avatar") else None
    
    return redirect(url_for("index"))

@app.route("/auth/logout")
def auth_logout():
    session.clear()
    return redirect(url_for("index"))

# ==============================
# HTML 템플릿
# ==============================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>RED | 프리미엄 샵</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body {
            background: radial-gradient(circle at 10% 20%, #0f0c1f, #02010a);
            font-family: 'Inter', sans-serif;
            color: #eef2ff;
            padding: 2rem;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header {
            background: rgba(15,23,42,0.65);
            backdrop-filter: blur(16px);
            border-radius: 2rem;
            padding: 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
        }
        .logo { font-size: 1.8rem; font-weight: 800; background: linear-gradient(135deg,#fff,#a78bfa,#ff4b6e); -webkit-background-clip:text; background-clip:text; color:transparent; }
        .user-info { display: flex; align-items: center; gap: 1rem; background: rgba(0,0,0,0.35); padding: 0.5rem 1rem; border-radius: 60px; }
        .avatar { width: 40px; height: 40px; border-radius: 50%; border: 2px solid #60a5fa; }
        .points { color: #ffb347; font-weight: 700; }
        .product-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1.5rem; }
        .product-card {
            background: rgba(0,0,0,0.4);
            border-radius: 1.5rem;
            overflow: hidden;
            border: 1px solid rgba(96,165,250,0.2);
            transition: transform 0.2s;
        }
        .product-card:hover { transform: translateY(-4px); border-color: #60a5fa; }
        .product-img { width: 100%; height: 200px; object-fit: cover; }
        .product-info { padding: 1.2rem; }
        .product-title { font-size: 1.2rem; font-weight: 700; }
        .product-price { font-size: 1.4rem; font-weight: 800; color: #ffb347; margin: 0.5rem 0; }
        .buy-btn {
            background: linear-gradient(135deg,#ff4b6e,#ff6b4a);
            border: none;
            width: 100%;
            padding: 0.7rem;
            border-radius: 40px;
            font-weight: 700;
            color: white;
            cursor: pointer;
        }
        .nav-links { display: flex; gap: 1rem; margin-top: 1rem; }
        .nav-link { color: #cbd5e1; text-decoration: none; padding: 0.5rem 1rem; border-radius: 40px; }
        .nav-link:hover, .nav-link.active { background: rgba(96,165,250,0.2); color: white; }
        .toast {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: #1e1a2f;
            padding: 12px 24px;
            border-radius: 40px;
            border: 1px solid #ff4b6e;
            z-index: 1001;
        }
        button { background: #5865f2; border: none; padding: 0.5rem 1rem; border-radius: 40px; color: white; cursor: pointer; }
        a { text-decoration: none; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <div class="logo">RED+RLNL</div>
        <div class="user-info">
            {% if user_id %}
            <img class="avatar" src="{{ avatar }}">
            <span>{{ username }}</span>
            <span class="points"><i class="fas fa-coins"></i> <span id="points">0</span> P</span>
            <a href="/auth/logout"><button>로그아웃</button></a>
            {% else %}
            <a href="/auth/login"><button>🔐 디스코드 로그인</button></a>
            {% endif %}
        </div>
    </div>
    <div class="nav-links">
        <a href="/" class="nav-link active">🏠 상품</a>
        <a href="/orders" class="nav-link">📦 구매내역</a>
    </div>
    <div class="product-grid" id="productGrid"></div>
</div>
<script>
    const userLoggedIn = {{ "true" if user_id else "false" }};
    const products = {{ PRODUCTS|tojson }};
    let stockData = {};

    async function fetchStock() {
        const res = await fetch('/api/stock');
        stockData = await res.json();
    }

    function showToast(msg, isError = false) {
        let toast = document.getElementById('toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'toast';
            toast.className = 'toast';
            document.body.appendChild(toast);
        }
        toast.textContent = msg;
        toast.style.background = isError ? '#8b0000' : '#1e1a2f';
        toast.style.opacity = '1';
        setTimeout(() => toast.style.opacity = '0', 3000);
    }

    async function refreshPoints() {
        if (!userLoggedIn) return;
        const res = await fetch('/api/points');
        const data = await res.json();
        document.getElementById('points').innerText = (data.points || 0).toLocaleString();
    }

    async function buyProduct(productId, productName, price) {
        try {
            const res = await fetch('/api/buy', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ product_id: productId })
            });
            const data = await res.json();
            if (data.ok) {
                showToast(`✅ 구매 완료! 코드: ${data.code}`);
                refreshPoints();
                await fetchStock();
                renderProducts();
            } else {
                showToast(data.error || "구매 실패", true);
            }
        } catch(e) {
            showToast("오류: " + e.message, true);
        }
    }

    function renderProducts() {
        if (!userLoggedIn) return;
        const grid = document.getElementById('productGrid');
        grid.innerHTML = '';
        products.forEach(p => {
            const stock = stockData[p.id] || 0;
            const card = document.createElement('div');
            card.className = 'product-card';
            card.innerHTML = `
                <img class="product-img" src="${p.img}">
                <div class="product-info">
                    <div class="product-title">${p.name}</div>
                    <div class="product-desc">${p.desc}</div>
                    <div class="product-price">${p.price.toLocaleString()}P</div>
                    <div class="product-stock">📦 재고: ${stock}개</div>
                    <button class="buy-btn" onclick="buyProduct('${p.id}','${p.name}',${p.price})">🛒 구매하기</button>
                </div>
            `;
            grid.appendChild(card);
        });
    }

    if (userLoggedIn) {
        fetchStock().then(() => renderProducts());
        refreshPoints();
        setInterval(refreshPoints, 30000);
    }
</script>
</body>
</html>
"""

ORDERS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>내 구매내역 | RED</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body {
            background: radial-gradient(circle at 10% 20%, #0f0c1f, #02010a);
            font-family: 'Inter', sans-serif;
            color: #eef2ff;
            padding: 2rem;
        }
        .container { max-width: 1000px; margin: 0 auto; }
        .header {
            background: rgba(15,23,42,0.65);
            backdrop-filter: blur(16px);
            border-radius: 2rem;
            padding: 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
        }
        .logo { font-size: 1.8rem; font-weight: 800; background: linear-gradient(135deg,#fff,#a78bfa,#ff4b6e); -webkit-background-clip:text; background-clip:text; color:transparent; }
        .user-info { display: flex; align-items: center; gap: 1rem; background: rgba(0,0,0,0.35); padding: 0.5rem 1rem; border-radius: 60px; }
        .avatar { width: 40px; height: 40px; border-radius: 50%; border: 2px solid #60a5fa; }
        .points { color: #ffb347; font-weight: 700; }
        .nav-links { display: flex; gap: 1rem; margin-bottom: 1rem; }
        .nav-link { color: #cbd5e1; text-decoration: none; padding: 0.5rem 1rem; border-radius: 40px; }
        .nav-link:hover, .nav-link.active { background: rgba(96,165,250,0.2); color: white; }
        table { width: 100%; border-collapse: collapse; background: rgba(15,23,42,0.65); border-radius: 1rem; overflow: hidden; }
        th, td { padding: 1rem; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1); }
        .code { font-family: monospace; background: #0f172a; padding: 0.2rem 0.6rem; border-radius: 8px; }
        button { background: #5865f2; border: none; padding: 0.5rem 1rem; border-radius: 40px; color: white; cursor: pointer; }
        a { text-decoration: none; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <div class="logo">RED+RLNL</div>
        <div class="user-info">
            {% if user_id %}
            <img class="avatar" src="{{ avatar }}">
            <span>{{ username }}</span>
            <span class="points"><i class="fas fa-coins"></i> <span id="points">0</span> P</span>
            <a href="/auth/logout"><button>로그아웃</button></a>
            {% endif %}
        </div>
    </div>
    <div class="nav-links">
        <a href="/" class="nav-link">🏠 상품</a>
        <a href="/orders" class="nav-link active">📦 구매내역</a>
    </div>
    <div id="ordersList"></div>
</div>
<script>
    async function loadOrders() {
        const res = await fetch('/api/orders');
        const data = await res.json();
        const container = document.getElementById('ordersList');
        if (!data.orders || data.orders.length === 0) {
            container.innerHTML = '<p style="text-align:center;padding:2rem;">아직 구매 내역이 없습니다.</p>';
            return;
        }
        let html = '<table><thead><tr><th>상품명</th><th>금액</th><th>코드</th><th>구매일시</th></tr></thead><tbody>';
        for (let o of data.orders) {
            html += `<tr><td>${o.product_name}</td><td>${o.price.toLocaleString()}P</td><td><span class="code">${o.code}</span></td><td>${o.created_at}</td></tr>`;
        }
        html += '</tbody></table>';
        container.innerHTML = html;
    }
    async function refreshPoints() {
        const res = await fetch('/api/points');
        const data = await res.json();
        document.getElementById('points').innerText = (data.points || 0).toLocaleString();
    }
    loadOrders();
    refreshPoints();
</script>
</body>
</html>
"""

# ==============================
# 실행 - 단일 서버
# ==============================
if __name__ == "__main__":
    # 봇은 별도 스레드로 실행 (선택사항)
    if DISCORD_TOKEN:
        threading.Thread(target=run_bot, daemon=True).start()
    
    # Flask 서버 실행
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
