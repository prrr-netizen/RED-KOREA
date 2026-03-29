from flask import Flask, render_template_string, request, jsonify, redirect
import sqlite3, os

app = Flask(__name__)

# ===== DB 설정 =====
DB_PATH = os.path.join(os.path.dirname(__file__), "shop.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 유저 포인트 (한 명만 쓴다는 가정: id=1)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            points INTEGER DEFAULT 0
        )
    """)

    # 주문 기록
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT,
            price INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 충전 수단 URL (예: 토스, 카카오페이 페이지 링크)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            charge_url TEXT
        )
    """)

    # 기본 데이터 세팅
    cur.execute("INSERT OR IGNORE INTO users (id, points) VALUES (1, 0)")
    cur.execute("INSERT OR IGNORE INTO settings (id, charge_url) VALUES (1, 'https://example.com/charge')")

    conn.commit()
    conn.close()

init_db()

# ===== 메인 화면 (유저 측) =====
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
            font-size: 1.8rem;
            font-weight: 700;
            letter-spacing: -0.5px;
            background: linear-gradient(135deg, #2b2d42, #4a4e69);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }
        .nav-links { display: flex; gap: 2rem; align-items: center; }
        .nav-links a { text-decoration: none; color: #2d2f36; font-weight: 500; transition: 0.2s; }
        .nav-links a:hover { color: #8b5f6c; }
        .cart-icon { position: relative; font-size: 1.4rem; }

        .hero {
            background: linear-gradient(120deg, #f4f1e1 0%, #e9e6d7 100%);
            padding: 4rem 2rem;
            text-align: center;
            border-bottom: 1px solid #ddd8c8;
        }
        .hero h1 { font-size: 3rem; font-weight: 700; margin-bottom: 1rem; color: #1e2a2f; }
        .hero p { font-size: 1.2rem; color: #3c4a4f; max-width: 600px; margin: 0 auto; }

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
            background: #b5838d;
            color: white;
            border: none;
            padding: 0.6rem 1rem;
            border-radius: 999px;
            font-size: 0.9rem;
            font-weight: 600;
            cursor: pointer;
        }
        .info-bar-right button:hover { background:#8d5f6d; }

        .products-section {
            max-width: 1280px;
            margin: 2.5rem auto;
            padding: 0 2rem;
        }
        .section-title {
            font-size: 1.8rem;
            font-weight: 600;
            margin-bottom: 2rem;
            border-left: 5px solid #b5838d;
            padding-left: 1rem;
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
            .hero h1 { font-size: 2rem; }
            .nav-container { flex-direction: column; gap: 1rem; }
            .nav-links { gap: 1.2rem; }
            .info-bar { flex-direction: column; align-items: flex-start; }
        }
    </style>
</head>
<body>

<div class="header">
    <div class="nav-container">
        <div class="logo"><i class="fas fa-store"></i> RED+RLNL</div>
        <div class="nav-links">
            <a href="#">홈</a>
            <a href="#">베스트</a>
            <a href="#">신상품</a>
            <a href="#">컬렉션</a>
            <div class="cart-icon">
                <i class="fas fa-shopping-bag"></i>
            </div>
        </div>
    </div>
</div>

<section class="hero">
    <h1>일상에 감각을 더하다</h1>
    <p>최고의 아이템들. 지금 만나보세요.</p>
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
        { id: 1, name: "🔴RED-trainer",    price: 13000, desc: "집중력과 몰입감을 높여주는 트레이닝 패키지", emoji: "🏋️" },
        { id: 2, name: "🔴RED-wolf",       price: 13000, desc: "공격적인 운영을 위한 하이레벨 패키지",      emoji: "🐺" },
        { id: 3, name: "🔴RED-kd-dropper", price: 7000,  desc: "KD를 확실히 떨어뜨리는 실험용 패키지",     emoji: "🎯" }
    ];

    const productGrid = document.getElementById('productGrid');
    const toastEl = document.getElementById('toastMsg');
    const pointsText = document.getElementById('pointsText');
    const chargeBtn = document.getElementById('chargeBtn');
    let toastTimer = null;

    function showToast(message) {
        if (toastTimer) clearTimeout(toastTimer);
        toastEl.textContent = message;
        toastEl.classList.add('show');
        toastTimer = setTimeout(() => {
            toastEl.classList.remove('show');
        }, 2000);
    }

    async function refreshPoints() {
        try {
            const res = await fetch("/api/points");
            const data = await res.json();
            pointsText.textContent = (data.points ?? 0).toLocaleString();
        } catch (e) {
            console.error(e);
        }
    }

    async function handleBuy(productName, price) {
        try {
            const res = await fetch("/api/buy", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name: productName, price: price })
            });
            const data = await res.json();

            if (data.ok) {
                showToast(`✅ ${productName} 구매 완료`);
                await refreshPoints();
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
            imgDiv.innerHTML = `<span style="font-size: 4rem;">${product.emoji}</span>`;

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
            if (data.url) {
                window.location.href = data.url;
            } else {
                showToast("충전 URL이 설정되지 않았습니다");
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

# 현재 포인트 조회
@app.route("/api/points")
def api_points():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT points FROM users WHERE id = 1")
    row = cur.fetchone()
    conn.close()
    points = row[0] if row else 0
    return jsonify({"points": points})

# 구매 처리: 포인트 차감 + 주문 기록
@app.route("/api/buy", methods=["POST"])
def api_buy():
    data = request.get_json()
    name = data.get("name")
    price = data.get("price")

    if not name or price is None:
        return jsonify({"ok": False, "error": "잘못된 요청입니다"}), 400

    price = int(price)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 현재 포인트 확인
    cur.execute("SELECT points FROM users WHERE id = 1")
    row = cur.fetchone()
    points = row[0] if row else 0

    if points < price:
        conn.close()
        return jsonify({"ok": False, "error": "포인트가 부족합니다"}), 400

    # 포인트 차감 + 주문 기록
    cur.execute("UPDATE users SET points = points - ? WHERE id = 1", (price,))
    cur.execute(
        "INSERT INTO orders (product_name, price) VALUES (?, ?)",
        (name, price),
    )
    conn.commit()
    conn.close()

    return jsonify({"ok": True})

# 충전하기 버튼이 이동할 URL 반환
@app.route("/api/charge-url")
def api_charge_url():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT charge_url FROM settings WHERE id = 1")
    row = cur.fetchone()
    conn.close()
    url = row[0] if row and row[0] else "https://example.com/charge"
    return jsonify({"url": url})

# ===== 간단 어드민 페이지 (/admin) =====
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
    </style>
</head>
<body>
    <h1>RED Admin</h1>

    <section>
        <h2>1. 유저 포인트 수동 설정</h2>
        <form method="post" action="/admin/set-points">
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

from flask import render_template_string as rts

@app.route("/admin")
def admin():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT charge_url FROM settings WHERE id = 1")
    row = cur.fetchone()
    charge_url = row[0] if row and row[0] else ""
    cur.execute("SELECT id, product_name, price, created_at FROM orders ORDER BY id DESC LIMIT 20")
    orders = cur.fetchall()
    conn.close()
    return rts(admin_html, charge_url=charge_url, orders=orders)

@app.route("/admin/set-points", methods=["POST"])
def admin_set_points():
    points = request.form.get("points", "").strip()
    try:
        value = int(points)
    except ValueError:
        return redirect("/admin")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE users SET points = ? WHERE id = 1", (value,))
    conn.commit()
    conn.close()
    return redirect("/admin")

@app.route("/admin/set-charge-url", methods=["POST"])
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
