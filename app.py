import os
import sqlite3
import requests
from flask import (
    Flask,
    render_template_string as rts,
    request,
    jsonify,
    redirect,
    url_for,
    session,
)

app = Flask(__name__)

# 기본 설정
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


# ===== 메인 화면 (최종판: 공지 마퀴 + 개성 있는 디자인) =====
index_html = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>RED | 프리미엄 온라인 샵</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;14..32,400;14..32,600;14..32,700;14..32,800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Inter', sans-serif;
        }

        body {
            background: #0a0a0c;
            color: #ededee;
            line-height: 1.5;
        }

        /* 헤더 */
        .header {
            background: rgba(10, 10, 12, 0.85);
            backdrop-filter: blur(16px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            padding: 1rem 2rem;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .nav-container {
            max-width: 1280px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }

        .logo {
            display: flex;
            align-items: center;
            gap: 0.6rem;
        }

        .logo img {
            height: 32px;
            filter: drop-shadow(0 0 6px rgba(255, 75, 110, 0.4));
        }

        .logo-text {
            font-size: 1.6rem;
            font-weight: 800;
            background: linear-gradient(135deg, #ff4b6e, #ff8c42);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            letter-spacing: -0.5px;
        }

        /* 우측 영역 (포인트 + 액션) */
        .right-area {
            display: flex;
            align-items: center;
            gap: 1.5rem;
        }

        .points-badge {
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(4px);
            padding: 0.45rem 1rem;
            border-radius: 60px;
            font-weight: 600;
            font-size: 0.9rem;
            border: 1px solid rgba(255, 75, 110, 0.3);
            transition: all 0.2s;
        }

        .points-badge i {
            color: #ffb347;
            margin-right: 0.4rem;
        }

        .points-badge span {
            color: #ffb347;
            font-weight: 800;
        }

        .action-buttons {
            display: flex;
            gap: 0.8rem;
        }

        .discord-btn {
            background: #5865f2;
            color: white;
            padding: 0.45rem 1.1rem;
            border-radius: 999px;
            font-size: 0.85rem;
            font-weight: 600;
            text-decoration: none;
            transition: 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
        }

        .discord-btn:hover {
            background: #4752c4;
            transform: translateY(-2px);
        }

        .charge-btn {
            background: linear-gradient(135deg, #ff4b6e, #ff6b4a);
            color: white;
            border: none;
            padding: 0.45rem 1.2rem;
            border-radius: 999px;
            font-weight: 700;
            font-size: 0.85rem;
            cursor: pointer;
            transition: 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            box-shadow: 0 4px 12px rgba(255, 75, 110, 0.3);
        }

        .charge-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(255, 75, 110, 0.4);
        }

        /* 공지 마퀴 (CSS 롤링) */
        .notice-bar {
            background: linear-gradient(90deg, #1e1a2f, #2a1e2c, #1e1a2f);
            border-bottom: 1px solid rgba(255, 75, 110, 0.3);
            border-top: 1px solid rgba(255, 75, 110, 0.2);
            padding: 0.7rem 0;
            overflow: hidden;
            white-space: nowrap;
        }

        .notice-track {
            display: inline-block;
            animation: scrollNotice 25s linear infinite;
        }

        .notice-item {
            display: inline-block;
            padding: 0 2rem;
            font-size: 0.9rem;
            font-weight: 500;
        }

        .notice-item i {
            color: #ff4b6e;
            margin-right: 0.5rem;
        }

        .notice-item strong {
            color: #ffb347;
        }

        @keyframes scrollNotice {
            0% { transform: translateX(0); }
            100% { transform: translateX(-50%); }
        }

        /* 히어로 */
        .hero {
            background: #000;
            padding: 0;
        }

        .hero-inner {
            max-width: 1280px;
            margin: 0 auto;
            height: 280px;
            background-image: url('https://cdn.discordapp.com/attachments/1084455385848627250/1488158674340937739/36a47df6e588163a.png');
            background-size: cover;
            background-position: center 30%;
            border-radius: 0 0 32px 32px;
            box-shadow: 0 10px 30px -10px rgba(0,0,0,0.5);
        }

        /* 상품 섹션 */
        .products-section {
            max-width: 1280px;
            margin: 3rem auto;
            padding: 0 2rem;
        }

        .section-title {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 2.5rem;
            position: relative;
            display: inline-block;
            background: linear-gradient(135deg, #fff, #ffb347);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }

        /* 그래뉼라 애니메이션 (입자 효과) */
        .section-title::before {
            content: "";
            position: absolute;
            bottom: -8px;
            left: 0;
            width: 100%;
            height: 3px;
            background: linear-gradient(90deg, #ff4b6e, #ffb347);
            border-radius: 4px;
            animation: granularMove 2s ease-in-out infinite alternate;
        }

        @keyframes granularMove {
            0% { transform: scaleX(0.8); opacity: 0.6; }
            100% { transform: scaleX(1); opacity: 1; }
        }

        .product-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 2rem;
        }

        .product-card {
            background: rgba(20, 20, 26, 0.7);
            backdrop-filter: blur(8px);
            border-radius: 28px;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: all 0.3s cubic-bezier(0.2, 0.9, 0.4, 1.1);
            cursor: pointer;
        }

        .product-card:hover {
            transform: translateY(-8px) scale(1.01);
            border-color: rgba(255, 75, 110, 0.5);
            box-shadow: 0 20px 35px -12px rgba(255, 75, 110, 0.25);
        }

        .product-img {
            width: 100%;
            height: 280px;
            background: #111216;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: transform 0.4s ease;
        }

        .product-card:hover .product-img {
            transform: scale(1.02);
        }

        .product-img img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .product-info {
            padding: 1.6rem;
        }

        .product-title {
            font-weight: 700;
            font-size: 1.3rem;
            margin-bottom: 0.5rem;
            letter-spacing: -0.3px;
        }

        .product-price {
            color: #ff6b4a;
            font-weight: 800;
            font-size: 1.5rem;
            margin: 0.6rem 0;
        }

        .product-desc {
            color: #a0a0b0;
            font-size: 0.85rem;
            margin-bottom: 1.2rem;
        }

        .buy-btn {
            background: linear-gradient(135deg, #ff4b6e, #ff6b4a);
            color: white;
            border: none;
            padding: 0.8rem;
            width: 100%;
            border-radius: 60px;
            font-weight: 700;
            cursor: pointer;
            transition: 0.2s;
            font-size: 0.9rem;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }

        .buy-btn:hover {
            opacity: 0.9;
            transform: scale(0.98);
        }

        /* 토스트 */
        .toast {
            position: fixed;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%) translateY(100px);
            background: #1e1a2f;
            backdrop-filter: blur(12px);
            color: #fff;
            padding: 12px 28px;
            border-radius: 60px;
            font-weight: 500;
            font-size: 0.9rem;
            z-index: 1000;
            transition: transform 0.25s ease;
            border: 1px solid rgba(255, 75, 110, 0.5);
            white-space: nowrap;
            pointer-events: none;
        }

        .toast.show {
            transform: translateX(-50%) translateY(0);
        }

        .footer {
            background: #050507;
            color: #6c6c7a;
            text-align: center;
            padding: 2rem;
            margin-top: 3rem;
            font-size: 0.8rem;
            border-top: 1px solid rgba(255,255,255,0.05);
        }

        @media (max-width: 680px) {
            .nav-container {
                flex-direction: column;
                align-items: stretch;
            }
            .right-area {
                justify-content: space-between;
            }
            .notice-item {
                font-size: 0.75rem;
            }
            .hero-inner {
                height: 200px;
            }
            .product-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>

<div class="header">
    <div class="nav-container">
        <div class="logo">
            <img src="https://cdn.discordapp.com/attachments/1084455385848627250/1488158725670961254/8f7d09ac9d5ba195.png" alt="RED">
            <span class="logo-text">RED+RLNL</span>
        </div>
        <div class="right-area">
            <div class="points-badge">
                <i class="fas fa-coins"></i> <span id="pointsText">0</span> P
            </div>
            <div class="action-buttons">
                <a href="https://discord.gg/q6nJpYuFB8" class="discord-btn"><i class="fab fa-discord"></i> 디스코드</a>
                <button id="chargeBtn" class="charge-btn"><i class="fas fa-bolt"></i> 충전하기</button>
            </div>
        </div>
    </div>
</div>

<!-- 공지 마퀴 (롤링 배너) -->
<div class="notice-bar">
    <div class="notice-track">
        <span class="notice-item"><i class="fas fa-fire"></i> <strong>HOT</strong>오픈 기념</span>
        <span class="notice-item"><i class="fas fa-gift"></i> 언제든지 문의 환영 <strong>고객 응대</strong> 신속 정확</span>
        <span class="notice-item"><i class="fas fa-headset"></i> 문의는 디스코드 채널에서 24시간 응대</span>
        <span class="notice-item"><i class="fas fa-charging-station"></i> 충전 5만원 이상 시 <strong>보너스 20%</strong> 적립</span>
        <!-- 복제본 (무한 롤링) -->
        <span class="notice-item"><i class="fas fa-fire"></i> <strong>HOT</strong> 3월 한정 특가! 전 상품 10% 추가 할인</span>
        <span class="notice-item"><i class="fas fa-gift"></i> 신규 회원 가입 시 <strong>5,000P</strong> 즉시 지급</span>
        <span class="notice-item"><i class="fas fa-headset"></i> 문의는 디스코드 채널에서 24시간 응대</span>
        <span class="notice-item"><i class="fas fa-charging-station"></i> 충전 5만원 이상 시 <strong>보너스 20%</strong> 적립</span>
    </div>
</div>

<section class="hero">
    <div class="hero-inner"></div>
</section>

<section class="products-section">
    <div class="section-title">✨ 오늘의 추천 상품</div>
    <div class="product-grid" id="productGrid"></div>
</section>

<div class="footer">
    <p>© 2026 RED | 프리미엄 서비스</p>
</div>

<div id="toastMsg" class="toast"></div>

<script>
    const products = [
        { id: 1, name: "🔴𝙍𝙀𝘿-𝗪𝗢𝗟𝗙-𝗟𝗜𝗧𝗘", price: 13000, desc: "라이트 버전으로 부담 없이 경험해보는 패키지", emoji: "🏋️", img: null },
        { id: 2, name: "🔴RED-𝗪𝗢𝗟𝗙",         price: 13000, desc: "공격적인 운영을 위한 하이레벨 패키지",      emoji: "🐺", img: "https://cdn.discordapp.com/attachments/1083101135096795201/1488186254561378425/WOLF.webp" },
        { id: 3, name: "🔴RED-kd-dropper",      price: 7000,  desc: "집중력과 몰입감을 높여주는 트레이닝 패키지", emoji: "🎯", img: null }
    ];
    // 라이트 버전 이미지 별도 처리
    const liteImg = "https://cdn.discordapp.com/attachments/1084455385848627250/1488164919663788065/WOLF_LITE.png";

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

            if (product.name === "🔴RED-𝗪𝗢𝗟𝗙" && product.img) {
                imgDiv.innerHTML = `<img src="${product.img}" alt="RED-wolf">`;
            } else if (product.name === "🔴𝙍𝙀𝘿-𝗪𝗢𝗟𝗙-𝗟𝗜𝗧𝗘") {
                imgDiv.innerHTML = `<img src="${liteImg}" alt="RED-WOLF-LITE">`;
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
    return rts(index_html)


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
        content = (
            f"<@{user_id}> 님 포인트가 {value:,}P 로 설정되었습니다.\\n"
            "티켓 문의 후 충전 요청하신 건에 대해, 입금 확인 및 관리자 확정 처리 완료되었습니다."
        )
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
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
