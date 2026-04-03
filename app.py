import os
import sqlite3
import requests
import random
import string
import threading
import asyncio
import logging
from datetime import datetime, timezone
from itertools import cycle
from typing import List, Optional
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
from discord.ext import commands
from dotenv import load_dotenv

# ==============================
# 기본 설정
# ==============================
logging.getLogger("discord.gateway").setLevel(logging.WARNING)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change")
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "dev-pass-change")

# 디스코드 OAuth2
DISCORD_CLIENT_ID = os.environ.get("DISCORD_CLIENT_ID", "1478639969009406004")
DISCORD_CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET", "여기에_시크릿키")
DISCORD_REDIRECT_URI = os.environ.get("DISCORD_REDIRECT_URI", "https://api.redkorea.store/auth/callback")

# 🔥 웹훅 URL (사용자님 제공 기준으로 수정)
ADMIN_WEBHOOK_URL = "https://discord.com/api/webhooks/1489485738168025279/nwe2k1dQl7f6lPpS9jCJJpHUXFD3d-dtcMCvS_NiDPXPsDtPW1hljJ1xFOdxPzf3QCxz"  # 관리자 채널
BUY_LOG_WEBHOOK_URL = "https://discord.com/api/webhooks/1488231305396224041/Fa_z7Wihwf9-k79aGNcvaLNj3emxWYxlFoD6xVGkgLxzZKig3Uc7MQpL8Nk93d4Pyfat"   # 구매 로그 채널

DB_PATH = os.path.join(os.path.dirname(__file__), "shop.db")

# ==============================
# DB 초기화
# ==============================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, points INTEGER DEFAULT 0)")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_name TEXT,
            price INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, charge_url TEXT)")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS product_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            code TEXT NOT NULL UNIQUE,
            used INTEGER DEFAULT 0
        )
    """)
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
    cur.execute("PRAGMA table_info(orders)")
    columns = [col[1] for col in cur.fetchall()]
    if "user_id" not in columns:
        cur.execute("ALTER TABLE orders ADD COLUMN user_id INTEGER DEFAULT 0")
    cur.execute("INSERT OR IGNORE INTO users (id, points) VALUES (1, 0)")
    cur.execute("INSERT OR IGNORE INTO settings (id, charge_url) VALUES (1, 'https://discord.gg/q6nJpYuFB8')")
    conn.commit()
    conn.close()

init_db()

# ==============================
# DB 함수 (포인트, 주문, 코드)
# ==============================
def get_points(user_id: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT points FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0

def add_points(user_id: int, amount: int) -> int:
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

def remove_points(user_id: int, amount: int) -> Optional[int]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT points FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    if not row or row[0] < amount:
        conn.close()
        return None
    new_balance = row[0] - amount
    cur.execute("UPDATE users SET points = ? WHERE id = ?", (new_balance, user_id))
    conn.commit()
    conn.close()
    return new_balance

def insert_order(user_id: int, product_name: str, price: int) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO orders (user_id, product_name, price) VALUES (?, ?, ?)", (user_id, product_name, price))
    conn.commit()
    conn.close()

def get_user_orders(user_id: int, limit: int = 5) -> List[dict]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT product_name, price, created_at FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT ?", (user_id, limit))
    rows = cur.fetchall()
    conn.close()
    return [{"product_name": r[0], "price": r[1], "created_at": r[2]} for r in rows]

def get_user_total_spent(user_id: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT SUM(price) FROM orders WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row and row[0] else 0

def add_product_code(product_id: str, code: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO product_codes (product_id, code, used) VALUES (?, ?, 0)", (product_id, code))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_unused_code(product_id: str) -> Optional[str]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT code FROM product_codes WHERE product_id = ? AND used = 0 LIMIT 1", (product_id,))
    row = cur.fetchone()
    if row:
        code = row[0]
        cur.execute("UPDATE product_codes SET used = 1 WHERE code = ?", (code,))
        conn.commit()
        conn.close()
        return code
    conn.close()
    return None

def get_code_stock(product_id: str) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM product_codes WHERE product_id = ? AND used = 0", (product_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0

def get_unused_codes(product_id: str) -> List[str]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT code FROM product_codes WHERE product_id = ? AND used = 0", (product_id,))
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]

def delete_code(code: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM product_codes WHERE code = ?", (code,))
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

# ==============================
# 충전 요청 (주문번호 발급)
# ==============================
def create_charge_request(user_id: int, amount: int) -> str:
    while True:
        order_num = ''.join(random.choices(string.digits, k=6))
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id FROM charge_requests WHERE order_number = ?", (order_num,))
        if not cur.fetchone():
            conn.close()
            break
        conn.close()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO charge_requests (order_number, user_id, amount, processed) VALUES (?, ?, ?, 0)",
                (order_num, user_id, amount))
    conn.commit()
    conn.close()
    return order_num

# ==============================
# 디스코드 봇
# ==============================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=".", intents=intents)

ADMIN_CHANNEL_ID = 1488221287531679915   # 실제 채널 ID (웹훅과 별개)
BUY_LOG_CHANNEL_ID = 1488221128286802143
REVIEW_CHANNEL_ID = 1487603259773419641
STATUS_MESSAGES = ["상담 환영", "문의는 티켓"]
status_cycle = cycle(STATUS_MESSAGES)
BUYER_ROLE_NAME = "구매자"

RED_PRODUCTS = [
    {"id": "wolf_lite", "name": "🔴𝙍𝙀𝘿-𝗪𝗢𝗟𝗙-𝗟𝗜𝗧𝗘", "desc": "라이트 버전으로 부담 없이 경험 해보는 패키지", "price": 7000},
    {"id": "wolf", "name": "🔴RED-𝗪𝗢𝗟𝗙", "desc": "공격적인 운영을 위한 하이레벨 패키지", "price": 13000},
    {"id": "kd_dropper", "name": "🔴RED-kd-dropper", "desc": "집중력과 몰입감을 높여주는 트레이닝 패키지", "price": 7000},
    {"id": "owo", "name": "🔴𝙍𝙀𝘿-𝐎𝐖𝐎", "desc": "AIMBOT 가까운 뼈 혹은 타겟 지정! 가성비 !!", "price": 7000},
]

async def is_buyer(member: discord.Member) -> bool:
    guild = member.guild
    if guild is None:
        return False
    role = discord.utils.get(guild.roles, name=BUYER_ROLE_NAME)
    return role is not None and role in member.roles

async def safe_dm_embed(user: discord.abc.User, embed: discord.Embed) -> None:
    try:
        dm = await user.create_dm()
        await dm.send(embed=embed)
    except Exception as e:
        print(f"[DM_EMBED_ERROR] user={user.id} | {e}")

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

class ProductSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(ProductSelect())

class ProductSelect(discord.ui.Select):
    def __init__(self):
        options = []
        for p in RED_PRODUCTS:
            stock = get_code_stock(p["id"])
            label = f"{p['name']} - {p['price']:,}P"
            description = f"{p['desc']} | 재고: {stock}개" if stock else f"{p['desc']} | 재고: 품절"
            options.append(discord.SelectOption(label=label, value=p["id"], description=description))
        super().__init__(placeholder="구매할 상품을 선택하세요", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        product_id = self.values[0]
        product = next((p for p in RED_PRODUCTS if p["id"] == product_id), None)
        if not product:
            embed = discord.Embed(title="❌ 오류", description="상품 정보를 찾을 수 없습니다.", color=0xff4444)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        user = interaction.user
        price = product["price"]
        product_name = product["name"]
        new_balance = remove_points(user.id, price)
        if new_balance is None:
            current = get_points(user.id)
            embed = discord.Embed(title="❌ 포인트 부족", description=f"필요 포인트: {price:,}P\n현재 포인트: {current:,}P", color=0xff4444)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        code = get_unused_code(product_id)
        if code is None:
            add_points(user.id, price)
            embed = discord.Embed(title="❌ 재고 부족", description=f"`{product_name}`의 재고가 소진되었습니다.\n관리자에게 문의해 주세요.", color=0xff4444)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        insert_order(user.id, product_name, price)
        # 관리자 채널 웹훅 (상세 로그)
        admin_embed = discord.Embed(title="✅ 구매 발생 (관리자용)", description=f"**유저:** {user.mention} (`{user.id}`)\n**상품명:** `{product_name}`\n**발급 코드:** `{code}`\n**차감 포인트:** {price:,}P\n**남은 포인트:** {new_balance:,}P", color=0x2ecc71)
        try:
            requests.post(ADMIN_WEBHOOK_URL, json={"embeds": [admin_embed.to_dict()]}, timeout=3)
        except:
            pass
        # 구매 로그 채널 웹훅 (익명)
        buy_embed = discord.Embed(title="🛒 구매 발생", description=f"익명의 유저가 **{product_name}** 을(를) 구매했습니다.", color=0x2ecc71)
        try:
            requests.post(BUY_LOG_WEBHOOK_URL, json={"embeds": [buy_embed.to_dict()]}, timeout=3)
        except:
            pass
        # DM 발송
        dm_embed = discord.Embed(title="✅ 구매 완료", description=f"**상품명:** {product_name}\n**발급 코드:** `{code}`\n**차감 포인트:** {price:,}P\n**남은 포인트:** {new_balance:,}P", color=0x2ecc71)
        dm_embed.set_footer(text="코드는 외부에 유출되지 않도록 주의해 주세요.")
        await safe_dm_embed(user, dm_embed)
        success_embed = discord.Embed(title="✅ 구매 완료", description=f"**{product_name}**\n차감 포인트: {price:,}P\n남은 포인트: {new_balance:,}P", color=0x2ecc71)
        view = AfterPurchaseView(product_name)
        await interaction.response.send_message(embed=success_embed, view=view, ephemeral=True)
        guild = interaction.guild
        if guild:
            role = discord.utils.get(guild.roles, name=BUYER_ROLE_NAME)
            if role and role not in user.roles:
                try:
                    await user.add_roles(role, reason="첫 구매로 인한 구매자 역할 부여")
                except Exception as e:
                    print(f"[ROLE_ERROR] {e}")

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
            order_list = [f"• `{o['created_at'][:10]}` **{o['product_name']}** - {o['price']:,}P" for o in orders]
            embed.add_field(name="📦 구매 내역", value="\n".join(order_list), inline=False)
        else:
            embed.add_field(name="📦 구매 내역", value="아직 구매 내역이 없습니다.", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🛒 구매", style=discord.ButtonStyle.primary, custom_id="red_buy")
    async def buy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ProductSelectView()
        embed = discord.Embed(title="📦 상품 선택", description="구매할 상품을 아래 메뉴에서 선택해 주세요.\n재고는 옵션 설명에 표시됩니다.", color=0x3498db)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class BuyerRedVendingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="💰 충전", style=discord.ButtonStyle.success, custom_id="buyer_red_charge")
    async def charge_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        points = get_points(user.id)
        embed = discord.Embed(
            title="💳 충전 안내 (구매자 전용)",
            description=(
                f"**아래 계좌로 입금 후, 관리자에게 입금 사실을 알려주세요.**\n\n"
                f"🏦 은행: 농협은행\n💳 계좌: `3521617659683`\n👤 예금주: 김대훈\n\n"
                f"📢 입금 완료 후 관리자에게 DM 또는 채팅으로 알려주시면 포인트를 지급해 드립니다.\n\n"
                f"📊 현재 포인트: **{points:,}P**"
            ),
            color=0x27ae60,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="📊 정보", style=discord.ButtonStyle.secondary, custom_id="buyer_red_info")
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
            order_list = [f"• `{o['created_at'][:10]}` **{o['product_name']}** - {o['price']:,}P" for o in orders]
            embed.add_field(name="📦 구매 내역", value="\n".join(order_list), inline=False)
        else:
            embed.add_field(name="📦 구매 내역", value="아직 구매 내역이 없습니다.", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🛒 구매", style=discord.ButtonStyle.primary, custom_id="buyer_red_buy")
    async def buy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ProductSelectView()
        embed = discord.Embed(title="📦 상품 선택", description="구매할 상품을 아래 메뉴에서 선택해 주세요.\n재고는 옵션 설명에 표시됩니다.", color=0x3498db)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# ==============================
# 관리자 충전 명령어
# ==============================
@bot.command(name="충전")
@commands.has_permissions(administrator=True)
async def charge_cmd(ctx: commands.Context, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.reply("❌ 0원 이상의 금액을 입력하세요.", delete_after=5)
        return
    new_balance = add_points(member.id, amount)
    await ctx.reply(f"✅ {member.mention} 님에게 {amount:,}P 충전 완료.\n현재 포인트: **{new_balance:,}P**", mention_author=False)
    dm_embed = discord.Embed(title="💰 충전 완료", description=f"**충전 포인트:** {amount:,}P\n**현재 포인트:** {new_balance:,}P", color=0x3498db)
    dm_embed.set_footer(text="문의사항은 관리자에게 문의하세요.")
    await safe_dm_embed(member, dm_embed)

@charge_cmd.error
async def charge_error(ctx: commands.Context, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.reply("❌ 관리자만 사용할 수 있습니다.", delete_after=5)
    else:
        await ctx.reply("❌ 사용법: `.충전 @유저 금액`", delete_after=5)

# ==============================
# 패널 생성 명령어
# ==============================
@bot.command(name="레드코리아패널")
@commands.has_permissions(administrator=True)
async def create_red_panel(ctx: commands.Context):
    embed = discord.Embed(title="🔴 RED KOREA - 탈콥", description="**🤖 디스코드 자동 자판기 🔄**\n\n버튼을 눌러 서비스를 이용하세요.", color=0xe74c3c)
    embed.set_footer(text="상담 환영 · 문의는 티켓")
    view = RedVendingView()
    await ctx.send(embed=embed, view=view)

@bot.command(name="레드코리아패널구매자")
@commands.has_permissions(administrator=True)
async def create_buyer_red_panel(ctx: commands.Context):
    embed = discord.Embed(title="🔴 RED KOREA - 탈콥 (구매자 전용)", description="**🤖 디스코드 자동 자판기 🔄**\n\n버튼을 눌러 서비스를 이용하세요.", color=0xe74c3c)
    embed.set_footer(text="구매자 전용 패널")
    view = BuyerRedVendingView()
    await ctx.send(embed=embed, view=view)

@bot.command(name="코드추가")
@commands.has_permissions(administrator=True)
async def add_code_cmd(ctx: commands.Context, product_id: str, *codes: str):
    valid_ids = [p["id"] for p in RED_PRODUCTS]
    if product_id not in valid_ids:
        await ctx.reply(f"❌ 유효한 상품 ID가 아닙니다. 가능: {', '.join(valid_ids)}", delete_after=10)
        return
    if not codes:
        await ctx.reply("❌ 추가할 코드를 입력하세요. 예: .코드추가 wolf_lite ABC-123 DEF-456", delete_after=10)
        return
    added = sum(1 for code in codes if add_product_code(product_id, code.strip()))
    failed = len(codes) - added
    await ctx.reply(f"✅ {added}개 추가 완료, {failed}개 실패 (중복 등)", delete_after=10)

@bot.command(name="코드목록")
@commands.has_permissions(administrator=True)
async def list_codes_cmd(ctx: commands.Context, product_id: str = None):
    if product_id is None:
        lines = []
        for p in RED_PRODUCTS:
            codes = get_unused_codes(p["id"])
            if codes:
                lines.append(f"**{p['name']}** (`{p['id']}`): {len(codes)}개")
                if len(codes) <= 10:
                    lines.append(f"  `{', '.join(codes)}`")
                else:
                    lines.append(f"  첫 10개: `{', '.join(codes[:10])}` ...")
            else:
                lines.append(f"**{p['name']}** (`{p['id']}`): 0개")
        await ctx.reply("\n".join(lines), delete_after=30)
    else:
        valid_ids = [p["id"] for p in RED_PRODUCTS]
        if product_id not in valid_ids:
            await ctx.reply(f"❌ 유효한 상품 ID가 아닙니다. 가능: {', '.join(valid_ids)}", delete_after=10)
            return
        codes = get_unused_codes(product_id)
        if codes:
            display = codes[:30]
            msg = f"**{product_id}** 미사용 코드 ({len(codes)}개):\n`" + "`, `".join(display) + "`"
            if len(codes) > 30:
                msg += f"\n... 외 {len(codes)-30}개"
            await ctx.reply(msg, delete_after=30)
        else:
            await ctx.reply(f"**{product_id}**에 미사용 코드가 없습니다.", delete_after=10)

@bot.command(name="코드삭제")
@commands.has_permissions(administrator=True)
async def delete_code_cmd(ctx: commands.Context, *, code: str):
    if delete_code(code):
        await ctx.reply(f"✅ 코드 `{code}` 삭제 완료.", delete_after=10)
    else:
        await ctx.reply(f"❌ 코드 `{code}`를 찾을 수 없습니다.", delete_after=10)

async def cycle_status():
    await bot.wait_until_ready()
    while not bot.is_closed():
        text = next(status_cycle)
        try:
            await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.watching, name=text))
        except Exception as e:
            print(f"[status_cycle] error: {e}")
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
# Flask 웹 라우트 (충전 요청)
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
        return jsonify({"ok": False, "error": "로그인이 필요합니다."}), 401
    data = request.get_json()
    amount = data.get("amount")
    if not amount or amount < 1:
        return jsonify({"ok": False, "error": "충전 금액을 입력해주세요"}), 400
    order_num = create_charge_request(user_id, amount)
    # 🔥 관리자 채널 웹훅으로만 전송 (구매 로그 채널에는 안 감)
    content = (
        f"💳 **충전 요청 접수**\n"
        f"유저: <@{user_id}>\n"
        f"금액: {amount:,}원\n"
        f"주문번호: `{order_num}`\n"
        f"계좌: 3521617659683 (농협, 김대훈)\n"
        f"입금 확인 후 `.충전 <@{user_id}> {amount}` 명령어로 포인트를 지급하세요."
    )
    try:
        requests.post(ADMIN_WEBHOOK_URL, json={"content": content}, timeout=3)
    except Exception as e:
        print(f"[WEBHOOK_ERROR] {e}")
    return jsonify({"ok": True, "order_number": order_num})

# ==============================
# 웹 디자인 (중앙 정렬)
# ==============================
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
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1.5rem;
        }
        .glass-card {
            background: rgba(15,23,42,0.65);
            backdrop-filter: blur(16px);
            border-radius: 2rem;
            border: 1px solid rgba(96,165,250,0.25);
            box-shadow: 0 25px 45px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.02);
            max-width: 540px;
            width: 100%;
            padding: 2rem 1.8rem;
            transition: transform 0.2s;
        }
        .glass-card:hover { transform: translateY(-2px); border-color: rgba(96,165,250,0.5); }
        .logo {
            font-size: 2rem;
            font-weight: 800;
            background: linear-gradient(135deg, #ffffff, #a78bfa, #ff4b6e);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            text-align: center;
            margin-bottom: 1.5rem;
        }
        .user-section {
            background: rgba(0,0,0,0.35);
            border-radius: 2rem;
            padding: 0.7rem 1.2rem;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-wrap: wrap;
            gap: 1rem;
            margin-bottom: 1.8rem;
            border: 1px solid rgba(96,165,250,0.2);
        }
        .user-info { display: flex; align-items: center; gap: 0.8rem; }
        .avatar { width: 40px; height: 40px; border-radius: 50%; border: 2px solid #60a5fa; object-fit: cover; }
        .username { font-weight: 600; font-size: 0.9rem; }
        .points-badge { background: rgba(255,180,71,0.15); padding: 0.35rem 0.9rem; border-radius: 40px; font-size: 0.8rem; font-weight: 600; color: #ffb347; }
        .points-badge i { margin-right: 0.3rem; }
        .login-btn { background: linear-gradient(135deg,#5865f2,#4752c4); color: white; text-decoration: none; padding: 0.5rem 1.2rem; border-radius: 40px; font-weight: 600; transition: 0.2s; display: inline-flex; align-items: center; gap: 0.5rem; }
        .login-btn:hover { transform: translateY(-2px); box-shadow: 0 6px 14px rgba(88,101,242,0.4); }
        .account-box { background: linear-gradient(135deg, rgba(37,99,235,0.15), rgba(147,51,234,0.1)); border-radius: 1.5rem; padding: 1.5rem; margin: 1.5rem 0; text-align: center; border: 1px solid rgba(96,165,250,0.3); }
        .account-box h2 { font-size: 1.2rem; margin-bottom: 0.8rem; }
        .account-number { font-size: 1.6rem; font-weight: 800; background: linear-gradient(135deg,#fff,#ffb347); -webkit-background-clip: text; background-clip: text; color: transparent; letter-spacing: 2px; margin: 0.5rem 0; }
        .charge-btn { background: linear-gradient(135deg,#ff4b6e,#ff6b4a); border: none; padding: 0.7rem 1.8rem; border-radius: 40px; font-weight: 700; color: white; cursor: pointer; margin-top: 1rem; transition: 0.2s; }
        .charge-btn:hover { transform: translateY(-2px); box-shadow: 0 8px 18px rgba(255,75,110,0.4); }
        .footer { text-align: center; margin-top: 2rem; color: #6c6c7a; font-size: 0.7rem; }
        .modal { display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%,-50%); background: #1e1a2f; backdrop-filter: blur(20px); padding: 1.8rem; border-radius: 1.5rem; z-index: 1000; width: 300px; text-align: center; border: 1px solid rgba(255,75,110,0.5); box-shadow: 0 20px 35px rgba(0,0,0,0.5); }
        .overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); backdrop-filter: blur(4px); z-index: 999; }
        input { width: 100%; padding: 0.6rem; margin: 1rem 0; border-radius: 12px; border: 1px solid #4b5563; background: #0f172a; color: white; font-size: 1rem; text-align: center; }
        .modal button { background: #ff4b6e; border: none; padding: 0.5rem 1rem; border-radius: 30px; color: white; cursor: pointer; margin: 0 0.5rem; font-weight: 600; transition: 0.1s; }
        .modal button:active { transform: scale(0.96); }
        @media (max-width: 500px) { .glass-card { padding: 1.5rem; } .account-number { font-size: 1.2rem; } }
    </style>
</head>
<body>
<div class="glass-card">
    <div class="logo">RED+RLNL</div>
    <div class="user-section">
        {% if user_id %}
        <div class="user-info">
            <img class="avatar" src="{{ avatar }}" alt="avatar">
            <span class="username">{{ username }}</span>
        </div>
        <div class="points-badge"><i class="fas fa-coins"></i> <span id="points">0</span> P</div>
        <a href="/auth/logout" style="color:#ff6b4a; text-decoration:none;"><i class="fas fa-sign-out-alt"></i></a>
        {% else %}
        <a href="/auth/login" class="login-btn"><i class="fab fa-discord"></i> 디스코드 로그인</a>
        {% endif %}
    </div>
    {% if user_id %}
    <div class="account-box">
        <h2><i class="fas fa-university"></i> 입금 계좌 정보</h2>
        <p>아래 계좌로 입금 후, 관리자에게 입금 사실을 알려주세요.</p>
        <div class="account-number">3521617659683</div>
        <p>예금주: 김대훈 | 농협은행</p>
        <button id="chargeBtn" class="charge-btn"><i class="fas fa-bolt"></i> 충전 요청</button>
    </div>
    {% endif %}
    <div class="footer">© 2026 RED | 프리미엄 서비스</div>
</div>
<div id="modalOverlay" class="overlay"></div>
<div id="chargeModal" class="modal">
    <h3>💳 충전 금액</h3>
    <input type="number" id="chargeAmount" placeholder="금액 (원)" min="1" step="1" autocomplete="off">
    <div>
        <button id="confirmChargeBtn">요청</button>
        <button id="closeModalBtn">닫기</button>
    </div>
</div>
<script>
    const userLoggedIn = {{ "true" if user_id else "false" }};
    let toastTimer = null;
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
            toast.style.fontSize = '0.8rem';
            toast.style.border = '1px solid #ff4b6e';
            document.body.appendChild(toast);
        }
        if (toastTimer) clearTimeout(toastTimer);
        toast.textContent = msg;
        toast.style.opacity = '1';
        toastTimer = setTimeout(() => toast.style.opacity = '0', 3000);
    }
    async function refreshPoints() {
        if (!userLoggedIn) return;
        try {
            const res = await fetch('/api/points');
            const data = await res.json();
            document.getElementById('points').innerText = (data.points || 0).toLocaleString();
        } catch(e) { console.error(e); }
    }
    refreshPoints();
    setInterval(refreshPoints, 30000);
    if (userLoggedIn) {
        const modal = document.getElementById('chargeModal');
        const overlay = document.getElementById('modalOverlay');
        const chargeBtn = document.getElementById('chargeBtn');
        const closeBtn = document.getElementById('closeModalBtn');
        const confirmBtn = document.getElementById('confirmChargeBtn');
        const amountInput = document.getElementById('chargeAmount');
        function showModal() { modal.style.display = 'block'; overlay.style.display = 'block'; }
        function hideModal() { modal.style.display = 'none'; overlay.style.display = 'none'; }
        chargeBtn.onclick = showModal;
        closeBtn.onclick = hideModal;
        overlay.onclick = hideModal;
        confirmBtn.onclick = async () => {
            const amount = parseInt(amountInput.value);
            if (!amount || amount < 1) { showToast("1원 이상 입력하세요."); return; }
            try {
                const res = await fetch('/api/charge-request', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ amount: amount })
                });
                const data = await res.json();
                if (data.ok) {
                    alert(`충전 요청 접수! 주문번호: ${data.order_number}\\n관리자가 확인 후 포인트를 지급합니다.`);
                    hideModal();
                    amountInput.value = '';
                } else { showToast(data.error || "오류 발생"); }
            } catch(e) { showToast("네트워크 오류"); }
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
# 실행
# ==============================
if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False, use_reloader=False)
