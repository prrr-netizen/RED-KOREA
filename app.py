import os
import sqlite3
import requests
from flask import (
    Flask,
    render_template_string,
    request,
    jsonify,
    redirect,
    url_for,
    session,
)

app = Flask(__name__)

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change")
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "dev-pass-change")


WEBHOOK_URL = "https://discord.com/api/webhooks/1488231305396224041/Fa_z7Wihwf9-k79aGNcvaLNj3emxWYxlFoD6xVGkgLxzZKig3Uc7MQpL8Nk93d4Pyfat"


DB_PATH = os.path.join(os.path.dirname(__file__), "shop.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            points INTEGER DEFAULT 0
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT,
            price INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            charge_url TEXT
        )
        """
    )

    cur.execute(
        "INSERT OR IGNORE INTO settings (id, charge_url) VALUES (1, 'https://discord.gg/q6nJpYuFB8')"
    )

    conn.commit()
    conn.close()


init_db()


def login_required(f):
    from functools import wraps

    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)

    return wrapper


# ===== 메인 화면 =====
index_html = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>RED | 온라인 샵</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;14..32,400;14..32,600;14..32,700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Inter', sans-serif; }
        body { background-color: #fafaf8; color: #1c1c1c; line-height: 1.5; }

        .header {
            background-color: #ffffff;
            border-bottom: 1px solid #eaeaea;
            padding: 1rem 2rem;
            position: sticky;
            top: 0;
            z-index: 100;
            backdrop-filter: blur(8px);
            background-color: rgba(255, 255, 255, 0.95);
        }
        .nav-container {
            max-width: 1280px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
        }
        .logo {
            font-size: 1.6rem;
            font-weight: 700;
            letter-spacing: -0.3px;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .logo-text {
            background: linear-gradient(135deg, #2b2d42, #4a4e69);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }
        .nav-links { display: flex; gap: 1.2rem; align-items: center; }
        .nav-links a { text-decoration: none; color: #2d2f36; font-weight: 500; transition: 0.2s; font-size: 0.9rem; }
        .nav-links a:hover { color: #8b5f6c; }
        .cart-icon { position: relative; font-size: 1.4rem; }

        .discord-btn {
            padding: 0.35rem 0.9rem;
            border-radius: 999px;
            background:#5865F2;
            color:#fff;
            font-size:0.8rem;
            font-weight:600;
        }

        .hero {
            background: #000;
            padding: 0;
            border-bottom: 1px solid #ddd8c8;
        }
        .hero-inner {
            max-width: 1280px;
            margin: 0 auto;
            height: 260px;
            background-image: url('https://cdn.discordapp.com/attachments/1084455385848627250/1488158674340937739/36a47df6e588163a.png?ex=69cbc344&is=69ca71c4&hm=e6fa4e68b74088782c150e3dd67245bbd7f7fdf179905bdfd26153e7ed94c346');
            background-size: cover;
            background-position: center;
            border-radius: 0 0 24px 24px;
        }

        .info-bar {
            max-width: 1280px;
            margin: 1.5rem auto 0;
            padding: 0 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
            flex-wrap: wrap;
        }
        .info-bar-left { font-size: 0.95rem; color: #555; }
        .info-bar-right button {
            background: #ff4b6e;
            color: white;
            border: none;
            padding: 0.7rem 1.3rem;
            border-radius: 999px;
            font-size: 0.95rem;
            font-weight: 700;
            cursor: pointer;
            box-shadow: 0 8px 18px rgba(255, 75, 110, 0.35);
            transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
        }
        .info-bar-right button:hover {
            background: #ff1f50;
            transform: translateY(-1px);
            box-shadow: 0 12px 24px rgba(255, 75, 110, 0.45);
        }
        .info-bar-right button:active {
            transform: translateY(0);
            box-shadow: 0 6px 14px rgba(255, 75, 110, 0.3);
        }

        .products-section {
            max-width: 1280px;
            margin: 2.5rem auto;
            padding: 0 2rem;
        }
        .section-title {
            font-size: 1.6rem;
            font-weight: 600;
            margin-bottom: 2rem;
            position: relative;
            display: inline-block;
            padding-bottom: 4px;
        }
        .section-title::after {
            content: "";
            position: absolute;
            left: 0;
            bottom: 0;
            height: 3px;
            width: 0;
            background: linear-gradient(90deg, #b5838d, #ff4b6e);
            border-radius: 999px;
            animation: section-underline 1s ease-out forwards;
        }
        @keyframes section-underline {
            from { width: 0; }
            to { width: 100%; }
        }

        .product-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 2rem;
        }
        .product-card {
            background: white;
            border-radius: 24px;
            overflow: hidden;
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.02), 0 6px 6px rgba(0, 0, 0, 0.03);
            transition: transform 0.25s ease, box-shadow 0.25s ease;
            cursor: pointer;
            border: 1px solid #efefef;
        }
        .product-card:hover {
            transform: translateY(-6px);
            box-shadow: 0 25px 30px -12px rgba(0, 0, 0, 0.15);
        }
        .product-img {
            width: 100%;
            height: 260px;
            background-color: #f3f0ea;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 4rem;
            color: #7c6e65;
        }
        .product-info { padding: 1.5rem; }
        .product-title { font-weight: 700; font-size: 1.25rem; margin-bottom: 0.5rem; }
        .product-price { color: #b5838d; font-weight: 700; font-size: 1.3rem; margin: 0.5rem 0; }
        .product-desc { color: #5a5e66; font-size: 0.85rem; margin-bottom: 1rem; }
        .buy-btn {
            background: #1e2a2f;
            color: white;
            border: none;
            padding: 0.7rem 1rem;
            width: 100%;
            border-radius: 60px;
            font-weight: 600;
            cursor: pointer;
            transition: 0.2s;
            font-size: 0.9rem;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        .buy-btn:hover { background: #2e3e44; transform: scale(0.98); }

        .toast {
            position: fixed;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%) translateY(100px);
            background: #1e2a2f;
            color: #f5ebe0;
            padding: 12px 24px;
            border-radius: 60px;
            font-weight: 500;
            font-size: 0.9rem;
            z-index: 1000;
            transition: transform 0.25s ease;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            pointer-events: none;
            white-space: nowrap;
        }
        .toast.show { transform: translateX(-50%) translateY(0); }

        .footer {
            background: #1c1e24;
            color: #bcbcbc;
            text-align: center;
            padding: 2rem;
            margin-top: 3rem;
            font-size: 0.85rem;
        }

        @media (max-width: 640px) {
            .nav-container { flex-direction: column; gap: 1rem; }
            .nav-links { gap: 1.2rem; }
            .info-bar { flex-direction: column; align-items: flex-start; }
            .hero-inner { height: 200px; border-radius: 0; }
        }
    </style>
</head>
<body>

<div class="header">
    <div class="nav-container">
        <div class="logo">
            <img
                src="https://cdn.discordapp.com/attachments/1084455385848627250/1488158725670961254/8f7d09ac9d5ba195.png?ex=69cbc350&is=69ca71d0&hm=951aa334d7e1c5e77b7a7970a48ec91752e8c82094ccf3c9e37b5c6ddb4250b3"
                alt="RED+RLNL"
                style="height: 26px; border-radius: 4px;"
            >
            <span class="logo-text">RED+RLNL</span>
        </div>
        <div class="nav-links">
            <a href="#">홈</a>
            <a href="#">베스트</a>
            <a href="#">신상품</a>
            <a href="#">컬렉션</a>
            <div class="cart-icon">
                <i class="fas fa-shopping-bag"></i>
            </div>
            <a href="https://discord.gg/q6nJpYuFB8" class="discord-btn">디스코드</a>
        </div>
    </div>
</div>

<section class="hero">
    <div class="hero-inner"></div>
</section>

<div class="info-bar">
    <div class="info-bar-left">
        현재 포인트: <span id="pointsText">0</span> P
    </div>
    <div class="info-bar-right">
        <button id="chargeBtn">충전하기</button>
    </div>
</div>

<section class="products-section">
    <div class="section-title">✨ 오늘의 추천 상품</div>
    <div class="product-grid" id="productGrid"></div>
</section>

<div class="footer">
    <p>&copy; 2026 RED</p>
</div>

<div id="toastMsg" class="toast"></div>

<script>
    const products = [
        { id: 1, name: "🔴𝙍𝙀𝘿-𝗪𝗢𝗟𝗙-𝗟𝗜𝗧𝗘", price: 13000, desc: "라이트 버전으로 부담 없이 경험해보는 패키지", emoji: "🏋️" },
        { id: 2, name: "🔴RED-𝗪𝗢𝗟𝗙",         price: 13000, desc: "공격적인 운영을 위한 하이레벨 패키지",      emoji: "🐺" },
        { id: 3, name: "🔴RED-kd-dropper",      price: 7000,  desc: "집중력과 몰입감을 높여주는 트레이닝 패키지", emoji: "🎯" }
    ];

    const productGrid = document.getElementById('productGrid');
    const toastEl = document.getElementById('toastMsg');
    const pointsText = document.getElementById('pointsText');
    const chargeBtn = document.getElementById('chargeBtn');
    let toastTimer = null;

    const urlParams = new URLSearchParams(window.location.search);
    const discordUserId = urlParams.get("uid");

    function showToast(message) {
        if (toastTimer) clearTimeout(toastTimer);
        toastEl.textContent = message;
        toastEl.classList.add('show');
        toastTimer = setTimeout(() => {
            toastEl.classList.remove('show');
        }, 2000);
    }

    async function refreshPoints() {
        if (!discordUserId) {
            pointsText.textContent = "0";
            return;
        }
        try {
            const res = await fetch(`/api/points?user_id=${discordUserId}`);
            const data = await res.json();
            pointsText.textContent = (data.points ?? 0).toLocaleString();
        } catch (e) {
            console.error(e);
        }
    }

    async function handleBuy(productName, price) {
        if (!discordUserId) {
            showToast("디스코드 링크를 통해 접속해 주세요.");
            return;
        }
        try {
            const res = await fetch("/api/buy", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_id: discordUserId, name: productName, price: price })
            });
            const data = await res.json();

            if (data.ok) {
                showToast(`✅ ${productName} 구매 완료`);
                await refreshPoints();
                window.location.href = "https://discord.gg/q6nJpYuFB8";
            } else {
                showToast(data.error || "구매 실패");
            }
        } catch (e) {
            console.error(e);
            showToast("오류가 발생했습니다");
        }
    }

    function renderProducts() {
        productGrid.innerHTML = '';
        products.forEach(product => {
            const card = document.createElement('div');
            card.className = 'product-card';

            const imgDiv = document.createElement('div');
            imgDiv.className = 'product-img';

            if (product.name === "🔴RED-𝗪𝗢𝗟𝗙") {
                imgDiv.innerHTML = `
                    <img src="https://cdn.discordapp.com/attachments/1083101135096795201/1488186254561378425/WOLF.webp?ex=69cbdcf4&is=69ca8b74&hm=7c6e58852c1c44851df7aa5706670c6d1ed777dce03f80bd413091fbd3267786"
                         alt="RED-wolf"
                         style="width:100%; height:100%; object-fit:cover; border-radius:24px 24px 0 0;">
                `;
            } else if (product.name === "🔴𝙍𝙀𝘿-𝗪𝗢𝗟𝗙-𝗟𝗜𝗧𝗘") {
                imgDiv.innerHTML = `
                    <img src="https://cdn.discordapp.com/attachments/1084455385848627250/1488164919663788065/WOLF_LITE.png?ex=69cbc915&is=69ca7795&hm=584c44535dd2b20996264d09dc9462c4cab828df89036640dc1fa1aaa0c0017a"
                         alt="RED-WOLF-LITE"
                         style="width:100%; height:100%; object-fit:cover; border-radius:24px 24px 0 0;">
                `;
            } else {
                imgDiv.innerHTML = `<span style="font-size: 4rem;">${product.emoji}</span>`;
            }

            const infoDiv = document.createElement('div');
            infoDiv.className = 'product-info';

            const title = document.createElement('div');
            title.className = 'product-title';
            title.innerText = product.name;

            const price = document.createElement('div');
            price.className = 'product-price';
            price.innerText = `${product.price.toLocaleString()}원`;

            const desc = document.createElement('div');
            desc.className = 'product-desc';
            desc.innerText = product.desc;

            const btn = document.createElement('button');
            btn.className = 'buy-btn';
            btn.innerHTML = '<i class="fas fa-shopping-cart"></i> 구매하기';
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                handleBuy(product.name, product.price);
            });

            infoDiv.appendChild(title);
            infoDiv.appendChild(price);
            infoDiv.appendChild(desc);
            infoDiv.appendChild(btn);

            card.appendChild(imgDiv);
            card.appendChild(infoDiv);

            card.addEventListener('click', (e) => {
                if(e.target !== btn && !btn.contains(e.target)) {
                    handleBuy(product.name, product.price);
                }
            });

            productGrid.appendChild(card);
        });
    }

    chargeBtn.addEventListener('click', async () => {
        try {
            const res = await fetch("/api/charge-url");
            const data = await res.json();
            showToast("충전 페이지로 이동합니다.");
            if (data.url) {
                window.location.href = data.url;
            }
        } catch (e) {
            console.error(e);
            showToast("오류가 발생했습니다");
        }
    });

    renderProducts();
    refreshPoints();
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(index_html)


@app.route("/api/points")
def api_points():
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"points": 0})
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT points FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    points = row[0] if row else 0
    return jsonify({"points": points})


@app.route("/api/buy", methods=["POST"])
def api_buy():
    data = request.get_json()
    user_id = data.get("user_id")
    name = data.get("name")
    price = data.get("price")

    if not user_id or not name or price is None:
        return jsonify({"ok": False, "error": "잘못된 요청입니다"}), 400

    try:
        user_id = int(user_id)
        price = int(price)
    except ValueError:
        return jsonify({"ok": False, "error": "잘못된 요청입니다"}), 400

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT points FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    points = row[0] if row else 0

    if points < price:
        conn.close()
        return jsonify({"ok": False, "error": "포인트가 부족합니다"}), 400

    cur.execute("UPDATE users SET points = points - ? WHERE id = ?", (price, user_id))
    cur.execute(
        "INSERT INTO orders (product_name, price) VALUES (?, ?)",
        (name, price),
    )
    conn.commit()
    conn.close()

    return jsonify({"ok": True})


@app.route("/api/charge-url")
def api_charge_url():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT charge_url FROM settings WHERE id = 1")
    row = cur.fetchone()
    conn.close()
    url = row[0] if row and row[0] else "https://discord.gg/q6nJpYuFB8"
    return jsonify({"url": url})


admin_html = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>RED Admin</title>
    <style>
        body { font-family: sans-serif; padding: 20px; background:#111; color:#eee; }
        h1 { margin-bottom: 1rem; }
        section { margin-bottom: 2rem; }
        label { display:block; margin-bottom:0.5rem; }
        input[type="text"] { width: 100%; max-width: 500px; padding: 0.4rem; }
        button { margin-top:0.5rem; padding:0.4rem 0.8rem; cursor:pointer; }
        table { border-collapse: collapse; width:100%; max-width:800px; margin-top:1rem; font-size:0.9rem; }
        th, td { border:1px solid #444; padding:0.4rem 0.6rem; }
        th { background:#222; }
        a { color:#4fc3f7; }
    </style>
</head>
<body>
    <h1>RED Admin</h1>
    <p><a href="/admin/logout">로그아웃</a></p>

    <section>
        <h2>1. 유저 포인트 수동 설정</h2>
        <form method="post" action="/admin/set-points">
            <label>디스코드 유저 ID:</label>
            <input type="text" name="user_id" placeholder="예: 123456789012345678">
            <label>포인트 값:</label>
            <input type="text" name="points" placeholder="예: 100000">
            <button type="submit">저장</button>
        </form>
    </section>

    <section>
        <h2>2. 충전하기 버튼 URL 설정</h2>
        <form method="post" action="/admin/set-charge-url">
            <label>충전 페이지 URL:</label>
            <input type="text" name="url" placeholder="https://...">
            <button type="submit">저장</button>
        </form>
        <p>현재 설정된 URL: {{ charge_url }}</p>
    </section>

    <section>
        <h2>3. 최근 주문 20개</h2>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>상품명</th>
                    <th>가격</th>
                    <th>시간</th>
                </tr>
            </thead>
            <tbody>
            {% for o in orders %}
                <tr>
                    <td>{{ o[0] }}</td>
                    <td>{{ o[1] }}</td>
                    <td>{{ "{:,}".format(o[2]) }}원</td>
                    <td>{{ o[3] }}</td>
                </tr>
            {% endfor %}
            </tbody>
        </table>
    </section>
</body>
</html>
"""


login_html = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>RED Admin Login</title>
    <style>
        body { font-family: sans-serif; background:#111; color:#eee; display:flex; justify-content:center; align-items:center; height:100vh; }
        .box { background:#1b1b1b; padding:20px 24px; border-radius:8px; width:260px; }
        h1 { font-size:1.2rem; margin-bottom:1rem; }
        label { display:block; margin-top:0.5rem; font-size:0.85rem; }
        input[type="text"], input[type="password"] { width:100%; padding:0.4rem; margin-top:0.2rem; border-radius:4px; border:1px solid #444; background:#000; color:#eee; }
        button { margin-top:0.8rem; width:100%; padding:0.4rem; cursor:pointer; background:#e53935; border:none; color:#fff; border-radius:4px; font-weight:600; }
        .error { color:#ff6666; font-size:0.8rem; margin-top:0.5rem; }
        a { color:#4fc3f7; font-size:0.8rem; }
    </style>
</head>
<body>
    <div class="box">
        <h1>RED Admin</h1>
        <form method="post">
            <label>아이디</label>
            <input type="text" name="username" autocomplete="off">
            <label>비밀번호</label>
            <input type="password" name="password" autocomplete="off">
            <button type="submit">로그인</button>
            {% if error %}
            <div class="error">{{ error }}</div>
            {% endif %}
        </form>
        <p><a href="/">← 메인으로</a></p>
    </div>
</body>
</html>
"""

from flask import render_template_string as rts


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin"))
        else:
            error = "아이디 또는 비밀번호가 올바르지 않습니다."
    return rts(login_html, error=error)


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))


@app.route("/admin")
@login_required
def admin():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT charge_url FROM settings WHERE id = 1")
    row = cur.fetchone()
    charge_url = row[0] if row and row[0] else ""
    cur.execute(
        "SELECT id, product_name, price, created_at FROM orders ORDER BY id DESC LIMIT 20"
    )
    orders = cur.fetchall()
    conn.close()
    return rts(admin_html, charge_url=charge_url, orders=orders)


@app.route("/admin/set-points", methods=["POST"])
@login_required
def admin_set_points():
    user_id_raw = request.form.get("user_id", "").strip()
    points_raw = request.form.get("points", "").strip()
    try:
        user_id = int(user_id_raw)
        value = int(points_raw)
    except ValueError:
        return redirect("/admin")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT points FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE users SET points = ? WHERE id = ?", (value, user_id))
    else:
        cur.execute("INSERT INTO users (id, points) VALUES (?, ?)", (user_id, value))
    conn.commit()
    conn.close()

    
    try:
        content = f"<@{user_id}> 님 포인트가 {value:,}P 로 설정되었습니다."
        requests.post(WEBHOOK_URL, json={"content": content}, timeout=3)
    except Exception as e:
        print("WEBHOOK ERROR:", e)

    return redirect("/admin")


@app.route("/admin/set-charge-url", methods=["POST"])
@login_required
def admin_set_charge_url():
    url = request.form.get("url", "").strip()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE settings SET charge_url = ? WHERE id = 1", (url,))
    conn.commit()
    conn.close()
    return redirect("/admin")


if __name__ == "__main__":
    app.run(debug=True)
