import os
import sqlite3
import requests
import random
import string
import re
import threading
import time
from datetime import datetime
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

# ==============================
# 기본 설정
# ==============================
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change")
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "dev-pass-change")

# 디스코드 OAuth2 설정 (본인 값으로 변경)
DISCORD_CLIENT_ID = "1478639969009406004"
DISCORD_CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET", "여기에_시크릿키")
DISCORD_REDIRECT_URI = "https://rani-mall.xyz/auth/callback"

# 웹훅 URL (관리자 알림용)
WEBHOOK_URL = "https://discord.com/api/webhooks/1488231305396224041/Fa_z7Wihwf9-k79aGNcvaLNj3emxWYxlFoD6xVGkgLxzZKig3Uc7MQpL8Nk93d4Pyfat"

# Bank API 설정
BANK_API_URL = "https://api.bankapi.co.kr/v1/transactions"
BANK_API_KEY = os.getenv("BANK_API_KEY", "pk_live_c5a38059a67a2c9bb87c77936256de70")
BANK_SECRET_KEY = os.getenv("BANK_SECRET_KEY", "sk_client_minimal_59dfc643573e982cbbf1b71602f9cbad")
BANK_CODE = "NH"
ACCOUNT_NUMBER = "3521617659683"
ACCOUNT_PASSWORD = os.getenv("ACCOUNT_PASSWORD", "1003")
RESIDENT_NUMBER = os.getenv("RESIDENT_NUMBER", "070117")

DB_PATH = os.path.join(os.path.dirname(__file__), "shop.db")

# ==============================
# DB 초기화 (자동충전 테이블 추가)
# ==============================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, points INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, product_name TEXT, price INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    cur.execute("CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, charge_url TEXT)")
    cur.execute("INSERT OR IGNORE INTO settings (id, charge_url) VALUES (1, 'https://discord.gg/q6nJpYuFB8')")
    
    # 자동충전 요청 테이블
    cur.execute("""
        CREATE TABLE IF NOT EXISTS charge_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            amount INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            processed INTEGER DEFAULT 0
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS processed_deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_date TEXT,
            transaction_time TEXT,
            amount INTEGER,
            order_number TEXT,
            user_id INTEGER,
            processed_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ==============================
# 자동충전 헬퍼 함수
# ==============================
def generate_order_number():
    while True:
        order_num = ''.join(random.choices(string.digits, k=6))
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id FROM charge_requests WHERE order_number = ?", (order_num,))
        exists = cur.fetchone()
        conn.close()
        if not exists:
            return order_num

def create_charge_request(user_id, amount):
    order_num = generate_order_number()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO charge_requests (order_number, user_id, amount, processed) VALUES (?, ?, ?, 0)",
                (order_num, user_id, amount))
    conn.commit()
    conn.close()
    return order_num

def add_points(user_id, amount):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT points FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    if row:
        new_balance = row[0] + amount
        cur.execute("UPDATE users SET points = ? WHERE id = ?", (new_balance, user_id))
    else:
        new_balance = amount
        cur.execute("INSERT INTO users (id, points) VALUES (?, ?)", (user_id, new_balance))
    conn.commit()
    conn.close()
    return new_balance

def get_charge_request_by_order(order_num):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id, amount, processed FROM charge_requests WHERE order_number = ?", (order_num,))
    row = cur.fetchone()
    conn.close()
    return {"user_id": row[0], "amount": row[1], "processed": row[2]} if row else None

def mark_charge_request_processed(order_num):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE charge_requests SET processed = 1 WHERE order_number = ?", (order_num,))
    conn.commit()
    conn.close()

def is_deposit_processed(order_num):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id FROM processed_deposits WHERE order_number = ?", (order_num,))
    row = cur.fetchone()
    conn.close()
    return row is not None

def mark_deposit_processed(transaction_date, transaction_time, amount, order_num, user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO processed_deposits (transaction_date, transaction_time, amount, order_number, user_id) VALUES (?, ?, ?, ?, ?)",
                (transaction_date, transaction_time, amount, order_num, user_id))
    conn.commit()
    conn.close()

# ==============================
# Bank API 호출 함수 (자동충전 엔진)
# ==============================
def fetch_today_deposits():
    today = datetime.now().strftime("%Y%m%d")
    headers = {
        "Authorization": f"Bearer {BANK_API_KEY}:{BANK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "bankCode": BANK_CODE,
        "accountNumber": ACCOUNT_NUMBER,
        "accountPassword": ACCOUNT_PASSWORD,
        "residentNumber": RESIDENT_NUMBER,
        "startDate": today,
        "endDate": today
    }
    try:
        resp = requests.post(BANK_API_URL, json=payload, headers=headers, timeout=(10, 60))
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                return data.get("transactions", [])
            else:
                print(f"[BANK_API] 응답 실패: {data}")
                return []
        else:
            print(f"[BANK_API] HTTP {resp.status_code}: {resp.text}")
            return []
    except Exception as e:
        print(f"[BANK_API] 예외: {e}")
        return []

def process_auto_charge():
    """은행 API를 호출하여 입금 내역을 확인하고 자동 충전"""
    print("[자동충전] 입금 확인 중...")
    deposits = fetch_today_deposits()
    if not deposits:
        return

    for tx in deposits:
        if tx.get("type") != "deposit":
            continue

        # 모든 문자열 필드를 하나로 합침 (주문번호 검색)
        text_fields = [
            tx.get("memo", ""),
            tx.get("description", ""),
            tx.get("displayName", ""),
            tx.get("counterparty", ""),
            tx.get("message", ""),
            tx.get("memo1", ""),
            tx.get("memo2", ""),
        ]
        raw_text = " ".join(str(f) for f in text_fields if f)
        if not raw_text.strip():
            continue

        match = re.search(r"\b(\d{6})\b", raw_text)
        if not match:
            continue

        order_num = match.group(1)
        if is_deposit_processed(order_num):
            continue

        req = get_charge_request_by_order(order_num)
        if not req or req["processed"] == 1:
            continue

        user_id = req["user_id"]
        amount = tx.get("amount", 0)
        if amount <= 0:
            continue

        # 포인트 지급
        new_balance = add_points(user_id, amount)
        mark_charge_request_processed(order_num)
        mark_deposit_processed(tx["date"], tx["time"], amount, order_num, user_id)

        # DM 전송 (웹훅 대신 봇이 DM을 보내야 하지만, 여기서는 간단히 웹훅으로 알림)
        content = f"💰 자동 충전 완료!\n유저 ID: {user_id}\n금액: {amount:,}P\n잔여 포인트: {new_balance:,}P\n주문번호: {order_num}"
        try:
            requests.post(WEBHOOK_URL, json={"content": content}, timeout=3)
        except Exception as e:
            print(f"[WEBHOOK] 오류: {e}")

        print(f"[자동충전] user {user_id} 에게 {amount}P 충전됨 (주문번호: {order_num})")

def start_auto_charge_loop():
    """백그라운드 스레드에서 60초마다 자동충전 실행"""
    def loop():
        while True:
            try:
                process_auto_charge()
            except Exception as e:
                print(f"[자동충전 루프 오류] {e}")
            time.sleep(60)
    thread = threading.Thread(target=loop, daemon=True)
    thread.start()

# ==============================
# 디스코드 OAuth2 라우트
# ==============================
def get_discord_user(access_token):
    resp = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    if resp.status_code == 200:
        return resp.json()
    return None

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
        "scope": "identify"
    }
    resp = requests.post("https://discord.com/api/oauth2/token", data=data)
    if resp.status_code != 200:
        return redirect(url_for("index"))
    
    token_data = resp.json()
    access_token = token_data.get("access_token")
    user = get_discord_user(access_token)
    if user:
        session["user_id"] = int(user["id"])
        session["username"] = f"{user['username']}#{user['discriminator']}"
        session["avatar"] = f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}.png" if user["avatar"] else None
    return redirect(url_for("index"))

@app.route("/auth/logout")
def auth_logout():
    session.clear()
    return redirect(url_for("index"))

# ==============================
# API 엔드포인트
# ==============================
@app.route("/api/points")
def api_points():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"points": 0})
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT points FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    points = row[0] if row else 0
    return jsonify({"points": points})

@app.route("/api/charge-request", methods=["POST"])
def api_charge_request():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"ok": False, "error": "로그인이 필요합니다."}), 401
    
    data = request.get_json()
    amount = data.get("amount")
    if not amount or amount < 1000:
        return jsonify({"ok": False, "error": "최소 충전 금액은 1,000원입니다."}), 400
    
    order_num = create_charge_request(user_id, amount)
    
    # 관리자 웹훅 알림
    content = (
        f"💳 **충전 요청 접수**\n"
        f"유저 ID: <@{user_id}>\n"
        f"금액: {amount:,}원\n"
        f"주문번호: `{order_num}`\n"
        f"계좌로 {amount:,}원을 입금해 주세요.\n"
        f"입금 시 메모에 주문번호 `{order_num}`를 꼭 입력해 주세요."
    )
    try:
        requests.post(WEBHOOK_URL, json={"content": content}, timeout=3)
    except Exception as e:
        print(f"웹훅 오류: {e}")
    
    return jsonify({"ok": True, "order_number": order_num})

# ==============================
# 메인 HTML (디스코드 로그인 + 계좌 정보 + 충전 요청)
# ==============================
index_html = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RED | 프리미엄 샵</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; font-family:'Inter',sans-serif; }
        body { background:#0a0a0c; color:#ededee; }
        .container { max-width:1280px; margin:0 auto; padding:2rem; }
        .header { display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem; margin-bottom:2rem; }
        .logo { font-size:1.8rem; font-weight:800; background:linear-gradient(135deg,#ff4b6e,#ff8c42); -webkit-background-clip:text; background-clip:text; color:transparent; }
        .user-info { background:rgba(255,255,255,0.08); padding:0.5rem 1rem; border-radius:60px; display:flex; align-items:center; gap:1rem; }
        .user-info img { width:32px; height:32px; border-radius:50%; }
        .points { color:#ffb347; font-weight:700; }
        .account-box { background:rgba(20,20,26,0.7); border-radius:28px; padding:1.5rem; margin:2rem 0; border:1px solid rgba(255,75,110,0.3); text-align:center; }
        .account-box h2 { margin-bottom:1rem; }
        .account-number { font-size:1.8rem; font-weight:800; background:linear-gradient(135deg,#fff,#ffb347); -webkit-background-clip:text; background-clip:text; color:transparent; letter-spacing:2px; }
        .charge-btn { background:linear-gradient(135deg,#ff4b6e,#ff6b4a); border:none; padding:0.8rem 2rem; border-radius:60px; font-weight:700; color:white; cursor:pointer; margin-top:1rem; }
        .footer { text-align:center; margin-top:3rem; color:#6c6c7a; }
        .toast { position:fixed; bottom:30px; left:50%; transform:translateX(-50%); background:#1e1a2f; padding:10px 24px; border-radius:60px; z-index:1000; transition:0.2s; opacity:0; pointer-events:none; white-space:nowrap; }
        .toast.show { opacity:1; }
        .modal { display:none; position:fixed; top:50%; left:50%; transform:translate(-50%,-50%); background:#1e1a2f; padding:2rem; border-radius:20px; z-index:1000; width:300px; text-align:center; }
        .modal input { width:100%; padding:0.5rem; margin:1rem 0; border-radius:8px; border:none; }
        .modal button { background:#ff4b6e; border:none; padding:0.5rem 1rem; border-radius:8px; color:white; cursor:pointer; margin:0 0.5rem; }
        .overlay { display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.7); z-index:999; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">RED+RLNL</div>
            <div class="user-info">
                {% if user_id %}
                    <img src="{{ avatar }}" alt="avatar">
                    <span>{{ username }}</span>
                    <span class="points"><i class="fas fa-coins"></i> <span id="points">0</span> P</span>
                    <a href="/auth/logout" style="color:#ff6b4a; margin-left:0.5rem;"><i class="fas fa-sign-out-alt"></i></a>
                {% else %}
                    <a href="/auth/login" class="discord-btn" style="background:#5865f2; padding:0.5rem 1rem; border-radius:60px; text-decoration:none; color:white;"><i class="fab fa-discord"></i> 디스코드 로그인</a>
                {% endif %}
            </div>
        </div>

        {% if user_id %}
        <div class="account-box">
            <h2><i class="fas fa-university"></i> 입금 계좌 정보</h2>
            <p>아래 계좌로 입금 후, 메모에 주문번호를 꼭 입력해 주세요.</p>
            <p class="account-number">3521617659683</p>
            <p>예금주: 김대훈 | 농협은행</p>
            <button id="chargeBtn" class="charge-btn"><i class="fas fa-bolt"></i> 충전 요청</button>
        </div>
        {% endif %}

        <div class="footer">
            <p>© 2026 RED | 프리미엄 서비스</p>
        </div>
    </div>

    <div id="toastMsg" class="toast"></div>
    <div id="modalOverlay" class="overlay"></div>
    <div id="chargeModal" class="modal">
        <h3>충전 금액 입력</h3>
        <input type="number" id="chargeAmount" placeholder="금액 (원)" min="1000" step="1000">
        <div>
            <button id="confirmChargeBtn">요청</button>
            <button id="closeModalBtn">닫기</button>
        </div>
    </div>

    <script>
        const userLoggedIn = {{ "true" if user_id else "false" }};
        let toastTimer = null;
        function showToast(msg) {
            const toast = document.getElementById('toastMsg');
            if (toastTimer) clearTimeout(toastTimer);
            toast.textContent = msg;
            toast.classList.add('show');
            toastTimer = setTimeout(() => toast.classList.remove('show'), 3000);
        }
        async function refreshPoints() {
            if (!userLoggedIn) return;
            try {
                const res = await fetch('/api/points');
                const data = await res.json();
                document.getElementById('points').textContent = (data.points || 0).toLocaleString();
            } catch(e) { console.error(e); }
        }
        refreshPoints();
        setInterval(refreshPoints, 30000);

        if (userLoggedIn) {
            const chargeBtn = document.getElementById('chargeBtn');
            const modal = document.getElementById('chargeModal');
            const overlay = document.getElementById('modalOverlay');
            const confirmBtn = document.getElementById('confirmChargeBtn');
            const closeBtn = document.getElementById('closeModalBtn');
            const amountInput = document.getElementById('chargeAmount');

            function showModal() { modal.style.display = 'block'; overlay.style.display = 'block'; }
            function hideModal() { modal.style.display = 'none'; overlay.style.display = 'none'; }

            chargeBtn.addEventListener('click', showModal);
            closeBtn.addEventListener('click', hideModal);
            overlay.addEventListener('click', hideModal);

            confirmBtn.addEventListener('click', async () => {
                const amount = parseInt(amountInput.value);
                if (!amount || amount < 1000) {
                    alert("1,000원 이상 입력하세요.");
                    return;
                }
                try {
                    const res = await fetch('/api/charge-request', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ amount: amount })
                    });
                    const data = await res.json();
                    if (data.ok) {
                        alert(`충전 요청이 접수되었습니다. 주문번호: ${data.order_number}\n아래 계좌로 입금 후 메모에 주문번호를 입력해 주세요.\n계좌: 3521617659683 (농협, 김대훈)`);
                        hideModal();
                    } else {
                        alert(data.error || "오류 발생");
                    }
                } catch(e) {
                    alert("네트워크 오류");
                }
            });
        }
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return rts(index_html, user_id=session.get("user_id"), username=session.get("username"), avatar=session.get("avatar"))

# ==============================
# 관리자 라우트 (간단 유지)
# ==============================
login_html = """
<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"><title>RED Admin Login</title></head>
<body style="background:#111;color:#eee;display:flex;justify-content:center;align-items:center;height:100vh;">
    <div style="background:#1b1b1b;padding:20px;border-radius:8px;width:260px;">
        <h1>RED Admin</h1>
        <form method="post">
            <input type="text" name="username" placeholder="아이디" style="width:100%;margin-bottom:10px;"><br>
            <input type="password" name="password" placeholder="비밀번호" style="width:100%;margin-bottom:10px;"><br>
            <button type="submit">로그인</button>
            {% if error %}<div style="color:#ff6666;">{{ error }}</div>{% endif %}
        </form>
    </div>
</body>
</html>
"""

admin_html = """
<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"><title>RED Admin</title></head>
<body style="background:#111;color:#eee;padding:20px;">
    <h1>RED Admin</h1>
    <p><a href="/admin/logout">로그아웃</a></p>
    <section>
        <h2>유저 포인트 수동 설정</h2>
        <form method="post" action="/admin/set-points">
            <label>디스코드 유저 ID:</label>
            <input type="text" name="user_id"><br>
            <label>포인트 값:</label>
            <input type="text" name="points"><br>
            <button type="submit">저장</button>
        </form>
    </section>
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
def admin():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    return rts(admin_html)

@app.route("/admin/set-points", methods=["POST"])
def admin_set_points():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
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
    return redirect("/admin")

# ==============================
# 앱 실행 (자동충전 루프 시작)
# ==============================
if __name__ == "__main__":
    # 백그라운드 자동충전 스레드 시작
    start_auto_charge_loop()
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
