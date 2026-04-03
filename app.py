import os
import sys
import requests
import random
import string
import threading
import asyncio
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

# 채널 ID
BUY_LOG_CHANNEL_ID = 1488221128286802143
ADMIN_CHANNEL_ID = 1488221287531679915
REVIEW_CHANNEL_ID = 1487603259773419641
INQUIRY_CHANNEL_ID = 1487602282257453238

# 역할 ID (설정 필요)
GUILD_ID = 1487602282257453236
NON_BUYER_ROLE_ID = 0  # 비구매자 역할 ID 입력
BUYER_ROLE_ID = 0      # 구매자 역할 ID 입력

# ==============================
# 데이터베이스
# ==============================
def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # users 테이블에 has_purchased 컬럼이 없으면 추가
    cur.execute("CREATE TABLE IF NOT EXISTS users (id BIGINT PRIMARY KEY, points INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS orders (id SERIAL PRIMARY KEY, user_id BIGINT, product_name TEXT, price INTEGER, code TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    cur.execute("CREATE TABLE IF NOT EXISTS product_codes (id SERIAL PRIMARY KEY, product_id TEXT NOT NULL, code TEXT NOT NULL UNIQUE, used INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS charge_requests (id SERIAL PRIMARY KEY, order_number TEXT UNIQUE NOT NULL, user_id BIGINT NOT NULL, amount INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, processed INTEGER DEFAULT 0)")
    
    # has_purchased 컬럼 추가 (없으면)
    try:
        cur.execute("ALTER TABLE users ADD COLUMN has_purchased INTEGER DEFAULT 0")
    except:
        pass
    
    conn.commit()
    conn.close()
    print("✅ DB 초기화 완료")

init_db()

# ==============================
# DB 헬퍼 함수
# ==============================
def to_int(value):
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except:
        return None

def get_points(user_id):
    uid = to_int(user_id)
    if not uid:
        return 0
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT points FROM users WHERE id = %s", (uid,))
    row = cur.fetchone()
    conn.close()
    return row["points"] if row else 0

def has_purchased(user_id):
    uid = to_int(user_id)
    if not uid:
        return False
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT has_purchased FROM users WHERE id = %s", (uid,))
        row = cur.fetchone()
        conn.close()
        return row["has_purchased"] == 1 if row else False
    except:
        conn.close()
        return False

def add_points(user_id, amount):
    uid = to_int(user_id)
    if not uid:
        return 0
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT points FROM users WHERE id = %s", (uid,))
    row = cur.fetchone()
    if row:
        new_balance = row["points"] + amount
        cur.execute("UPDATE users SET points = %s WHERE id = %s", (new_balance, uid))
    else:
        new_balance = amount
        cur.execute("INSERT INTO users (id, points, has_purchased) VALUES (%s, %s, 0)", (uid, new_balance))
    conn.commit()
    conn.close()
    return new_balance

def remove_points(user_id, amount):
    uid = to_int(user_id)
    if not uid:
        return None
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT points FROM users WHERE id = %s", (uid,))
    row = cur.fetchone()
    if not row or row["points"] < amount:
        conn.close()
        return None
    new_balance = row["points"] - amount
    cur.execute("UPDATE users SET points = %s WHERE id = %s", (new_balance, uid))
    conn.commit()
    conn.close()
    return new_balance

def mark_as_purchased(user_id):
    uid = to_int(user_id)
    if not uid:
        return
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE users SET has_purchased = 1 WHERE id = %s AND (has_purchased IS NULL OR has_purchased = 0)", (uid,))
        conn.commit()
    except:
        pass
    conn.close()

def insert_order(user_id, product_name, price, code):
    uid = to_int(user_id)
    if not uid:
        return
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO orders (user_id, product_name, price, code) VALUES (%s, %s, %s, %s)",
                (uid, product_name, price, code))
    conn.commit()
    conn.close()
    mark_as_purchased(uid)

def get_user_orders(user_id, limit=10):
    uid = to_int(user_id)
    if not uid:
        return []
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT product_name, price, code, created_at FROM orders WHERE user_id = %s ORDER BY created_at DESC LIMIT %s",
                (uid, limit))
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

def add_product_code(product_id, code):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO product_codes (product_id, code, used) VALUES (%s, %s, 0)", (product_id, code))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def get_unused_codes(product_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT code FROM product_codes WHERE product_id = %s AND used = 0", (product_id,))
    rows = cur.fetchall()
    conn.close()
    return [row["code"] for row in rows]

def delete_code(code):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM product_codes WHERE code = %s", (code,))
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def create_charge_request(user_id, amount):
    uid = to_int(user_id)
    if not uid:
        return ""
    order_num = ''.join(random.choices(string.digits, k=6))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO charge_requests (order_number, user_id, amount, processed) VALUES (%s, %s, %s, 0)",
                (order_num, uid, amount))
    conn.commit()
    conn.close()
    return order_num

# ==============================
# 상품 데이터
# ==============================
PRODUCTS = [
    {"id": "wolf_lite", "name": "🔴 RED-WOLF-LITE", "desc": "라이트 버전", "price": 7000, "img": "https://i.imgur.com/Z3BhZ18.jpeg"},
    {"id": "wolf", "name": "🔴 RED-WOLF", "desc": "하이레벨 패키지", "price": 13000, "img": "https://i.imgur.com/0UBCMGR.jpeg"},
    {"id": "kd_dropper", "name": "🔴 RED-kd-dropper", "desc": "트레이닝 패키지", "price": 7000, "img": "https://i.imgur.com/ApGpo16.jpeg"},
    {"id": "owo", "name": "🔴 RED-OWO", "desc": "AIMBOT 가성비", "price": 7000, "img": "https://i.imgur.com/7W1eg5S.png"},
]

# ==============================
# 디스코드 봇
# ==============================
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix=".", intents=intents)

async def update_user_role(user_id: int, is_buyer: bool):
    if not GUILD_ID or not NON_BUYER_ROLE_ID or not BUYER_ROLE_ID:
        return
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return
    member = guild.get_member(user_id)
    if not member:
        return
    non_role = guild.get_role(NON_BUYER_ROLE_ID)
    buyer_role = guild.get_role(BUYER_ROLE_ID)
    if is_buyer:
        if non_role and non_role in member.roles:
            await member.remove_roles(non_role)
        if buyer_role and buyer_role not in member.roles:
            await member.add_roles(buyer_role)
    else:
        if buyer_role and buyer_role in member.roles:
            await member.remove_roles(buyer_role)
        if non_role and non_role not in member.roles:
            await member.add_roles(non_role)

async def send_alerts(user_id, product_name, code, price, new_balance, is_first):
    # 구매로그 채널 (익명)
    ch = bot.get_channel(BUY_LOG_CHANNEL_ID)
    if ch:
        await ch.send(f"🛒 익명의 유저가 **{product_name}** 을(를) 구매했습니다.")
    
    # 관리자 채널 (상세)
    ch = bot.get_channel(ADMIN_CHANNEL_ID)
    if ch:
        embed = discord.Embed(title="✅ 구매 상세", color=0x2ecc71)
        embed.add_field(name="유저 ID", value=str(user_id))
        embed.add_field(name="상품명", value=product_name)
        embed.add_field(name="발급 코드", value=f"`{code}`")
        embed.add_field(name="차감 포인트", value=f"{price:,}P")
        embed.add_field(name="남은 포인트", value=f"{new_balance:,}P")
        if is_first:
            embed.add_field(name="🎉 첫 구매", value="구매자 역할이 부여되었습니다.")
        await ch.send(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ 디스코드 봇 로그인: {bot.user}")
    print(f"📋 등록된 명령어: {[cmd.name for cmd in bot.commands]}")
    
    guild = bot.get_guild(GUILD_ID)
    if guild:
        print(f"📌 서버: {guild.name}")
    
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=".도움말"))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.reply("❌ 존재하지 않는 명령어입니다. `.도움말` 로 확인하세요.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.reply("❌ 관리자 권한이 필요합니다.")
    else:
        await ctx.reply(f"❌ 오류: {error}")

# ========== 일반 명령어 ==========
@bot.command(name="도움말")
async def help_cmd(ctx):
    embed = discord.Embed(title="📚 RED KOREA 봇 도움말", color=0x3498db)
    embed.add_field(name="`.정보`", value="내 포인트와 구매내역 확인", inline=False)
    embed.add_field(name="`.레드코리아패널`", value="자판기 패널 생성 (관리자)", inline=False)
    embed.add_field(name="`.충전 @유저 금액`", value="포인트 충전 (관리자)", inline=False)
    embed.add_field(name="`.코드추가 상품ID 코드`", value="상품 코드 추가 (관리자)", inline=False)
    embed.add_field(name="`.코드목록 [상품ID]`", value="미사용 코드 목록 (관리자)", inline=False)
    embed.add_field(name="`.코드삭제 코드`", value="코드 삭제 (관리자)", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="정보")
async def info_cmd(ctx):
    user = ctx.author
    points = get_points(user.id)
    has_purchased_flag = has_purchased(user.id)
    orders = get_user_orders(user.id, 5)
    
    embed = discord.Embed(title="📊 내 정보", color=0x3498db)
    embed.add_field(name="💰 포인트", value=f"{points:,}P", inline=False)
    embed.add_field(name="🏷️ 상태", value="✅ 구매자" if has_purchased_flag else "❌ 비구매자", inline=False)
    
    if orders:
        order_text = "\n".join([f"• {o['product_name']} - {o['price']:,}P" for o in orders[:3]])
        embed.add_field(name="📦 최근 구매", value=order_text, inline=False)
    
    await ctx.send(embed=embed)

# ========== 관리자 명령어 ==========
@bot.command(name="레드코리아패널")
@commands.has_permissions(administrator=True)
async def create_panel(ctx):
    """일반 패널 생성 - 비구매자도 구매 가능, 충전은 구매자만"""
    
    embed = discord.Embed(
        title="🔴 RED KOREA 자판기",
        description="버튼을 눌러 서비스를 이용하세요",
        color=0xe74c3c
    )
    
    view = discord.ui.View(timeout=None)
    
    # 구매 버튼
    async def buy_callback(interaction):
        await interaction.response.defer(ephemeral=True)
        
        options = []
        for p in PRODUCTS:
            stock = get_code_stock(p["id"])
            options.append(discord.SelectOption(
                label=f"{p['name']} - {p['price']:,}P",
                value=p["id"],
                description=f"재고: {stock}개"
            ))
        
        select = discord.ui.Select(placeholder="상품 선택", options=options)
        
        async def select_callback(interaction):
            await interaction.response.defer(ephemeral=True)
            product_id = select.values[0]
            product = next(p for p in PRODUCTS if p["id"] == product_id)
            
            user = interaction.user
            before_purchase = has_purchased(user.id)
            new_balance = remove_points(user.id, product["price"])
            
            if new_balance is None:
                current = get_points(user.id)
                await interaction.followup.send(f"❌ 포인트 부족 (필요: {product['price']:,}P / 보유: {current:,}P)", ephemeral=True)
                return
            
            code = get_unused_code(product_id)
            if code is None:
                add_points(user.id, product["price"])
                await interaction.followup.send(f"❌ 재고 부족 - {product['name']}", ephemeral=True)
                return
            
            insert_order(user.id, product["name"], product["price"], code)
            after_purchase = has_purchased(user.id)
            is_first_purchase = (not before_purchase and after_purchase)
            
            # 역할 업데이트
            await update_user_role(user.id, True)
            
            # 알림 전송
            await send_alerts(user.id, product["name"], code, product["price"], new_balance, is_first_purchase)
            
            # DM 전송
            try:
                dm = await user.create_dm()
                await dm.send(f"✅ 구매 완료!\n상품: {product['name']}\n코드: `{code}`\n잔액: {new_balance:,}P")
            except:
                pass
            
            await interaction.followup.send(f"✅ 구매 완료!\n코드: `{code}`\n잔액: {new_balance:,}P", ephemeral=True)
        
        select.callback = select_callback
        view_select = discord.ui.View()
        view_select.add_item(select)
        await interaction.followup.send("📦 상품을 선택하세요:", view=view_select, ephemeral=True)
    
    # 정보 버튼
    async def info_callback(interaction):
        await interaction.response.defer(ephemeral=True)
        user = interaction.user
        points = get_points(user.id)
        has_purchased_flag = has_purchased(user.id)
        orders = get_user_orders(user.id, 5)
        
        embed_info = discord.Embed(title="📊 내 정보", color=0x3498db)
        embed_info.add_field(name="💰 포인트", value=f"{points:,}P", inline=False)
        embed_info.add_field(name="🏷️ 상태", value="✅ 구매자" if has_purchased_flag else "❌ 비구매자", inline=False)
        
        if orders:
            order_text = "\n".join([f"• {o['product_name']} - {o['price']:,}P" for o in orders[:3]])
            embed_info.add_field(name="📦 최근 구매", value=order_text, inline=False)
        
        await interaction.followup.send(embed=embed_info, ephemeral=True)
    
    # 충전 버튼 (구매자만 계좌 노출, 비구매자는 문의 안내)
    async def charge_callback(interaction):
        user = interaction.user
        is_buyer = has_purchased(user.id)
        
        if is_buyer:
            embed_charge = discord.Embed(
                title="💰 충전 안내",
                description="**계좌 정보**\n🏦 농협은행\n💳 `3521617659683`\n👤 김대훈\n\n입금 후 관리자에게 알려주세요.",
                color=0x27ae60
            )
            await interaction.response.send_message(embed=embed_charge, ephemeral=True)
        else:
            embed_charge = discord.Embed(
                title="🔒 구매자 전용 서비스",
                description=f"❌ 구매 이력이 없습니다.\n문의 채널: <#{INQUIRY_CHANNEL_ID}>",
                color=0xe74c3c
            )
            await interaction.response.send_message(embed=embed_charge, ephemeral=True)
    
    buy_btn = discord.ui.Button(label="🛒 구매", style=discord.ButtonStyle.primary)
    info_btn = discord.ui.Button(label="📊 정보", style=discord.ButtonStyle.secondary)
    charge_btn = discord.ui.Button(label="💰 충전", style=discord.ButtonStyle.success)
    
    buy_btn.callback = buy_callback
    info_btn.callback = info_callback
    charge_btn.callback = charge_callback
    
    view.add_item(buy_btn)
    view.add_item(info_btn)
    view.add_item(charge_btn)
    
    await ctx.send(embed=embed, view=view)
    print("✅ 패널 생성 완료")

@bot.command(name="충전")
@commands.has_permissions(administrator=True)
async def charge_cmd(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.reply("❌ 0원 이상 입력하세요.")
        return
    new_balance = add_points(member.id, amount)
    await ctx.reply(f"✅ {member.mention} 님에게 {amount:,}P 충전 완료. 현재 포인트: **{new_balance:,}P**")

@bot.command(name="코드추가")
@commands.has_permissions(administrator=True)
async def add_code_cmd(ctx, product_id: str, *codes: str):
    valid_ids = [p["id"] for p in PRODUCTS]
    if product_id not in valid_ids:
        await ctx.reply(f"❌ 유효한 상품 ID: {', '.join(valid_ids)}")
        return
    if not codes:
        await ctx.reply("❌ 추가할 코드를 입력하세요.")
        return
    added = 0
    for code in codes:
        if add_product_code(product_id, code.strip()):
            added += 1
    await ctx.reply(f"✅ {added}개 추가 완료, {len(codes)-added}개 실패")

@bot.command(name="코드목록")
@commands.has_permissions(administrator=True)
async def list_codes_cmd(ctx, product_id: str = None):
    if product_id is None:
        lines = []
        for p in PRODUCTS:
            codes = get_unused_codes(p["id"])
            lines.append(f"**{p['name']}** (`{p['id']}`): {len(codes)}개")
        await ctx.reply("\n".join(lines))
    else:
        codes = get_unused_codes(product_id)
        if codes:
            await ctx.reply(f"**{product_id}** 미사용 코드 ({len(codes)}개):\n`" + "`, `".join(codes[:30]) + "`")
        else:
            await ctx.reply(f"**{product_id}**에 미사용 코드가 없습니다.")

@bot.command(name="코드삭제")
@commands.has_permissions(administrator=True)
async def delete_code_cmd(ctx, *, code: str):
    if delete_code(code):
        await ctx.reply(f"✅ 코드 `{code}` 삭제 완료.")
    else:
        await ctx.reply(f"❌ 코드 `{code}` 없음.")

def run_bot():
    if DISCORD_TOKEN:
        try:
            print("🤖 디스코드 봇 시작 중...")
            bot.run(DISCORD_TOKEN, reconnect=True)
        except Exception as e:
            print(f"❌ 봇 실행 오류: {e}")
    else:
        print("⚠️ DISCORD_TOKEN 환경 변수가 없습니다.")

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
    
    new_balance = remove_points(user_id, product["price"])
    if new_balance is None:
        current = get_points(user_id)
        return jsonify({"ok": False, "error": f"포인트 부족 (필요: {product['price']:,}P / 보유: {current:,}P)"}), 400
    
    code = get_unused_code(product_id)
    if code is None:
        add_points(user_id, product["price"])
        return jsonify({"ok": False, "error": "재고 부족"}), 400
    
    insert_order(user_id, product["name"], product["price"], code)
    
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
            flex-wrap: wrap;
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .logo { font-size: 1.8rem; font-weight: 800; background: linear-gradient(135deg,#fff,#a78bfa,#ff4b6e); -webkit-background-clip:text; background-clip:text; color:transparent; }
        .user-info { display: flex; align-items: center; gap: 1rem; background: rgba(0,0,0,0.35); padding: 0.5rem 1rem; border-radius: 60px; }
        .avatar { width: 40px; height: 40px; border-radius: 50%; border: 2px solid #60a5fa; }
        .points { color: #ffb347; font-weight: 700; }
        .nav-links { display: flex; gap: 1rem; margin-bottom: 1rem; }
        .nav-link { color: #cbd5e1; text-decoration: none; padding: 0.5rem 1rem; border-radius: 40px; }
        .nav-link:hover, .nav-link.active { background: rgba(96,165,250,0.2); color: white; }
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
        button, .discord-btn { background: #5865f2; border: none; padding: 0.5rem 1rem; border-radius: 40px; color: white; cursor: pointer; text-decoration: none; display: inline-block; }
        a { text-decoration: none; }
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
            <a href="/auth/login" class="discord-btn">🔐 디스코드 로그인</a>
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

    function showToast(msg, isError) {
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
        setInterval(() => fetchStock().then(() => renderProducts()), 60000);
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
            flex-wrap: wrap;
            gap: 1rem;
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
            html += `<tr>
                <td>${o.product_name}</td>
                <td>${o.price.toLocaleString()}P</td>
                <td><span class="code">${o.code}</span></td>
                <td>${o.created_at}</td>
            </tr>`;
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
# 실행
# ==============================
if __name__ == "__main__":
    if DISCORD_TOKEN:
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
        print("🤖 봇 스레드 시작됨")
    else:
        print("⚠️ DISCORD_TOKEN 없음 - 봇 미실행")
    
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Flask 서버 시작 (포트: {port})")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
