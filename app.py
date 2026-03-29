from flask import Flask, render_template_string, request, jsonify
import sqlite3, os

app = Flask(__name__)

# ===== 주문 DB 설정 =====
DB_PATH = os.path.join(os.path.dirname(__file__), "orders.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT,
            price INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ===== 메인 화면 =====
index_html = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>RED | 온라인 샵</title>
    <!-- Google Fonts & Font Awesome -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;14..32,400;14..32,600;14..32,700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Inter', sans-serif;
        }

        body {
            background-color: #fafaf8;
            color: #1c1c1c;
            line-height: 1.5;
        }

        /* 헤더 */
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

        .nav-links {
            display: flex;
            gap: 2rem;
            align-items: center;
        }

        .nav-links a {
            text-decoration: none;
            color: #2d2f36;
            font-weight: 500;
            transition: 0.2s;
        }

        .nav-links a:hover {
            color: #8b5f6c;
        }

        .cart-icon {
            position: relative;
            font-size: 1.4rem;
        }

        /* 히어로 섹션 */
        .hero {
            background: linear-gradient(120deg, #f4f1e1 0%, #e9e6d7 100%);
            padding: 4rem 2rem;
            text-align: center;
            border-bottom: 1px solid #ddd8c8;
        }

        .hero h1 {
            font-size: 3rem;
            font-weight: 700;
            margin-bottom: 1rem;
            color: #1e2a2f;
        }

        .hero p {
            font-size: 1.2rem;
            color: #3c4a4f;
            max-width: 600px;
            margin: 0 auto;
        }

        /* 상품 그리드 */
        .products-section {
            max-width: 1280px;
            margin: 3rem auto;
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

        .product-info {
            padding: 1.5rem;
        }

        .product-title {
            font-weight: 700;
            font-size: 1.25rem;
            margin-bottom: 0.5rem;
        }

        .product-price {
            color: #b5838d;
            font-weight: 700;
            font-size: 1.3rem;
            margin: 0.5rem 0;
        }

        .product-desc {
            color: #5a5e66;
            font-size: 0.85rem;
            margin-bottom: 1rem;
        }

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

        .buy-btn:hover {
            background: #2e3e44;
            transform: scale(0.98);
        }

        /* 토스트 알림 */
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

        .toast.show {
            transform: translateX(-50%) translateY(0);
        }

        /* 푸터 */
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
        }
    </style>
</head>
<body>

<div class="header">
    <div class="nav-container">
        <div class="logo"><i class="fas fa-store"></i> MODERNSTORE</div>
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
    <p>미니멀리즘과 따뜻함이 공존하는 아이템들. 지금 만나보세요.</p>
</section>

<section class="products-section">
    <div class="section-title">✨ 오늘의 추천 상품</div>
    <div class="product-grid" id="productGrid"></div>
</section>

<div class="footer">
    <p>&copy; 2026 RED</p>
</div>

<div id="toastMsg" class="toast">🛍️ 장바구니에 담았습니다</div>

<script>
    // 상품 데이터 (더미)
    const products = [
        {
            id: 1,
            name: "울 저지 가디건",
            price: 89000,
            desc: "부드러운 터치감의 오버핏 가디건",
            emoji: "🧥"
        },
        {
            id: 2,
            name: "미니멀 무드 백",
            price: 49000,
            desc: "데일리로 갖기 좋은 에코백",
            emoji: "👜"
        },
        {
            id: 3,
            name: "세라믹 핸드 드립 세트",
            price: 67000,
            desc: "취미를 특별하게, 커피 타임",
            emoji: "☕"
        },
        {
            id: 4,
            name: "무드등 + 디퓨저 세트",
            price: 55000,
            desc: "은은한 조명과 향기, 힐링 패키지",
            emoji: "🕯️"
        },
        {
            id: 5,
            name: "오버사이즈 니트",
            price: 72000,
            desc: "포근한 겨울 필수템",
            emoji: "🧶"
        },
        {
            id: 6,
            name: "빈티지 레트로 시계",
            price: 38000,
            desc: "아날로그 감성 인테리어",
            emoji: "⏰"
        }
    ];

    const productGrid = document.getElementById('productGrid');
    const toastEl = document.getElementById('toastMsg');
    let toastTimer = null;

    function showToast(message) {
        if (toastTimer) clearTimeout(toastTimer);
        toastEl.textContent = message || "🛍️ 장바구니에 담았습니다";
        toastEl.classList.add('show');
        toastTimer = setTimeout(() => {
            toastEl.classList.remove('show');
        }, 2000);
    }

    async function handleBuy(productName, price) {
        showToast(`✅ ${productName} - ${price.toLocaleString()}원 담기 완료 (데모)`);

        try {
            await fetch("/api/buy", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: productName,
                    price: price
                })
            });
        } catch (e) {
            console.error(e);
        }

        console.log(`[구매시뮬] 상품: ${productName}, 가격: ${price}`);
    }

    // 상품 카드 렌더링
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
            btn.innerHTML = '<i class="fas fa-shopping-cart"></i> 바로 구매하기';
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

    renderProducts();
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(index_html)

# 주문 기록 받는 API
@app.route("/api/buy", methods=["POST"])
def api_buy():
    data = request.get_json()
    name = data.get("name")
    price = data.get("price")

    if not name or price is None:
        return jsonify({"ok": False, "error": "invalid data"}), 400

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO orders (product_name, price) VALUES (?, ?)",
        (name, int(price)),
    )
    conn.commit()
    conn.close()

    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(debug=True)
