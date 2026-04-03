import os
import sqlite3
import requests
import random
import string
import re
import threading
import time
import asyncio
import logging
from datetime import datetime
from itertools import cycle
from pathlib import Path

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
from discord.ext import commands, tasks
from dotenv import load_dotenv

# ==============================
# 기본 설정
# ==============================
logging.getLogger("discord.gateway").setLevel(logging.WARNING)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change")
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "dev-pass-change")

# 디스코드 OAuth2 설정
DISCORD_CLIENT_ID = "1478639969009406004"
DISCORD_CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET", "여기에_시크릿키")
DISCORD_REDIRECT_URI = "https://your-app-name.onrender.com/auth/callback"  # 배포 시 실제 주소로 변경

# 웹훅 URL (관리자 알림용)
WEBHOOK_URL = "https://discord.com/api/webhooks/1488231305396224041/Fa_z7Wihwf9-k79aGNcvaLNj3emxWYxlFoD6xVGkgLxzZKig3Uc7MQpL8Nk93d4Pyfat"

# Bank API 설정
BANK_API_URL = "https://api.bankapi.co.kr/v1/transactions"
BANK_API_KEY = os.environ.get("BANK_API_KEY", "pk_live_c5a38059a67a2c9bb87c77936256de70")
BANK_SECRET_KEY = os.environ.get("BANK_SECRET_KEY", "sk_client_minimal_59dfc643573e982cbbf1b71602f9cbad")
BANK_CODE = "NH"
ACCOUNT_NUMBER = "3521617659683"
ACCOUNT_PASSWORD = os.environ.get("ACCOUNT_PASSWORD", "1003")
RESIDENT_NUMBER = os.environ.get("RESIDENT_NUMBER", "070117")

DB_PATH = os.path.join(os.path.dirname(__file__), "shop.db")

# ==============================
# 디스코드 봇 설정
# ==============================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=".", intents=intents)

ADMIN_CHANNEL_ID = 1488221287531679915
BUY_LOG_CHANNEL_ID = 1488221128286802143
REVIEW_CHANNEL_ID = 1487603259773419641
STATUS_MESSAGES = ["상담 환영", "문의는 티켓"]
status_cycle = cycle(STATUS_MESSAGES)
BUYER_ROLE_NAME = "구매자"

# ==============================
# DB 초기화
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
# 공통 DB 함수
# ==============================
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

def get_points(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT points FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0

def create_charge_request(user_id, amount):
    while True:
        order_num = ''.join(random.choices(string.digits, k=6))
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id FROM charge_requests WHERE order_number = ?", (order_num,))
        exists = cur.fetchone()
        conn.close()
        if not exists:
            break
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO charge_requests (order_number, user_id, amount, processed) VALUES (?, ?, ?, 0)",
                (order_num, user_id, amount))
    conn.commit()
    conn.close()
    return order_num

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
# Bank API 자동충전 엔진 (백그라운드 스레드)
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
        resp = requests.post(BANK_API_URL, json=payload, headers=headers, timeout=(10, 30))
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
    deposits = fetch_today_deposits()
    if not deposits:
        return
    for tx in deposits:
        if tx.get("type") != "deposit":
            continue
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
        new_balance = add_points(user_id, amount)
        mark_charge_request_processed(order_num)
        mark_deposit_processed(tx["date"], tx["time"], amount, order_num, user_id)
        # DM 보내기 (봇이 켜져 있을 때만)
        asyncio.run_coroutine_threadsafe(send_dm(user_id, amount, new_balance), bot.loop)
        # 관리자 채널 알림
        try:
            content = f"💰 자동 충전 완료!\n유저 ID: {user_id}\n금액: {amount:,}P\n잔여 포인트: {new_balance:,}P\n주문번호: {order_num}"
            requests.post(WEBHOOK_URL, json={"content": content}, timeout=3)
        except:
            pass
        print(f"[자동충전] user {user_id} 에게 {amount}P 충전됨 (주문번호: {order_num})")

async def send_dm(user_id, amount, new_balance):
    try:
        user = await bot.fetch_user(user_id)
        embed = discord.Embed(
            title="💰 자동 충전 완료",
            description=f"**{amount:,}P**가 충전되었습니다.\n현재 포인트: **{new_balance:,}P**",
            color=0x2ecc71
        )
        await user.send(embed=embed)
    except Exception as e:
        print(f"[DM 실패] {user_id}: {e}")

def start_auto_charge_loop():
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
# 디스코드 봇 명령어 (기존 기능 축약)
# ==============================
@bot.command(name="충전")
@commands.has_permissions(administrator=True)
async def charge_cmd(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.reply("❌ 0원 이상 입력하세요.")
        return
    new_balance = add_points(member.id, amount)
    await ctx.reply(f"✅ {member.mention} 님에게 {amount:,}P 충전 완료. 현재 포인트: {new_balance:,}P")
    dm_embed = discord.Embed(title="💰 충전 완료", description=f"{amount:,}P가 충전되었습니다.\n현재 포인트: {new_balance:,}P", color=0x3498db)
    try:
        await member.send(embed=dm_embed)
    except:
        pass

@bot.command(name="레드코리아패널")
@commands.has_permissions(administrator=True)
async def create_red_panel(ctx):
    embed = discord.Embed(title="🔴 RED KOREA - 탈콥", description="버튼을 눌러 이용하세요.", color=0xe74c3c)
    await ctx.send(embed=embed)

@bot.command(name="레드코리아패널구매자")
@commands.has_permissions(administrator=True)
async def create_buyer_red_panel(ctx):
    embed = discord.Embed(title="🔴 RED KOREA (구매자 전용)", description="버튼을 눌러 이용하세요.", color=0xe74c3c)
    await ctx.send(embed=embed)

@bot.command(name="코드추가")
@commands.has_permissions(administrator=True)
async def add_code_cmd(ctx, product_id, *codes):
    await ctx.reply("코드 추가 기능은 구현 필요")

@bot.command(name="코드목록")
@commands.has_permissions(administrator=True)
async def list_codes_cmd(ctx, product_id=None):
    await ctx.reply("코드 목록 기능은 구현 필요")

@bot.command(name="코드삭제")
@commands.has_permissions(administrator=True)
async def delete_code_cmd(ctx, code):
    await ctx.reply("코드 삭제 기능은 구현 필요")

@bot.event
async def on_ready():
    print(f"✅ 디스코드 봇 로그인: {bot.user}")

async def cycle_status():
    await bot.wait_until_ready()
    while not bot.is_closed():
        text = next(status_cycle)
        try:
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=text))
        except:
            break
        await asyncio.sleep(15)

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(cycle_status())
    bot.run(os.getenv("DISCORD_TOKEN"))

# ==============================
# Flask 라우트
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

@app.route("/api/points")
def api_points():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"points": 0})
    return jsonify({"points": get_points(user_id)})

@app.route("/api/charge-request", methods=["POST"])
def api_charge_request():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"ok": False, "error": "로그인 필요"}), 401
    data = request.get_json()
    amount = data.get("amount")
    if not amount or amount < 1000:
        return jsonify({"ok": False, "error": "최소 1,000원"}), 400
    order_num = create_charge_request(user_id, amount)
    content = (
        f"💳 **충전 요청 접수**\n"
        f"유저 ID: <@{user_id}>\n"
        f"금액: {amount:,}원\n"
        f"주문번호: `{order_num}`\n"
        f"계좌로 입금 후 메모에 주문번호를 입력하세요."
    )
    try:
        requests.post(WEBHOOK_URL, json={"content": content}, timeout=3)
    except:
        pass
    return jsonify({"ok": True, "order_number": order_num})

index_html = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>RED | 프리미엄 샵</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap" rel="stylesheet">
    <style>
        body { background:#0a0a0c; color:#ededee; font-family:Inter; margin:0; padding:2rem; }
        .container { max-width:1280px; margin:0 auto; }
        .header { display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem; }
        .logo { font-size:1.8rem; font-weight:800; background:linear-gradient(135deg,#ff4b6e,#ff8c42); -webkit-background-clip:text; background-clip:text; color:transparent; }
        .user-info { background:rgba(255,255,255,0.08); padding:0.5rem 1rem; border-radius:60px; display:flex; align-items:center; gap:1rem; }
        .points { color:#ffb347; font-weight:700; }
        .account-box { background:rgba(20,20,26,0.7); border-radius:28px; padding:1.5rem; margin:2rem 0; text-align:center; border:1px solid rgba(255,75,110,0.3); }
        .account-number { font-size:1.8rem; font-weight:800; background:linear-gradient(135deg,#fff,#ffb347); -webkit-background-clip:text; background-clip:text; color:transparent; }
        .charge-btn { background:linear-gradient(135deg,#ff4b6e,#ff6b4a); border:none; padding:0.8rem 2rem; border-radius:60px; font-weight:700; color:white; cursor:pointer; margin-top:1rem; }
        .footer { text-align:center; margin-top:3rem; color:#6c6c7a; }
        .modal { display:none; position:fixed; top:50%; left:50%; transform:translate(-50%,-50%); background:#1e1a2f; padding:2rem; border-radius:20px; z-index:1000; width:300px; text-align:center; }
        .overlay { display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.7); z-index:999; }
        input { width:100%; padding:0.5rem; margin:1rem 0; border-radius:8px; border:none; }
        .modal button { background:#ff4b6e; border:none; padding:0.5rem 1rem; border-radius:8px; color:white; cursor:pointer; margin:0 0.5rem; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <div class="logo">RED+RLNL</div>
        <div class="user-info">
            {% if user_id %}
                <img src="{{ avatar }}" width="32" height="32" style="border-radius:50%;">
                <span>{{ username }}</span>
                <span class="points"><i class="fas fa-coins"></i> <span id="points">0</span> P</span>
                <a href="/auth/logout" style="color:#ff6b4a;">로그아웃</a>
            {% else %}
                <a href="/auth/login" style="background:#5865f2; padding:0.5rem 1rem; border-radius:60px; text-decoration:none; color:white;">디스코드 로그인</a>
            {% endif %}
        </div>
    </div>
    {% if user_id %}
    <div class="account-box">
        <h2>입금 계좌 정보</h2>
        <p>아래 계좌로 입금 후, 메모에 주문번호를 입력하세요.</p>
        <p class="account-number">3521617659683</p>
        <p>예금주: 김대훈 | 농협은행</p>
        <button id="chargeBtn" class="charge-btn">충전 요청</button>
    </div>
    {% endif %}
    <div class="footer">© 2026 RED | 프리미엄 서비스</div>
</div>
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
    async function refreshPoints() {
        if (!userLoggedIn) return;
        try {
            const res = await fetch('/api/points');
            const data = await res.json();
            document.getElementById('points').innerText = (data.points || 0).toLocaleString();
        } catch(e) {}
    }
    refreshPoints();
    setInterval(refreshPoints, 30000);
    if (userLoggedIn) {
        const modal = document.getElementById('chargeModal');
        const overlay = document.getElementById('modalOverlay');
        document.getElementById('chargeBtn').onclick = () => { modal.style.display = 'block'; overlay.style.display = 'block'; };
        document.getElementById('closeModalBtn').onclick = () => { modal.style.display = 'none'; overlay.style.display = 'none'; };
        overlay.onclick = () => { modal.style.display = 'none'; overlay.style.display = 'none'; };
        document.getElementById('confirmChargeBtn').onclick = async () => {
            const amount = parseInt(document.getElementById('chargeAmount').value);
            if (!amount || amount < 1000) { alert("1,000원 이상 입력하세요."); return; }
            const res = await fetch('/api/charge-request', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({amount}) });
            const data = await res.json();
            if (data.ok) {
                alert(`충전 요청 접수! 주문번호: ${data.order_number}\n계좌로 입금 후 메모에 주문번호를 입력하세요.`);
                modal.style.display = 'none';
                overlay.style.display = 'none';
            } else alert(data.error);
        };
    }
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return rts(index_html, user_id=session.get("user_id"), username=session.get("username"), avatar=session.get("avatar"))

# ==============================
# 앱 실행 (Flask + 디스코드 봇 동시 실행)
# ==============================
if __name__ == "__main__":
    # 자동충전 루프 시작 (백그라운드)
    start_auto_charge_loop()
    # 디스코드 봇을 별도 스레드에서 실행
    import threading
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    # Flask 서버 실행
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
