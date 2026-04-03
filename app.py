import os
import sys
import requests
import random
import string
import threading
import asyncio
import logging
from datetime import datetime, timezone
from itertools import cycle
from typing import List, Optional

# audioop-lts 패치 (Python 3.13+ 호환성)
try:
    import audioop
except ImportError:
    import audioop_lts as audioop

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
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# ==============================
# 기본 설정
# ==============================
logging.getLogger("discord.gateway").setLevel(logging.WARNING)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change")
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "dev-pass-change")

# 디스코드 OAuth2
DISCORD_CLIENT_ID = os.environ.get("DISCORD_CLIENT_ID", "1488342279029784768")
DISCORD_CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET", "S8wERVotwZOSpz2A_75KCIWeYbxMf9GP")
DISCORD_REDIRECT_URI = os.environ.get("DISCORD_REDIRECT_URI", "https://api.redkorea.store/auth/callback")

# 웹훅
ADMIN_WEBHOOK_URL = "https://discord.com/api/webhooks/1489485738168025279/nwe2k1dQl7f6lPpS9jCJJpHUXFD3d-dtcMCvS_NiDPXPsDtPW1hljJ1xFOdxPzf3QCxz"
BUY_LOG_WEBHOOK_URL = "https://discord.com/api/webhooks/1488231305396224041/Fa_z7Wihwf9-k79aGNcvaLNj3emxWYxlFoD6xVGkgLxzZKig3Uc7MQpL8Nk93d4Pyfat"

# PostgreSQL (Supabase Session Pooler – IPv4)
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres.cczcenhgureeamwjtkug:5P5iPdjnEMP7ZKDQ@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres?sslmode=require")

# 데이터베이스 연결 테스트
try:
    test_conn = psycopg2.connect(DATABASE_URL)
    test_conn.close()
    print("✅ 데이터베이스 연결 성공")
except Exception as e:
    print(f"❌ 데이터베이스 연결 실패: {e}")
    sys.exit(1)

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id BIGINT PRIMARY KEY,
            points INTEGER DEFAULT 0
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            product_name TEXT,
            price INTEGER,
            code TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            charge_url TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS product_codes (
            id SERIAL PRIMARY KEY,
            product_id TEXT NOT NULL,
            code TEXT NOT NULL UNIQUE,
            used INTEGER DEFAULT 0
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS charge_requests (
            id SERIAL PRIMARY KEY,
            order_number TEXT UNIQUE NOT NULL,
            user_id BIGINT NOT NULL,
            amount INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed INTEGER DEFAULT 0
        )
    """)
    cur.execute("INSERT INTO settings (id, charge_url) VALUES (1, 'https://discord.gg/q6nJpYuFB8') ON CONFLICT (id) DO NOTHING")
    conn.commit()
    conn.close()

init_db()

# ==============================
# DB 함수
# ==============================
def get_points(user_id: int) -> int:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT points FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row["points"] if row else 0

def add_points(user_id: int, amount: int) -> int:
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

def remove_points(user_id: int, amount: int) -> Optional[int]:
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

def insert_order(user_id: int, product_name: str, price: int, code: str) -> None:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO orders (user_id, product_name, price, code) VALUES (%s, %s, %s, %s)",
        (user_id, product_name, price, code)
    )
    conn.commit()
    conn.close()

def get_user_orders(user_id: int, limit: int = 10) -> List[dict]:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT product_name, price, code, created_at FROM orders WHERE user_id = %s ORDER BY created_at DESC LIMIT %s",
        (user_id, limit)
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_user_total_spent(user_id: int) -> int:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(SUM(price), 0) FROM orders WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row["coalesce"] if row else 0

def add_product_code(product_id: str, code: str) -> bool:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO product_codes (product_id, code, used) VALUES (%s, %s, 0)", (product_id, code))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def get_unused_code(product_id: str) -> Optional[str]:
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

def get_code_stock(product_id: str) -> int:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM product_codes WHERE product_id = %s AND used = 0", (product_id,))
    row = cur.fetchone()
    conn.close()
    return row["count"] if row else 0

def get_unused_codes(product_id: str) -> List[str]:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT code FROM product_codes WHERE product_id = %s AND used = 0", (product_id,))
    rows = cur.fetchall()
    conn.close()
    return [row["code"] for row in rows]

def delete_code(code: str) -> bool:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM product_codes WHERE code = %s", (code,))
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def create_charge_request(user_id: int, amount: int) -> str:
    while True:
        order_num = ''.join(random.choices(string.digits, k=6))
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM charge_requests WHERE order_number = %s", (order_num,))
        if not cur.fetchone():
            conn.close()
            break
        conn.close()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO charge_requests (order_number, user_id, amount, processed) VALUES (%s, %s, %s, 0)",
        (order_num, user_id, amount)
    )
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
# 디스코드 봇
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

async def safe_dm_embed(user: discord.abc.User, embed: discord.Embed) -> None:
    try:
        dm = await user.create_dm()
        await dm.send(embed=embed)
    except Exception as e:
        print(f"[DM_EMBED_ERROR] user={user.id} | {e}")

# ========== 디스코드 뷰 ==========
class ProductSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(ProductSelect())

class ProductSelect(discord.ui.Select):
    def __init__(self):
        options = []
        for p in PRODUCTS:
            stock = get_code_stock(p["id"])
            label = f"{p['name']} - {p['price']:,}P"
            description = f"{p['desc']} | 재고: {stock}개" if stock else f"{p['desc']} | 재고: 품절"
            options.append(discord.SelectOption(label=label, value=p["id"], description=description))
        super().__init__(placeholder="구매할 상품을 선택하세요", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        product_id = self.values[0]
        product = next((p for p in PRODUCTS if p["id"] == product_id), None)
        if not product:
            await interaction.response.send_message("❌ 오류", ephemeral=True)
            return
        user = interaction.user
        price = product["price"]
        product_name = product["name"]
        new_balance = remove_points(user.id, price)
        if new_balance is None:
            current = get_points(user.id)
            await interaction.response.send_message(f"❌ 포인트 부족 (필요: {price:,}P / 보유: {current:,}P)", ephemeral=True)
            return
        code = get_unused_code(product_id)
        if code is None:
            add_points(user.id, price)
            await interaction.response.send_message(f"❌ 재고 부족 - {product_name}", ephemeral=True)
            return
        insert_order(user.id, product_name, price, code)
        # 관리자 웹훅
        admin_embed = discord.Embed(title="✅ 구매 발생 (관리자용)", description=f"**유저:** {user.mention} (`{user.id}`)\n**상품명:** `{product_name}`\n**발급 코드:** `{code}`\n**차감 포인트:** {price:,}P\n**남은 포인트:** {new_balance:,}P", color=0x2ecc71)
        try:
            requests.post(ADMIN_WEBHOOK_URL, json={"embeds": [admin_embed.to_dict()]}, timeout=3)
        except: pass
        # 구매 로그 웹훅
        buy_embed = discord.Embed(title="🛒 구매 발생", description=f"익명의 유저가 **{product_name}** 을(를) 구매했습니다.", color=0x2ecc71)
        try:
            requests.post(BUY_LOG_WEBHOOK_URL, json={"embeds": [buy_embed.to_dict()]}, timeout=3)
        except: pass
        # DM
        dm_embed = discord.Embed(title="✅ 구매 완료", description=f"**상품명:** {product_name}\n**발급 코드:** `{code}`\n**차감 포인트:** {price:,}P\n**남은 포인트:** {new_balance:,}P", color=0x2ecc71)
        await safe_dm_embed(user, dm_embed)
        await interaction.response.send_message(f"✅ 구매 완료! 코드: `{code}` (DM으로도 전송)", ephemeral=True)

class AfterPurchaseView(discord.ui.View):
    def __init__(self, product_name: str):
        super().__init__(timeout=300)
        self.product_name = product_name

    @discord.ui.button(label="📝 구매후기 작성", style=discord.ButtonStyle.secondary, custom_id="red_write_review")
    async def write_review_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = discord.ui.Modal(title="구매 후기 작성")
        modal.add_item(discord.ui.TextInput(label="후기 내용", placeholder="솔직한 후기를 남겨주세요.", required=True, max_length=400, style=discord.TextStyle.paragraph))
        async def on_submit(interaction: discord.Interaction):
            content = modal.children[0].value
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            ch = bot.get_channel(REVIEW_CHANNEL_ID)
            if isinstance(ch, discord.TextChannel):
                embed = discord.Embed(title=f"📝 구매 후기 · {self.product_name}", description=f"**작성자:** {interaction.user.mention} (`{interaction.user.id}`)\n**상품명:** `{self.product_name}`\n\n{content}\n\n*작성 시간(UTC): {now}*", color=0xf1c40f)
                await ch.send(embed=embed)
            await interaction.response.send_message("✅ 후기가 등록되었습니다.", ephemeral=True)
        modal.on_submit = on_submit
        await interaction.response.send_modal(modal)

class RedVendingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="💰 충전", style=discord.ButtonStyle.success, custom_id="red_charge")
    async def charge_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        TICKET_CHANNEL_ID = 1487602282257453238
        embed = discord.Embed(title="🔒 구매자 전용 서비스", description=f"회원님은 현재 구매 내역이 없습니다.\n충전을 원하시면 먼저 구매 후 이용 가능합니다.\n문의: <#{TICKET_CHANNEL_ID}> (티켓 채널)", color=0xe74c3c)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="📊 정보", style=discord.ButtonStyle.secondary, custom_id="red_info")
    async def info_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        points = get_points(user.id)
        total_spent = get_user_total_spent(user.id)
        orders = get_user_orders(user.id)
        embed = discord.Embed(title="📋 사용자 정보", color=0x3498db)
        embed.add_field(name="디스코드", value=f"{user.mention}", inline=False)
        embed.add_field(name="ID", value=f"`{user.id}`", inline=False)
        embed.add_field(name="💰 현재 포인트", value=f"{points:,}P", inline=False)
        embed.add_field(name="💸 누적 사용 포인트", value=f"{total_spent:,}P", inline=False)
        if orders:
            order_list = "\n".join([f"• `{o['created_at'][:10]}` **{o['product_name']}** - {o['price']:,}P" for o in orders])
            embed.add_field(name="📦 구매 내역", value=order_list, inline=False)
        else:
            embed.add_field(name="📦 구매 내역", value="아직 구매 내역이 없습니다.", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🛒 구매", style=discord.ButtonStyle.primary, custom_id="red_buy")
    async def buy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ProductSelectView()
        embed = discord.Embed(title="📦 상품 선택", description="구매할 상품을 선택하세요.\n재고는 옵션 설명에 표시됩니다.", color=0x3498db)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class BuyerRedVendingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="💰 충전", style=discord.ButtonStyle.success, custom_id="buyer_red_charge")
    async def charge_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        points = get_points(user.id)
        embed = discord.Embed(
            title="💳 충전 안내",
            description=(
                f"**아래 계좌로 입금 후, 관리자에게 알려주세요.**\n\n"
                f"🏦 농협은행\n💳 `3521617659683`\n👤 김대훈\n\n"
                f"📊 현재 포인트: **{points:,}P**"
            ),
            color=0x27ae60,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="📊 정보", style=discord.ButtonStyle.secondary, custom_id="red_info")
async def info_button(self, interaction: discord.Interaction, button: discord.ui.Button):
    await interaction.response.defer(ephemeral=True)

    user = interaction.user
    points = get_points(user.id)
    total_spent = get_user_total_spent(user.id)
    orders = get_user_orders(user.id)

    embed = discord.Embed(title="📋 사용자 정보", color=0x3498db)
    embed.add_field(name="디스코드", value=f"{user.mention}", inline=False)
    embed.add_field(name="ID", value=f"`{user.id}`", inline=False)
    embed.add_field(name="💰 현재 포인트", value=f"{points:,}P", inline=False)
    embed.add_field(name="💸 누적 사용 포인트", value=f"{total_spent:,}P", inline=False)
    if orders:
        order_list = "\n".join(
            [f"• `{o['created_at'][:10]}` **{o['product_name']}** - {o['price']:,}P" for o in orders]
        )
        embed.add_field(name="📦 구매 내역", value=order_list, inline=False)
    else:
        embed.add_field(name="📦 구매 내역", value="아직 구매 내역이 없습니다.", inline=False)

    await interaction.followup.send(embed=embed, ephemeral=True)

# ========== 디스코드 명령어 ==========
@bot.command(name="충전")
@commands.has_permissions(administrator=True)
async def charge_cmd(ctx: commands.Context, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.reply("❌ 0원 이상 입력하세요.", delete_after=5)
        return
    new_balance = add_points(member.id, amount)
    await ctx.reply(f"✅ {member.mention} 님에게 {amount:,}P 충전 완료. 현재 포인트: **{new_balance:,}P**")
    dm_embed = discord.Embed(title="💰 충전 완료", description=f"{amount:,}P가 충전되었습니다.\n현재 포인트: {new_balance:,}P", color=0x3498db)
    await safe_dm_embed(member, dm_embed)

@bot.command(name="레드코리아패널")
@commands.has_permissions(administrator=True)
async def create_red_panel(ctx: commands.Context):
    embed = discord.Embed(title="🔴 RED KOREA - 탈콥", description="**🤖 디스코드 자판기**\n버튼을 눌러 서비스를 이용하세요.", color=0xe74c3c)
    view = RedVendingView()
    await ctx.send(embed=embed, view=view)

@bot.command(name="레드코리아패널구매자")
@commands.has_permissions(administrator=True)
async def create_buyer_red_panel(ctx: commands.Context):
    embed = discord.Embed(title="🔴 RED KOREA (구매자 전용)", description="**🤖 디스코드 자판기**\n버튼을 눌러 서비스를 이용하세요.", color=0xe74c3c)
    view = BuyerRedVendingView()
    await ctx.send(embed=embed, view=view)

@bot.command(name="코드추가")
@commands.has_permissions(administrator=True)
async def add_code_cmd(ctx: commands.Context, product_id: str, *codes: str):
    valid_ids = [p["id"] for p in PRODUCTS]
    if product_id not in valid_ids:
        await ctx.reply(f"❌ 유효한 상품 ID: {', '.join(valid_ids)}", delete_after=10)
        return
    if not codes:
        await ctx.reply("❌ 추가할 코드를 입력하세요.", delete_after=10)
        return
    added = sum(1 for code in codes if add_product_code(product_id, code.strip()))
    await ctx.reply(f"✅ {added}개 추가 완료, {len(codes)-added}개 실패", delete_after=10)

@bot.command(name="코드목록")
@commands.has_permissions(administrator=True)
async def list_codes_cmd(ctx: commands.Context, product_id: str = None):
    if product_id is None:
        lines = []
        for p in PRODUCTS:
            codes = get_unused_codes(p["id"])
            lines.append(f"**{p['name']}** (`{p['id']}`): {len(codes)}개")
        await ctx.reply("\n".join(lines), delete_after=30)
    else:
        codes = get_unused_codes(product_id)
        if codes:
            await ctx.reply(f"**{product_id}** 미사용 코드 ({len(codes)}개):\n`" + "`, `".join(codes[:30]) + "`", delete_after=30)
        else:
            await ctx.reply(f"**{product_id}**에 미사용 코드가 없습니다.", delete_after=10)

@bot.command(name="코드삭제")
@commands.has_permissions(administrator=True)
async def delete_code_cmd(ctx: commands.Context, *, code: str):
    if delete_code(code):
        await ctx.reply(f"✅ 코드 `{code}` 삭제 완료.", delete_after=10)
    else:
        await ctx.reply(f"❌ 코드 `{code}` 없음.", delete_after=10)

async def cycle_status():
    await bot.wait_until_ready()
    while not bot.is_closed():
        text = next(status_cycle)
        try:
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=text))
        except:
            break
        await asyncio.sleep(15)

@bot.event
async def on_ready():
    print(f"✅ 디스코드 봇 로그인: {bot.user}")
    asyncio.create_task(cycle_status())

def run_bot():
    try:
        bot.run(os.environ["DISCORD_TOKEN"])
    except Exception as e:
        print(f"봇 실행 오류: {e}")

# ==============================
# Flask 웹 라우트
# ==============================
@app.route("/api/stock")
def api_stock():
    stocks = {}
    for p in PRODUCTS:
        stocks[p["id"]] = get_code_stock(p["id"])
    return jsonify(stocks)

@app.route("/api/points")
def api_points():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"points": 0})
    return jsonify({"points": get_points(user_id)})

@app.route("/api/buy", methods=["POST"])
def api_buy():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"ok": False, "error": "로그인 필요"}), 401
    data = request.get_json()
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
        return jsonify({"ok": False, "error": "재고 부족"}), 400
    insert_order(user_id, product_name, price, code)
    # 웹훅
    admin_embed = discord.Embed(title="✅ 구매 발생 (관리자용)", description=f"**유저:** <@{user_id}> (`{user_id}`)\n**상품명:** `{product_name}`\n**발급 코드:** `{code}`\n**차감 포인트:** {price:,}P\n**남은 포인트:** {new_balance:,}P", color=0x2ecc71)
    try:
        requests.post(ADMIN_WEBHOOK_URL, json={"embeds": [admin_embed.to_dict()]}, timeout=3)
    except: pass
    buy_embed = discord.Embed(title="🛒 구매 발생", description=f"익명의 유저가 **{product_name}** 을(를) 구매했습니다.", color=0x2ecc71)
    try:
        requests.post(BUY_LOG_WEBHOOK_URL, json={"embeds": [buy_embed.to_dict()]}, timeout=3)
    except: pass
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
    content = f"💳 **충전 요청**\n유저: <@{user_id}>\n금액: {amount:,}원\n주문번호: `{order_num}`\n계좌: 3521617659683 (농협, 김대훈)\n입금 확인 후 `.충전 <@{user_id}> {amount}`"
    try:
        requests.post(ADMIN_WEBHOOK_URL, json={"content": content}, timeout=3)
    except: pass
    return jsonify({"ok": True, "order_number": order_num})

# ========== HTML 템플릿 ==========
index_html = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>RED | 프리미엄 샵</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;14..32,400;14..32,600;14..32,700;14..32,800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body {
            background: radial-gradient(circle at 10% 20%, #0f0c1f, #02010a);
            font-family: 'Inter', sans-serif;
            color: #eef2ff;
            min-height: 100vh;
            padding: 2rem 1.5rem;
        }
        .container { max-width: 1280px; margin: 0 auto; }
        .notice-bar {
            background: linear-gradient(90deg, #1e1a2f, #2a1e2c, #1e1a2f);
            border-bottom: 1px solid rgba(255,75,110,0.3);
            border-top: 1px solid rgba(255,75,110,0.2);
            padding: 0.7rem 0;
            overflow: hidden;
            white-space: nowrap;
            margin-bottom: 1.5rem;
            border-radius: 60px;
        }
        .notice-track {
            display: inline-block;
            animation: scrollNotice 25s linear infinite;
        }
        .notice-item { display: inline-block; padding: 0 2rem; font-size: 0.9rem; font-weight: 500; }
        .notice-item i { color: #ff4b6e; margin-right: 0.5rem; }
        .notice-item strong { color: #ffb347; }
        @keyframes scrollNotice { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }
        .glass-card {
            background: rgba(15,23,42,0.65);
            backdrop-filter: blur(16px);
            border-radius: 2rem;
            border: 1px solid rgba(96,165,250,0.25);
            padding: 1.5rem;
            margin-bottom: 2rem;
        }
        .header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem; }
        .logo { font-size: 1.8rem; font-weight: 800; background: linear-gradient(135deg,#fff,#a78bfa,#ff4b6e); -webkit-background-clip:text; background-clip:text; color:transparent; }
        .user-info { display: flex; align-items: center; gap: 1rem; background: rgba(0,0,0,0.35); padding: 0.5rem 1rem; border-radius: 60px; }
        .avatar { width: 40px; height: 40px; border-radius: 50%; border: 2px solid #60a5fa; }
        .points { color: #ffb347; font-weight: 700; }
        .nav-links { display: flex; gap: 1rem; }
        .nav-link { color: #cbd5e1; text-decoration: none; padding: 0.5rem 1rem; border-radius: 40px; transition: 0.2s; }
        .nav-link:hover, .nav-link.active { background: rgba(96,165,250,0.2); color: white; }
        .product-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1.5rem; margin: 2rem 0; }
        .product-card { background: rgba(0,0,0,0.4); border-radius: 1.5rem; overflow: hidden; border: 1px solid rgba(96,165,250,0.2); transition: transform 0.2s, border-color 0.2s; }
        .product-card:hover { transform: translateY(-4px); border-color: #60a5fa; }
        .product-img { width: 100%; height: 200px; object-fit: cover; }
        .product-info { padding: 1.2rem; }
        .product-title { font-size: 1.2rem; font-weight: 700; margin-bottom: 0.5rem; }
        .product-desc { font-size: 0.85rem; color: #9ca3af; margin-bottom: 0.5rem; }
        .product-price { font-size: 1.4rem; font-weight: 800; color: #ffb347; margin-bottom: 0.5rem; }
        .product-stock { font-size: 0.8rem; color: #60a5fa; margin-bottom: 1rem; }
        .buy-btn { background: linear-gradient(135deg,#ff4b6e,#ff6b4a); border: none; width: 100%; padding: 0.7rem; border-radius: 40px; font-weight: 700; color: white; cursor: pointer; transition: 0.2s; }
        .buy-btn:hover { transform: translateY(-2px); box-shadow: 0 6px 14px rgba(255,75,110,0.4); }
        .login-message { text-align: center; padding: 2rem; background: rgba(0,0,0,0.3); border-radius: 1.5rem; margin: 2rem 0; }
        .footer { text-align: center; color: #6c6c7a; font-size: 0.7rem; margin-top: 2rem; }
        .modal { display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%,-50%); background: #1e1a2f; backdrop-filter: blur(20px); padding: 1.8rem; border-radius: 1.5rem; z-index: 1000; width: 300px; text-align: center; border: 1px solid #ff4b6e; }
        .overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 999; }
        input { width: 100%; padding: 0.6rem; margin: 1rem 0; border-radius: 12px; border: 1px solid #4b5563; background: #0f172a; color: white; text-align: center; }
        .modal button { background: #ff4b6e; border: none; padding: 0.5rem 1rem; border-radius: 30px; color: white; cursor: pointer; margin: 0 0.5rem; }
        @media (max-width: 640px) { .product-grid { grid-template-columns: 1fr; } .header { flex-direction: column; } }
    </style>
</head>
<body>
<div class="container">
    <div class="notice-bar">
        <div class="notice-track">
            <span class="notice-item"><i class="fas fa-gift"></i> 첫 구매 15% 할인! <strong>코드: WELCOME15</strong></span>
            <span class="notice-item"><i class="fas fa-fire"></i> 🔥 3월 한정 특가! 전 상품 10% 추가 할인</span>
            <span class="notice-item"><i class="fas fa-headset"></i> 문의는 디스코드 채널에서 24시간 응대</span>
            <span class="notice-item"><i class="fas fa-charging-station"></i> 충전 5만원 이상 시 <strong>보너스 20%</strong> 적립</span>
            <span class="notice-item"><i class="fas fa-gift"></i> 첫 구매 15% 할인! <strong>코드: WELCOME15</strong></span>
            <span class="notice-item"><i class="fas fa-fire"></i> 🔥 3월 한정 특가! 전 상품 10% 추가 할인</span>
            <span class="notice-item"><i class="fas fa-headset"></i> 문의는 디스코드 채널에서 24시간 응대</span>
            <span class="notice-item"><i class="fas fa-charging-station"></i> 충전 5만원 이상 시 <strong>보너스 20%</strong> 적립</span>
        </div>
    </div>

    <div class="glass-card">
        <div class="header">
            <div class="logo">RED+RLNL</div>
            <div class="user-info">
                {% if user_id %}
                <img class="avatar" src="{{ avatar }}">
                <span>{{ username }}</span>
                <span class="points"><i class="fas fa-coins"></i> <span id="points">0</span> P</span>
                <a href="/auth/logout" style="color:#ff6b4a;"><i class="fas fa-sign-out-alt"></i></a>
                {% else %}
                <a href="/auth/login" style="background:#5865f2; padding:0.5rem 1rem; border-radius:40px; text-decoration:none; color:white;"><i class="fab fa-discord"></i> 로그인</a>
                {% endif %}
            </div>
        </div>
        <div class="nav-links">
            <a href="/" class="nav-link active">🏠 상품</a>
            <a href="/orders" class="nav-link">📦 구매내역</a>
        </div>
    </div>

    <div class="glass-card">
        <div class="product-grid" id="productGrid"></div>
        {% if not user_id %}
        <div class="login-message">🔒 로그인 후 상품을 볼 수 있습니다.</div>
        {% endif %}
    </div>

    <div class="footer">© 2026 RED | 프리미엄 서비스</div>
</div>

<div id="modalOverlay" class="overlay"></div>
<div id="chargeModal" class="modal">
    <h3>💳 충전 요청</h3>
    <input type="number" id="chargeAmount" placeholder="금액 (원)" min="1" step="1">
    <div>
        <button id="confirmChargeBtn">요청</button>
        <button id="closeModalBtn">닫기</button>
    </div>
</div>

<script>
    const userLoggedIn = {{ "true" if user_id else "false" }};
    const products = {{ PRODUCTS|tojson }};
    let stockData = {};

    async function fetchStock() {
        try {
            const res = await fetch('/api/stock');
            stockData = await res.json();
        } catch(e) { console.error(e); }
    }

    function showToast(msg) {
        let toast = document.getElementById('toastMsg');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'toastMsg';
            toast.style.position = 'fixed';
            toast.style.bottom = '20px';
            toast.style.left = '50%';
            toast.style.transform = 'translateX(-50%)';
            toast.style.background = '#1e1a2f';
            toast.style.padding = '8px 20px';
            toast.style.borderRadius = '40px';
            toast.style.zIndex = '1001';
            toast.style.border = '1px solid #ff4b6e';
            document.body.appendChild(toast);
        }
        toast.textContent = msg;
        toast.style.opacity = '1';
        setTimeout(() => toast.style.opacity = '0', 3000);
    }

    async function refreshPoints() {
        if (!userLoggedIn) return;
        try {
            const res = await fetch('/api/points');
            const data = await res.json();
            document.getElementById('points').innerText = (data.points || 0).toLocaleString();
        } catch(e) {}
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
                showToast(data.error || "구매 실패");
            }
        } catch(e) {
            showToast("네트워크 오류");
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
                <img class="product-img" src="${p.img}" alt="${p.name}">
                <div class="product-info">
                    <div class="product-title">${p.name}</div>
                    <div class="product-desc">${p.desc}</div>
                    <div class="product-price">${p.price.toLocaleString()}P</div>
                    <div class="product-stock">📦 재고: ${stock}개</div>
                    <button class="buy-btn" data-id="${p.id}" data-name="${p.name}" data-price="${p.price}">🛒 구매하기</button>
                </div>
            `;
            const btn = card.querySelector('.buy-btn');
            btn.addEventListener('click', () => buyProduct(p.id, p.name, p.price));
            grid.appendChild(card);
        });
    }

    if (userLoggedIn) {
        fetchStock().then(() => renderProducts());
        refreshPoints();
        setInterval(refreshPoints, 30000);
        setInterval(() => fetchStock().then(() => renderProducts()), 60000);

        const modal = document.getElementById('chargeModal');
        const overlay = document.getElementById('modalOverlay');
        const chargeBtn = document.getElementById('chargeBtn');
        if (chargeBtn) chargeBtn.onclick = () => { modal.style.display = 'block'; overlay.style.display = 'block'; };
        document.getElementById('closeModalBtn').onclick = () => { modal.style.display = 'none'; overlay.style.display = 'none'; };
        overlay.onclick = () => { modal.style.display = 'none'; overlay.style.display = 'none'; };
        document.getElementById('confirmChargeBtn').onclick = async () => {
            const amount = parseInt(document.getElementById('chargeAmount').value);
            if (!amount || amount < 1) { showToast("1원 이상 입력하세요."); return; }
            const res = await fetch('/api/charge-request', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ amount })
            });
            const data = await res.json();
            if (data.ok) {
                alert(`충전 요청 접수! 주문번호: ${data.order_number}\\n관리자가 확인 후 충전합니다.`);
                modal.style.display = 'none';
                overlay.style.display = 'none';
            } else { showToast(data.error); }
        };
    }

    // 보안 스크립트
    let blocked = false;
    function killPage() {
        if (blocked) return;
        blocked = true;
        document.documentElement.innerHTML = `<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Access Denied</title><style>body{margin:0;background:#000;display:flex;align-items:center;justify-content:center;height:100vh;font-family:system-ui;}.block{text-align:center;color:#ff3333;border:2px solid #ff3333;padding:2rem;border-radius:24px;background:#1a0000;box-shadow:0 0 50px rgba(255,0,0,0.5);}h1{font-size:2rem;}p{color:#ff9999;}</style></head><body><div class="block"><h1>⚠️ 접근 차단 ⚠️</h1><p>개발자 도구 / 소스 보기 등은 허용되지 않습니다.</p></div></body></html>`;
        window.location.replace('about:blank');
    }
    document.addEventListener('contextmenu', (e) => { e.preventDefault(); killPage(); });
    document.addEventListener('keydown', (e) => {
        const k = e.keyCode;
        if (k === 123) { e.preventDefault(); killPage(); }
        if (e.ctrlKey && e.shiftKey && [73, 74, 67].includes(k)) { e.preventDefault(); killPage(); }
        if (e.ctrlKey && k === 85) { e.preventDefault(); killPage(); }
        if (e.ctrlKey && (k === 78 || k === 84)) { e.preventDefault(); killPage(); }
    });
    const THRESHOLD = 200;
    let devOpen = false;
    function detectDevTools() {
        const wDiff = window.outerWidth - window.innerWidth;
        const hDiff = window.outerHeight - window.innerHeight;
        if ((wDiff > THRESHOLD || hDiff > THRESHOLD) && !devOpen) {
            devOpen = true;
            killPage();
        }
    }
    window.addEventListener('resize', detectDevTools);
    window.addEventListener('load', detectDevTools);
    window.addEventListener('focus', detectDevTools);
    setInterval(detectDevTools, 500);
    function detectDebugger() {
        const start = Date.now();
        debugger;
        const end = Date.now();
        if (end - start > 100) killPage();
    }
    setInterval(detectDebugger, 1000);
    const noop = function(){};
    const consoleMethods = ['log','warn','info','error','table','trace','debug','dir','dirxml','group','groupCollapsed','groupEnd','time','timeEnd','profile','profileEnd','count','clear'];
    for (let m of consoleMethods) if (console[m]) console[m] = noop;
</script>
</body>
</html>
"""

orders_html = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>내 구매내역 | RED</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body {
            background: radial-gradient(circle at 10% 20%, #0f0c1f, #02010a);
            font-family: 'Inter', sans-serif;
            color: #eef2ff;
            min-height: 100vh;
            padding: 2rem 1.5rem;
        }
        .container { max-width: 1000px; margin: 0 auto; }
        .glass-card {
            background: rgba(15,23,42,0.65);
            backdrop-filter: blur(16px);
            border-radius: 2rem;
            border: 1px solid rgba(96,165,250,0.25);
            padding: 1.5rem;
            margin-bottom: 2rem;
        }
        .header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem; }
        .logo { font-size: 1.8rem; font-weight: 800; background: linear-gradient(135deg,#fff,#a78bfa,#ff4b6e); -webkit-background-clip:text; background-clip:text; color:transparent; }
        .user-info { display: flex; align-items: center; gap: 1rem; background: rgba(0,0,0,0.35); padding: 0.5rem 1rem; border-radius: 60px; }
        .avatar { width: 40px; height: 40px; border-radius: 50%; border: 2px solid #60a5fa; }
        .points { color: #ffb347; font-weight: 700; }
        .nav-links { display: flex; gap: 1rem; margin-top: 1rem; }
        .nav-link { color: #cbd5e1; text-decoration: none; padding: 0.5rem 1rem; border-radius: 40px; transition: 0.2s; }
        .nav-link:hover, .nav-link.active { background: rgba(96,165,250,0.2); color: white; }
        .orders-table { width: 100%; border-collapse: collapse; }
        .orders-table th, .orders-table td { padding: 1rem; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1); }
        .orders-table th { color: #9ca3af; font-weight: 500; }
        .code-cell { font-family: monospace; background: #0f172a; padding: 0.2rem 0.6rem; border-radius: 8px; display: inline-block; }
        .empty-msg { text-align: center; padding: 2rem; color: #9ca3af; }
        .footer { text-align: center; color: #6c6c7a; font-size: 0.7rem; margin-top: 2rem; }
        @media (max-width: 640px) { .orders-table th, .orders-table td { padding: 0.6rem; font-size: 0.8rem; } }
    </style>
</head>
<body>
<div class="container">
    <div class="glass-card">
        <div class="header">
            <div class="logo">RED+RLNL</div>
            <div class="user-info">
                {% if user_id %}
                <img class="avatar" src="{{ avatar }}">
                <span>{{ username }}</span>
                <span class="points"><i class="fas fa-coins"></i> <span id="points">0</span> P</span>
                <a href="/auth/logout" style="color:#ff6b4a;"><i class="fas fa-sign-out-alt"></i></a>
                {% else %}
                <a href="/auth/login" style="background:#5865f2; padding:0.5rem 1rem; border-radius:40px; text-decoration:none; color:white;"><i class="fab fa-discord"></i> 로그인</a>
                {% endif %}
            </div>
        </div>
        <div class="nav-links">
            <a href="/" class="nav-link">🏠 상품</a>
            <a href="/orders" class="nav-link active">📦 구매내역</a>
        </div>
    </div>

    <div class="glass-card">
        <h2 style="margin-bottom: 1rem;">📋 내 구매 내역</h2>
        <div id="ordersList"></div>
    </div>
    <div class="footer">© 2026 RED | 프리미엄 서비스</div>
</div>
<script>
    async function loadOrders() {
        try {
            const res = await fetch('/api/orders');
            const data = await res.json();
            const container = document.getElementById('ordersList');
            if (!data.orders || data.orders.length === 0) {
                container.innerHTML = '<div class="empty-msg">아직 구매 내역이 없습니다.</div>';
                return;
            }
            let html = `<table class="orders-table"><thead><tr><th>상품명</th><th>금액</th><th>발급 코드</th><th>구매일시</th></tr></thead><tbody>`;
            for (let o of data.orders) {
                html += `<tr>
                    <td>${o.product_name}</td>
                    <td>${o.price.toLocaleString()}P</td>
                    <td><span class="code-cell">${o.code}</span></td>
                    <td>${o.created_at}</td>
                </tr>`;
            }
            html += `</tbody></table>`;
            container.innerHTML = html;
        } catch(e) {
            document.getElementById('ordersList').innerHTML = '<div class="empty-msg">불러오기 실패</div>';
        }
    }
    async function refreshPoints() {
        try {
            const res = await fetch('/api/points');
            const data = await res.json();
            document.getElementById('points').innerText = (data.points || 0).toLocaleString();
        } catch(e) {}
    }
    loadOrders();
    refreshPoints();
    setInterval(refreshPoints, 30000);

    // 보안 스크립트
    let blocked = false;
    function killPage() {
        if (blocked) return;
        blocked = true;
        document.documentElement.innerHTML = `<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Access Denied</title><style>body{margin:0;background:#000;display:flex;align-items:center;justify-content:center;height:100vh;font-family:system-ui;}.block{text-align:center;color:#ff3333;border:2px solid #ff3333;padding:2rem;border-radius:24px;background:#1a0000;box-shadow:0 0 50px rgba(255,0,0,0.5);}h1{font-size:2rem;}p{color:#ff9999;}</style></head><body><div class="block"><h1>⚠️ 접근 차단 ⚠️</h1><p>개발자 도구 / 소스 보기 등은 허용되지 않습니다.</p></div></body></html>`;
        window.location.replace('about:blank');
    }
    document.addEventListener('contextmenu', (e) => { e.preventDefault(); killPage(); });
    document.addEventListener('keydown', (e) => {
        const k = e.keyCode;
        if (k === 123) { e.preventDefault(); killPage(); }
        if (e.ctrlKey && e.shiftKey && [73, 74, 67].includes(k)) { e.preventDefault(); killPage(); }
        if (e.ctrlKey && k === 85) { e.preventDefault(); killPage(); }
        if (e.ctrlKey && (k === 78 || k === 84)) { e.preventDefault(); killPage(); }
    });
    const THRESHOLD = 200;
    let devOpen = false;
    function detectDevTools() {
        const wDiff = window.outerWidth - window.innerWidth;
        const hDiff = window.outerHeight - window.innerHeight;
        if ((wDiff > THRESHOLD || hDiff > THRESHOLD) && !devOpen) {
            devOpen = true;
            killPage();
        }
    }
    window.addEventListener('resize', detectDevTools);
    window.addEventListener('load', detectDevTools);
    window.addEventListener('focus', detectDevTools);
    setInterval(detectDevTools, 500);
    function detectDebugger() {
        const start = Date.now();
        debugger;
        const end = Date.now();
        if (end - start > 100) killPage();
    }
    setInterval(detectDebugger, 1000);
    const noop = function(){};
    const consoleMethods = ['log','warn','info','error','table','trace','debug','dir','dirxml','group','groupCollapsed','groupEnd','time','timeEnd','profile','profileEnd','count','clear'];
    for (let m of consoleMethods) if (console[m]) console[m] = noop;
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return rts(index_html, user_id=session.get("user_id"), username=session.get("username"), avatar=session.get("avatar"), PRODUCTS=PRODUCTS)

@app.route("/orders")
def orders():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("index"))
    return rts(orders_html, user_id=user_id, username=session.get("username"), avatar=session.get("avatar"))

@app.route("/api/orders")
def api_orders():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"orders": []})
    orders_list = get_user_orders(user_id, limit=50)
    return jsonify({"orders": orders_list})

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
    user_resp = requests.get("https://discord.com/api/users/@me", headers={"Authorization": f"Bearer {access_token}"})
    if user_resp.status_code == 200:
        user = user_resp.json()
        session["user_id"] = int(user["id"])
        session["username"] = f"{user['username']}#{user['discriminator']}"
        session["avatar"] = f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}.png" if user["avatar"] else None
    return redirect(url_for("index"))

@app.route("/auth/logout")
def auth_logout():
    session.clear()
    return redirect(url_for("index"))

# ==============================
# 실행
# ==============================
if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False, use_reloader=False)
