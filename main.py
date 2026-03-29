from flask import Flask, render_template, request, make_response
from flask import session, redirect, url_for, abort, jsonify,send_from_directory
import datetime,time,sqlite3,randomstring,os,datetime,hashlib,random,ast,requests,uuid
from discord_webhook import DiscordWebhook, DiscordEmbed
from twilio.rest import Client
from babel.numbers import format_number
import locale,re,secrets
import threading
from flask_apscheduler import APScheduler
from flask_paginate import get_page_args

panel_keypair = {os.environ.get("PANEL_KEY", ""): os.environ.get("PANEL_VALUE", "")}

app = Flask(__name__)
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()
app.config['SERVER_NAME'] = os.environ.get("SERVER_NAME", "holysharry.co")
cwdir =  os.path.dirname(__file__) + "/"

app.secret_key = os.environ.get("SECRET_KEY", randomstring.pick(30))
# def maxchragreset(name):
#     conn = sqlite3.connect(db(name))
#     cur = conn.cursor()
#     cur.execute("UPDATE users SET maxcharge = ?", (0,))
#     conn.commit()
#     conn.close()   
    
@scheduler.task('cron', id='maxchargereset', day='*')
def maxchargereset():
    store_list = os.listdir(f"{cwdir}/database/")
    for data in store_list:
        con = sqlite3.connect(f"{cwdir}/database/" + data)
        cur = con.cursor()
        cur.execute("UPDATE users SET maxcharge = ?;",(0,))
        con.commit()
        con.close()
@scheduler.task('cron', id='visitorstoday', day='*')
def visitorstoday():
    store_list = os.listdir(f"{cwdir}/database/")
    for data in store_list:
        con = sqlite3.connect(f"{cwdir}/database/" + data)
        cur = con.cursor()
        cur.execute("DELETE FROM visitorstoday;")
        con.commit()
        con.close()        
@scheduler.task('cron', id='visitorsweek', day_of_week ='mon')
def visitorsweek():
    store_list = os.listdir(f"{cwdir}/database/")
    for data in store_list:
        con = sqlite3.connect(f"{cwdir}/database/" + data)
        cur = con.cursor()
        cur.execute("DELETE FROM visitorsweek;")
        con.commit()
        con.close()
@scheduler.task('cron', id='visitorsmonth', month='*')
def visitorsmonth():
    store_list = os.listdir(f"{cwdir}/database/")
    for data in store_list:
        con = sqlite3.connect(f"{cwdir}/database/" + data)
        cur = con.cursor()
        cur.execute("DELETE FROM visitorsmonth;")
        con.commit()
        con.close()                           

@app.template_filter('lenjago')
def lenjago(jago, txt):
    return len(jago.split(txt))

app.jinja_env.filters['lenjago'] = lenjago

def number_format(value, locale_=None):
    if locale_ is None:
        locale_ = locale.getlocale()[0]
    return format_number(value, locale=locale_)

app.jinja_env.filters['number_format'] = number_format


if (os.path.isfile(f"{cwdir}ban.db")):
    pass
else:
    con = sqlite3.connect(f"{cwdir}ban.db") # 밴기능 db
    with con:
        cur = con.cursor()
        cur.execute("""CREATE TABLE "ban" ("ip" TEXT);""")
        con.commit()
    con.close

def is_expired(time):
    ServerTime = datetime.datetime.now()
    ExpireTime = datetime.datetime.strptime(time, '%Y-%m-%d %H:%M')
    if ((ExpireTime - ServerTime).total_seconds() >= 0):
        return False
    else:
        return True


def get_expiretime(time):
    ServerTime = datetime.datetime.now()
    ExpireTime = datetime.datetime.strptime(time, '%Y-%m-%d %H:%M')
    if ((ExpireTime - ServerTime).total_seconds() >= 0):
        how_long = (ExpireTime - ServerTime)
        days = how_long.days
        hours = how_long.seconds // 3600
        minutes = how_long.seconds // 60 - hours * 60
        return str(round(days)) + "일 " + str(round(hours)) + "시간"
    else:
        return False


def make_expiretime(days):
    ServerTime = datetime.datetime.now()
    ExpireTime = ServerTime + datetime.timedelta(days=days)
    ExpireTime_STR = (ServerTime + datetime.timedelta(days=days)).strftime('%Y-%m-%d %H:%M')
    return ExpireTime_STR


def add_time(now_days, add_days):
    ExpireTime = datetime.datetime.strptime(now_days, '%Y-%m-%d %H:%M')
    ExpireTime_STR = (ExpireTime + datetime.timedelta(days=add_days)).strftime('%Y-%m-%d %H:%M')
    return ExpireTime_STR


def nowstr():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def db(name):
    return cwdir + "database/" + name + ".db"

def hash(string):
    return str(hashlib.sha512((string + "saltysalt!@#%!@$!").encode()).hexdigest())

def search_user(name, id):
    con = sqlite3.connect(db(name))
    cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE id == ?", (id,))
    result = cur.fetchone()
    con.close()
    return result

def search_token(name, id):
    con = sqlite3.connect(db(name))
    cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE token == ?", (id,))
    result = cur.fetchone()
    con.close()
    return result

def get_info(name):
    con = sqlite3.connect(db(name))
    cur = con.cursor()
    cur.execute("SELECT * FROM info;")
    result = cur.fetchone()
    con.close()
    return result

def search_chargewait(name, id):
    con = sqlite3.connect(db(name))
    cur = con.cursor()
    cur.execute("SELECT * FROM bankwait WHERE id == ?", (id,))
    result = cur.fetchone()
    con.close()
    return result

def search_prodintroduce(name, id):
    con = sqlite3.connect(db(name))
    cur = con.cursor()
    cur.execute("SELECT * FROM products WHERE id == ?", (id,))
    result = cur.fetchone()
    con.close()
    return result

def get_products(name):
    con = sqlite3.connect(db(name))
    cur = con.cursor()
    cur.execute("SELECT * FROM sqlite_sequence WHERE name == ?", ("products",))
    result = cur.fetchone()
    con.close()
    return result[1]

def get_catagory(name):
    con = sqlite3.connect(db(name))
    cur = con.cursor()
    cur.execute("SELECT * FROM sqlite_sequence WHERE name == ?", ("category",))
    result = cur.fetchone()
    con.close()
    return result[1]

def gennum(name):
    con = sqlite3.connect(db(name))
    cur = con.cursor()
    cur.execute("SELECT * FROM sqlite_sequence WHERE name == ?", ("products",))
    result = cur.fetchone()
    con.close()
    return result[1] + 1

def genid(name,  **args):
    con = sqlite3.connect(db(name))
    cur = con.cursor()
    sql = "SELECT * FROM " +  "products" + " WHERE "
    c = 1
    keys = args.keys()
    for i in keys:
        if len(keys) == c:
            sql += i + "=%s "
        else:
            sql += i + "=%s and "
        c += 1
        cur.execute(sql, tuple(args.values()))
        result = cur.fetchall()
        con.commit()
        con.close()
        if len(result) == 0: return 0
        else: return result[0][1]      
        
def search_prod(name, id):
    con = sqlite3.connect(db(name))
    cur = con.cursor()
    cur.execute("SELECT * FROM products WHERE id == ?", (id,))
    result = cur.fetchone()
    con.close()
    return result

def search_popups(name, id):
    con = sqlite3.connect(db(name))
    cur = con.cursor()
    cur.execute("SELECT * FROM popups WHERE id == ?", (id,))
    result = cur.fetchone()
    con.close()
    return result

def search_category(name, id):
    con = sqlite3.connect(db(name))
    cur = con.cursor()
    cur.execute("SELECT * FROM category WHERE id == ?", (id,))
    result = cur.fetchone()
    con.close()
    return result

def addStock(name, id, stocks, oneline):
    conn = sqlite3.connect(db(name))
    cur = conn.cursor()
    for stock in stocks:
        cur.execute("INSERT INTO stock VALUES(?,?,?)", (id, stock, oneline))
    conn.commit()
    conn.close() 
    
def addraw(name, id, stocks, time):
    conn = sqlite3.connect(db(name))
    cur = conn.cursor()
    for stock in stocks:
     cur.execute("INSERT INTO raw VALUES(?,?,?);", (id, stock, time))
    conn.commit()
    conn.close()
def removeStock(name, id, stocks):
    conn = sqlite3.connect(db(name))
    cur = conn.cursor()
    cur.execute("DELETE FROM stock WHERE id == ? and stock == ?",(id, stocks))
    conn.commit()
    conn.close()            

def removeNULLStock(name, id, stocks):
    conn = sqlite3.connect(db(name))
    cur = conn.cursor()
    cur.execute("DELETE FROM stock WHERE id == ? and stock == ?",(id,stocks,))
    conn.commit()
    conn.close()   
def getip():
    return request.headers.get("CF-Connecting-IP", request.remote_addr)

def getAllStock(name, id):
    conn = sqlite3.connect(db(name))
    cur = conn.cursor()
    cur.execute("SELECT * FROM stock WHERE id == ?", (id,))
    stocks = cur.fetchall()
    conn.close()
    return stocks

def get_prod(name, id):
    con = sqlite3.connect(db(name))
    cur = con.cursor()
    cur.execute("SELECT * FROM products WHERE id == ?", (id,))
    result = cur.fetchone()
    con.close()
    return result
def get_raw(name, id):
    con = sqlite3.connect(db(name))
    cur = con.cursor()
    cur.execute("SELECT * FROM raw WHERE id == ?", (id,))
    result = cur.fetchone()
    con.close()
    return result
def get_sto(name, id):
    con = sqlite3.connect(db(name))
    cur = con.cursor()
    cur.execute("SELECT * FROM stock WHERE id == ?", (id,))
    result = cur.fetchall()
    con.close()
    return result
def get_category(name, id):
    con = sqlite3.connect(db(name))
    cur = con.cursor()
    cur.execute("SELECT * FROM category WHERE id == ?", (id,))
    result = cur.fetchall()
    con.close()
    return result
def get_prodtest(name, id):
    con = sqlite3.connect(db(name))
    cur = con.cursor()
    cur.execute("SELECT * FROM products WHERE id == ?", (id,))
    result = cur.fetchone()
    con.close()
    return result

def get_price(name, id , userrank, prodtype):
    if(userrank == "관리자" or userrank == "부관리자"):
        con = sqlite3.connect(db(name))
        cur = con.cursor()
        cur.execute("SELECT * FROM price WHERE product_id == ? and rank == ? and prod1 == ?", (id,"구매자",prodtype))
        result = cur.fetchone()
        con.close()
        return result
    elif(userrank == "미인증"):
        con = sqlite3.connect(db(name))
        cur = con.cursor()
        cur.execute("SELECT * FROM price WHERE product_id == ? and rank == ? and prod1 == ?", (id,"비구매자",prodtype))
        result = cur.fetchone()
        con.close()
        return result
    else:
        con = sqlite3.connect(db(name))
        cur = con.cursor()
        cur.execute("SELECT * FROM price WHERE product_id == ? and rank == ? and prod1 == ?", (id,userrank,prodtype))
        result = cur.fetchone()
        con.close()
        return result
        
    
def generateOTP():
    return random.randrange(100000,999999)
    
def getOTPApi(name,id,getnumber):
    otp = generateOTP()
    con = sqlite3.connect(db(name))
    cur = con.cursor()
    cur.execute("INSERT INTO smstest VALUES(?, ?, ?);", (id,getnumber,str(otp)))
    con.commit()
    con.close()
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    client = Client(account_sid, auth_token)
    body = "[인증번호] " + "["+ str(otp) +"]" + "를 입력해주세요."
    message = client.messages.create(                              
    body=body,
    from_="+15017122661",       
    to=getnumber
    )
    if(message.sid):
        return True
    else:
        False
        
def getsms(name,getnumber):
    con = sqlite3.connect(db(name))
    cur = con.cursor()
    cur.execute("SELECT * FROM smstest WHERE sms == ?" , (getnumber,))
    _product = cur.fetchone()
    con.close()
    if(_product):
        return True
    else:
        False   

def getcategoryid(name,id):
    con = sqlite3.connect(db(name))
    cur = con.cursor()
    cur.execute("SELECT * FROM category")
    category1 = cur.fetchall()
    category = category1
    cur.execute("SELECT * FROM products WHERE id == ?", (id,))
    test = cur.fetchone()
    _category = []
    for i in category:
        getnum = test[5]
        getint = int(getnum)
        _category.append([i[0], i[1], getint])
    con.close() 
    return _category

def getuserrank(name,id):
    con = sqlite3.connect(db(name))
    cur = con.cursor()
    cur.execute("SELECT * FROM rank")
    category1 = cur.fetchall()
    category = category1
    cur.execute("SELECT * FROM users WHERE id == ?", (id,))
    test = cur.fetchone()
    getnum = test[8]
    _category = []
    for i in category:      
        _category.append([i[0], getnum,i[1]])
    con.close() 
    return _category

def gethyperlink(name,id):
    con = sqlite3.connect(db(name))
    cur = con.cursor()
    cur.execute("SELECT * FROM linksel")
    category1 = cur.fetchall()
    category = category1
    cur.execute("SELECT * FROM hyperlink WHERE id == ?", (id,))
    test = cur.fetchone()
    _category = []
    for i in category:
        unauth = test[3]
        nonbuyer = test[4]
        buyer = test[5]
        vip = test[6]
        vvip = test[7]
        reseller = test[8]
        _category.append([i[0], i[1],unauth,nonbuyer,buyer,vip,vvip,reseller])
    con.close() 
    return _category

def getbanktype(name,id):
    con = sqlite3.connect(db(name))
    cur = con.cursor()
    cur.execute("SELECT * FROM banktype")
    category1 = cur.fetchall()
    category = category1
    _category = []
    for i in category:
        _category.append([i[0],i[1],id])
    con.close() 
    return _category


def getranktest(name, id):
    if(id == 0):
        con = sqlite3.connect(db(name))
        cur = con.cursor()
        cur.execute("SELECT * FROM rank WHERE id == ?", (1,))
        result = cur.fetchone()
        con.close()
        return result[1] 
    else:
        con = sqlite3.connect(db(name))
        cur = con.cursor()
        cur.execute("SELECT * FROM rank WHERE id == ?", (id,))
        result = cur.fetchone()
        con.close()
        return result[1]
def getranktest2(name, id):
    con = sqlite3.connect(db(name))
    cur = con.cursor()
    cur.execute("SELECT * FROM rank WHERE id == ?", (id,))
    result = cur.fetchone()
    con.close()
    return result[1]            
def getui(name):
    con = sqlite3.connect(db(name))
    cur = con.cursor()
    cur.execute("SELECT * FROM ui;")
    result = cur.fetchone()  
    con.close()
    return result
    
@app.route("/", methods=["GET", "POST"])
def create():
    return abort(404)

@app.route("/file/<path:path>", methods=["GET", "POST"])
def download(path):
    try:
        return send_from_directory('file', path)
    except FileNotFoundError:
        return abort(404)

@app.route("/checkversion", methods=["GET"])
def filevercheck():
    conn = sqlite3.connect(f"{cwdir}leagueoflegends.db")
    curr = conn.cursor()
    curr.execute("SELECT * FROM upload") 
    versioncheck = curr.fetchone()              
    conn.close()
    return render_template("lol.html", versioncheck=versioncheck[0])     
@app.route("/smsotp", subdomain='<name>',methods=["POST"])
def smsotp(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (name.isalpha()):
            if (os.path.isfile(db(name))):
                if (name in session):
                    conn = sqlite3.connect(db(name))
                    with conn:
                        curr = conn.cursor()
                        curr.execute("SELECT * FROM smstest WHERE id == ?;", (session[name],))
                        chargereq_info = curr.fetchone()
                        if (chargereq_info != None):
                            return "이미 진행 중인 인증 신청이 있습니다 관리자에게 문의해주세요."
                        else:
                            if ("phonenumber" in request.get_json()):
                                server_info = get_info(name)
                                userinfo = search_user(name, session[name])
                                if(server_info[28] != 0):
                                    if(userinfo[8] == 0):
                                        getnumber = request.get_json()["phonenumber"]
                                        test2 = getnumber.replace("-","")
                                        Result = "+82" + test2
                                        test = getOTPApi(name,session[name],Result)
                                        if test:
                                            curr.execute("UPDATE users SET phonenumber = ? WHERE id == ?", (str(getnumber), session[name]))
                                            conn.commit()
                                            curr.execute("UPDATE info SET smscount = smscount - ?", (1,))
                                            conn.commit()
                                            try:
                                                webhook = DiscordWebhook(username="HOLYSHARRY.CO", avatar_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png", url=server_info[14])
                                                embed = DiscordEmbed(title="**실시간 문자 인증 알림**", value="",color=0x191A2F)
                                                embed.add_embed_field(name='아이디', value=f'{session[name]}',inline=False)
                                                embed.add_embed_field(name='전화번호', value=f'{getnumber}',inline=False)
                                                embed.add_embed_field(name='아이피', value=f'{getip()}',inline=False)
                                                embed.add_embed_field(name='인증상태', value='문자 전송 완료',inline=False)
                                                embed.add_embed_field(name='전송시간', value=f'{nowstr()}',inline=False)
                                                embed.set_footer(text='HOLYSHARRY.CO', icon_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png")
                                                embed.set_timestamp()
                                                webhook.add_embed(embed)
                                                webhook.execute()
                                            except:
                                                print("Webhook Error")   
                                            return "ok"
                                        else:
                                            return "error"
                                else:  
                                    return "인증 건수 초과"
                            else:
                                return "알 수 없는 오류입니다."
                    conn.close()  
                else:
                    return "로그인이 해제되었습니다. 다시 로그인해주세요."
            else:
                abort(404)
        else:
            abort(404)   
@app.route("/check", subdomain='<name>', methods=["POST"])
def check(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (name.isalpha()):
            if (os.path.isfile(db(name))):
                if (name in session):
                    if ("amount" in request.get_json()):
                        getnumber = request.get_json()["amount"]
                        server_info = get_info(name)
                        userinfo = search_user(name, session[name])
                        if(server_info[28] != 0):
                            if(userinfo[8] == 0):
                                test = getsms(name,getnumber)
                                if test:
                                    conn = sqlite3.connect(db(name))
                                    curr = conn.cursor()
                                    curr.execute("UPDATE users SET rankdata1 = ? WHERE id == ?", (1, session[name]))
                                    conn.commit()
                                    curr.execute("DELETE FROM smstest WHERE id == ?;", (session[name],))
                                    conn.commit()
                                    curr.execute("SELECT * FROM users WHERE id == ?;", (session[name],))
                                    getphone = curr.fetchone()
                                    conn.close()
                                    try:
                                        webhook = DiscordWebhook(username="HOLYSHARRY.CO", avatar_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png", url=server_info[14])
                                        embed = DiscordEmbed(title="**실시간 문자 인증 알림**", value="",color=0x191A2F)
                                        embed.add_embed_field(name='아이디', value=f'{session[name]}',inline=False)
                                        embed.add_embed_field(name='전화번호', value=f'{getphone[10]}',inline=False)
                                        embed.add_embed_field(name='인증번호', value=f'{getnumber}',inline=False)
                                        embed.add_embed_field(name='인증상태', value='성공',inline=False)
                                        embed.add_embed_field(name='아이피', value=f'{getip()}',inline=False)
                                        embed.add_embed_field(name='인증시간', value=f'{nowstr()}',inline=False)
                                        embed.set_footer(text='HOLYSHARRY.CO', icon_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png")
                                        embed.set_timestamp()
                                        webhook.add_embed(embed)
                                        webhook.execute()
                                    except:
                                        print("Webhook Error")    
                                    return "ok"
                                else:
                                    return "실패"
                        else:
                            return "인증 건수 초과"     
                    else:
                        return "알 수 없는 오류입니다."
                else:
                    return "로그인이 해제되었습니다. 다시 로그인해주세요."
            else:
                abort(404)
        else:
            abort(404)                
@app.route("/", subdomain='<name>', methods=["GET"])
def index(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (name.isalpha()):
            if (os.path.isfile(db(name))):
                if (name in session):
                    return redirect("notice")
                else:
                    return redirect(url_for('login', name = name))
            else:
                abort(404)
        else:
            abort(404)
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d
@app.route("/api/v1", subdomain='<name>', methods=["POST"])
def getapiuserid(name):
        if (request.method == "POST"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if ("token" in request.get_json()):
                        user_info = search_token(name, request.get_json()["token"])
                        if (user_info != None):
                            resultid = user_info[0]
                            con = sqlite3.connect(db(name))
                            con.row_factory = dict_factory
                            cur = con.cursor()
                            cur.execute("SELECT id, nowbuytime, product,maxprice,count(*), group_concat(buycode,',') FROM buylogtest WHERE id = ? GROUP BY nowbuytime HAVING count(*) > 0 ORDER BY nowbuytime DESC LIMIT 5;",(resultid,)) # 5개 제한
                            test = cur.fetchall()
                            con.close()    
                            return {"buylog": test ,"code": resultid }
                        else:
                            return {"buylog": "None","code": "None"}
                    else:
                        return {"buylog": "Error","code": "Error"}
                else:
                    abort(404)
            else:
                abort(404)
@app.route("/login", subdomain='<name>', methods=["GET", "POST"])
def login(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "GET"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        return redirect("notice")
                    else:
                        info = get_info(name)
                        if (str(info[6]) != ""):
                            return render_template("403.html", reason=info[6])
                        else:
                            return render_template("login.html", name=info[0], background=info[13])
                else:
                    abort(404)
            else:
                abort(404)
        else:
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        return redirect("shop")
                    else:
                        if ("id" in request.form and "pw" in request.form):
                            user_info = search_user(name, request.form["id"])
                            if (user_info != None):
                                if (user_info[1] == hash(request.form["pw"])):
                                    if (user_info[5] == ""):
                                        con = sqlite3.connect(db(name))
                                        cur = con.cursor()
                                        cur.execute("SELECT * FROM visitorstoday WHERE ip == ?;", (getip(),))
                                        visitorstoday = cur.fetchone()
                                        cur.execute("SELECT * FROM visitorsweek WHERE ip == ?;", (getip(),))
                                        visitorsweek = cur.fetchone()
                                        cur.execute("SELECT * FROM visitorsmonth WHERE ip == ?;", (getip(),))
                                        visitorsmonth = cur.fetchone()
                                        if(visitorstoday == None):
                                            cur.execute("INSERT INTO visitorstoday VALUES(?);", (getip(),))
                                            con.commit()
                                        if(visitorsweek == None):  
                                            cur.execute("INSERT INTO visitorsweek VALUES(?);", (getip(),))
                                            con.commit()
                                        if(visitorsmonth == None):
                                            cur.execute("INSERT INTO visitorsmonth VALUES(?);", (getip(),))
                                            con.commit()       
                                        con.close() 
                                        server_info = get_info(name)
                                        session[name] = request.form["id"]
                                        if (server_info[19] != None):
                                            try:
                                                webhook = DiscordWebhook(username="HOLYSHARRY.CO", avatar_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png", url=server_info[14])
                                                embed = DiscordEmbed(title="**실시간 로그인 알림**", value="",color=0x191A2F)
                                                embed.add_embed_field(name='아이디', value=f'{request.form["id"]}',inline=False)
                                                embed.add_embed_field(name='접속 시간', value=f'{nowstr()}',inline=False)
                                                embed.add_embed_field(name='아이피', value=f'{getip()}',inline=False)
                                                embed.set_footer(text='HOLYSHARRY.CO', icon_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png")
                                                embed.set_timestamp()
                                                webhook.add_embed(embed)
                                                webhook.execute()
                                            except:
                                                print("Webhook Error")
                                        return '<script>window.location.href = "notice"</script>'
                                    else:
                                        reason = user_info[6]
                                        return f'<script>alert(`관리자에 의해 차단된 계정입니다.\n차단 사유 : {reason}`); window.location.href = "login";</script>'
                                else:
                                    return '<script>alert("비밀번호가 틀렸습니다."); window.location.href = "login"</script>'
                            else:
                                return '<script>alert("아이디가 틀렸습니다."); window.location.href = "login"</script>'
                        else:
                            return '<script>alert("잘못된 접근입니다."); window.location.href = "login"</script>'
                else:
                    abort(404)
            else:
                abort(404)

@app.route("/register", subdomain='<name>',methods=["GET", "POST"])
def register(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "GET"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        return redirect("shop")
                    else:
                        info = get_info(name)
                        if (str(info[6]) != ""):
                            return render_template("403.html", reason=info[6])
                        elif (is_expired(info[7])):
                            return render_template("403.html", reason="라이센스 연장이 필요합니다.")
                        else:
                            return render_template("register.html", name=info[0], background=info[15])
                else:
                    abort(404)
            else:
                abort(404)
        else:
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        return redirect("shop")
                    else:
                        if ("id" in request.form and "pw" in request.form):
                            user_info = search_user(name, request.form["id"])
                            if (user_info == None):
                                con = sqlite3.connect(db(name))
                                cur = con.cursor()
                                cur.execute("SELECT * FROM users WHERE ip == ?;", (getip(),))
                                iplist = cur.fetchone()
                                con.close()
                                if (iplist == None):
                                    reg = re.compile(r'[a-z][^0-9]')
                                    if reg.match(request.form["id"]):
                                        if ((len(request.form["id"]) >= 6 and len(request.form["id"]) <= 24) and (len(request.form["pw"]) >= 6 and len(request.form["pw"]) <= 24)):
                                            con = sqlite3.connect(db(name))
                                            cur = con.cursor()
                                            cur.execute("INSERT INTO users VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ? ,?);", (request.form["id"], hash(request.form["pw"]), getip(), 0, "[]", "", "", request.form["tag"], 1, 0,None,"true","[]",0,None))
                                            con.commit()
                                            con.close()
                                            session.pop(name, None)
                                            session[name] = request.form["id"]
                                            server_info = get_info(name)
                                            if (server_info[14] != None):
                                                try:
                                                    webhook = DiscordWebhook(username="HOLYSHARRY.CO", avatar_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png", url=server_info[14])
                                                    embed = DiscordEmbed(title="**실시간 회원가입 알림**", value="",color=0x191A2F)
                                                    embed.add_embed_field(name='가입한 아이디', value=f'{request.form["id"]}',inline=False)
                                                    embed.add_embed_field(name='가입 시간', value=f'{nowstr()}',inline=False)
                                                    embed.add_embed_field(name='아이피', value=f'{getip()}',inline=False)
                                                    embed.set_footer(text='HOLYSHARRY.CO', icon_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png")
                                                    embed.set_timestamp()
                                                    webhook.add_embed(embed)
                                                    webhook.execute()
                                                except:
                                                    print("Webhook Error")
                                                return '<script>alert("회원가입에 성공했습니다!"); window.location.href = "notice"</script>'
                                        else:
                                            return '<script>alert("아이디 및 암호는 6 ~ 24자입니다."); window.location.href = "register"</script>'
                                    else:
                                        return '<script>alert("아이디의 형식이 올바르지 않습니다."); window.location.href = "register"</script>'
                                    
                                else:
                                    return '<script>alert("이미 해당 IP로 가입된 계정이 있습니다."); window.location.href = "register"</script>'
                            else:
                                return '<script>alert("이미 존재하는 아이디입니다."); window.location.href = "register"</script>'
                        else:
                            return '<script>alert("잘못된 접근입니다."); window.location.href = "register"</script>'
                else:
                    abort(404)
            else:
                abort(404)                
@app.route("/sms_verify", subdomain='<name>',methods=["GET"])
def sms_verify(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (name.isalpha()):
            if (os.path.isfile(db(name))):
                if (name in session):
                    info = get_info(name)
                    user_info = search_user(name, session[name])
                    if (str(info[6]) != ""):
                            return render_template("403.html", reason=info[6])
                    elif (is_expired(info[7])):
                        return render_template("403.html", reason="라이센스 연장이 필요합니다.")
                    else:
                        getcat = getcategory(name)
                        getname = name
                        getuicolor = getui(name)
                        getranktesta = getranktest(name,user_info[8])
                        con = sqlite3.connect(db(name))
                        cur = con.cursor()
                        cur.execute("SELECT * FROM hyperlink")
                        link = cur.fetchall()
                        cur.execute("SELECT * FROM buylogtest")
                        getallbuylog = cur.fetchall()
                        links = []
                        for i in link:
                            getrank = user_info[8]
                            if (getrank == 6 or getrank == 7):
                                gegesgseg = 1
                             if (getrank == 0):
                                 nonBuy = i[4]
                                if (nonBuy == 1):
                                    gegesgseg = 1
                                else:
                                    gegesgseg = 0     
                            if (getrank == 1):
                                nonBuy = i[4]
                                if(nonBuy == 1):
                                    gegesgseg = 1
                                else:
                                    gegesgseg = 0        
                            if(getrank == 2):
                                Buy = i[5]
                                if(Buy == 1):
                                    gegesgseg = 1
                                else:
                                    gegesgseg = 0        
                            if(getrank == 3):
                                vip = i[6]
                                if(vip == 1):
                                    gegesgseg = 1
                                else:
                                    gegesgseg = 0
                            if(getrank == 4):
                                vvip = i[7]
                                if(vvip == 1):
                                    gegesgseg = 1    
                                else:
                                    gegesgseg = 0    
                            if(getrank == 5):
                                resell = i[8] 
                                if(resell == 1):
                                    gegesgseg = 1 
                                else:
                                    gegesgseg = 0                                    
                            links.append([i[0],i[1],i[2],gegesgseg])                   
                        con.close()
                        if(user_info[8] == 0 and info[28] != 0):
                            return render_template("sms_verify.html",ui=getuicolor,link=links, getrank=getranktesta,name=info[0] ,alllogs=getallbuylog,category=getcat, getname=getname,user_info=user_info, music=info[8], shopinfo=info, linking=info[14], url=name, file=info[16], channelio=info[21])
                        else:
                            return redirect("shop")
                else:
                    return redirect("login")
            else:
                abort(404)
        else:
             abort(404)
@app.route("/verify_code", subdomain='<name>',methods=["GET"])
def verify_code(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (name.isalpha()):
            if (os.path.isfile(db(name))):
                if (name in session):
                    info = get_info(name)
                    user_info = search_user(name, session[name])
                    if (str(info[6]) != ""):
                            return render_template("403.html", reason=info[6])
                    elif (is_expired(info[7])):
                        return render_template("403.html", reason="라이센스 연장이 필요합니다.")
                    else:
                        server_info = get_info(name)
                        user_info = search_user(name, session[name])
                        getcat = getcategory(name)
                        getname = name
                        getuicolor = getui(name)
                        getranktesta = getranktest(name,user_info[8])
                        con = sqlite3.connect(db(name))
                        cur = con.cursor()
                        cur.execute("SELECT * FROM hyperlink")
                        link = cur.fetchall()
                        cur.execute("SELECT * FROM buylogtest")
                        getallbuylog = cur.fetchall()
                        links = []
                        for i in link:
                            getrank = user_info[8]
                            if(getrank == 6 or getrank == 7):
                                gegesgseg = 1
                            if(getrank == 0):
                                noauth = i[3]
                                if(noauth == 1):
                                    gegesgseg = 1
                                else:
                                    gegesgseg = 0        
                            if(getrank == 1):
                                nonBuy = i[4]
                                if(nonBuy == 1):
                                    gegesgseg = 1
                                else:
                                    gegesgseg = 0        
                            if(getrank == 2):
                                Buy = i[5]
                                if(Buy == 1):
                                    gegesgseg = 1
                                else:
                                    gegesgseg = 0        
                            if(getrank == 3):
                                vip = i[6]
                                if(vip == 1):
                                    gegesgseg = 1
                                else:
                                    gegesgseg = 0
                            if(getrank == 4):
                                vvip = i[7]
                                if(vvip == 1):
                                    gegesgseg = 1    
                                else:
                                    gegesgseg = 0    
                            if(getrank == 5):
                                resell = i[8] 
                                if(resell == 1):
                                    gegesgseg = 1 
                                else:
                                    gegesgseg = 0                                    
                            links.append([i[0],i[1],i[2],gegesgseg])                   
                        con.close()
                        if(user_info[8] == 0 and server_info[28] != 0):
                            return render_template("verify_code.html",ui=getuicolor,link=links, getrank=getranktesta,name=server_info[0] ,alllogs=getallbuylog,category=getcat, getname=getname,user_info=user_info, music=server_info[8], shopinfo=server_info, linking=server_info[14], url=name, file=info[16], channelio=server_info[21])
                        else:
                            return redirect("shop")
                else:
                    return redirect("login")
            else:
                abort(404)
        else:
             abort(404)                    
def getcategory(name):
    con = sqlite3.connect(db(name))
    cur = con.cursor()
    cur.execute("SELECT * FROM category")
    category1 = cur.fetchall()
    category = category1
    _category = []
    for i in category:
        cur.execute("SELECT * FROM products WHERE category01 == ?" , (i[0],))
        _product = cur.fetchall()
        l = len(_product)
        _category.append( [ i[0], i[1], l ] )
    con.close()   
    return _category

def productLists(name,category,id):
    con = sqlite3.connect(db(name))
    cur = con.cursor()
    cur.execute("SELECT * FROM products WHERE category01 == ?", (category,))
    _product = cur.fetchall()
    product = []
    getranktesta = getranktest(name,id)
    if (getranktesta == "관리자" or getranktesta == "부관리자"):
        for i in _product:
            cur.execute("SELECT * FROM price WHERE product_id == ? and rank == ? and prod1 == ?", (i[0],"구매자", "1day"))
            dayprice = cur.fetchall()
            i1 = dayprice
            cur.execute("SELECT * FROM price WHERE product_id == ? and rank == ? and prod1 == ?", (i[0],"구매자", "7day"))
            weekprice = cur.fetchall()
            i2 = weekprice
            cur.execute("SELECT * FROM price WHERE product_id == ? and rank == ? and prod1 == ?", (i[0],"구매자", "30day"))
            monthprice = cur.fetchall()
            i3 = monthprice
            cur.execute("SELECT * FROM products WHERE id == ?", (i[0],))
            test = cur.fetchone()
            test2 = (test[2])
            get1daylabel = (test[8])
            get7daylabel = (test[9])
            get30daylabel = (test[10])
            if(test[4] != "" ):
                len1 = len(test[4].split("\n"))
            else:
                len1 = "0"
            if(test[6] != "" ):
                len7 = len(test[6].split("\n"))
            else:
                len7 = "0" 
            if(test[7] != "" ):
                len30 = len(test[7].split("\n"))
            else:
                len30 = "0"           
            if i[5] == "0":
                l = "미분류"
            else:
                category = get_category(name , i[5])[0][1]
                l = category 
            if(len1 ==  "0"):  
                ProdResult1 = "재고없음"
            else:
                ProdResult1 = "구매하기"    
            if(len7 == "0"):  
                ProdResult2 = "재고없음"
            else:
                ProdResult2 = "구매하기"      
            if(len30 == "0"):
                ProdResult3 = "재고없음"       
            else:
                ProdResult3 = "구매하기"   
            product.append([i[0],i[1], test2, i[4], i[5], i1[0][2],len1,l, i[3], i2[0][2], i3[0][2], get1daylabel, get7daylabel, get30daylabel,len7,len30, i[12], ProdResult1, ProdResult2, ProdResult3])
                    #0,1,2,3,4,5,6,7,8,9
    elif (getranktesta == "미인증"):
        for i in _product:
            cur.execute("SELECT * FROM price WHERE product_id == ? and rank == ? and prod1 == ?", (i[0],"비구매자", "1day"))
            dayprice = cur.fetchall()
            i1 = dayprice
            cur.execute("SELECT * FROM price WHERE product_id == ? and rank == ? and prod1 == ?", (i[0],"비구매자", "7day"))
            weekprice = cur.fetchall()
            i2 = weekprice
            cur.execute("SELECT * FROM price WHERE product_id == ? and rank == ? and prod1 == ?", (i[0],"비구매자", "30day"))
            monthprice = cur.fetchall()
            i3 = monthprice
            cur.execute("SELECT * FROM products WHERE id == ?", (i[0],))
            test = cur.fetchone()
            test2 = (test[2])
            get1daylabel = (test[8])
            get7daylabel = (test[9])
            get30daylabel = (test[10])
            if(test[4] != "" ):
                len1 = len(test[4].split("\n"))
            else:
                len1 = "0"
            if(test[6] != "" ):
                len7 = len(test[6].split("\n"))
            else:
                len7 = "0" 
            if(test[7] != "" ):
                len30 = len(test[7].split("\n"))
            else:
                len30 = "0"           
            if i[5] == "0":
                l = "미분류"
            else:
                category = get_category(name , i[5])[0][1]
                l = category 
            if(len1 ==  "0"):  
                ProdResult1 = "재고없음"
            else:
                ProdResult1 = "구매하기"    
            if(len7 == "0"):  
                ProdResult2 = "재고없음"
            else:
                ProdResult2 = "구매하기"      
            if(len30 == "0"):
                ProdResult3 = "재고없음"       
            else:
                ProdResult3 = "구매하기"   
            product.append([i[0],i[1], test2, i[4], i[5], i1[0][2],len1,l, i[3], i2[0][2], i3[0][2], get1daylabel, get7daylabel, get30daylabel,len7,len30, i[12], ProdResult1, ProdResult2, ProdResult3])
                    #0,1,2,3,4,5,6,7,8,9
    else:    
        for i in _product:
            cur.execute("SELECT * FROM price WHERE product_id == ? and rank == ? and prod1 == ?", (i[0],getranktesta, "1day"))
            dayprice = cur.fetchall()
            i1 = dayprice
            cur.execute("SELECT * FROM price WHERE product_id == ? and rank == ? and prod1 == ?", (i[0],getranktesta, "7day"))
            weekprice = cur.fetchall()
            i2 = weekprice
            cur.execute("SELECT * FROM price WHERE product_id == ? and rank == ? and prod1 == ?", (i[0],getranktesta, "30day"))
            monthprice = cur.fetchall()
            i3 = monthprice
            cur.execute("SELECT * FROM products WHERE id == ?", (i[0],))
            test = cur.fetchone()
            test2 = (test[2])
            get1daylabel = (test[8])
            get7daylabel = (test[9])
            get30daylabel = (test[10])
            if(test[4] != "" ):
                len1 = len(test[4].split("\n"))
            else:
                len1 = "0"
            if(test[6] != "" ):
                len7 = len(test[6].split("\n"))
            else:
                len7 = "0" 
            if(test[7] != "" ):
                len30 = len(test[7].split("\n"))
            else:
                len30 = "0"           
            if i[5] == "0":
                l = "미분류"
            else:
                category = get_category(name , i[5])[0][1]
                l = category 
            if(len1 ==  "0"):  
                ProdResult1 = "재고없음"
            else:
                ProdResult1 = "구매하기"    
            if(len7 == "0"):  
                ProdResult2 = "재고없음"
            else:
                ProdResult2 = "구매하기"      
            if(len30 == "0"):
                ProdResult3 = "재고없음"       
            else:
                ProdResult3 = "구매하기"   
            product.append([i[0],i[1], test2, i[4], i[5], i1[0][2],len1,l, i[3], i2[0][2], i3[0][2], get1daylabel, get7daylabel, get30daylabel,len7,len30, i[12], ProdResult1, ProdResult2, ProdResult3])
                    #0,1,2,3,4,5,6,7,8,9
    return product

@app.route("/shop/<id>",subdomain='<name>', methods=["GET"])
def shop2(name , id):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (name.isalpha()):
            if (os.path.isfile(db(name))):
                if (name in session):
                 server_info = get_info(name)
                 if (str(server_info[6]) != ""):
                    return render_template("403.html", reason=server_info[6])
                 elif (is_expired(server_info[7])):
                    return render_template("403.html", reason="라이센스 연장이 필요합니다.")
                 else:
                    user_info = search_user(name, session[name])
                    getranktesta = getranktest(name,user_info[8])
                    getLists =  productLists(name, id,user_info[8])
                    getcat = getcategory(name)
                    getname = name
                    getuicolor = getui(name)
                    con = sqlite3.connect(db(name))
                    cur = con.cursor()
                    cur.execute("SELECT count(*) FROM visitorstoday")
                    getvisitorstoday = cur.fetchone()
                    visitorstoday = getvisitorstoday[0]
                    cur.execute("SELECT count(*) FROM visitorsweek")
                    getvisitorsweek = cur.fetchone()
                    visitorsweek = getvisitorsweek[0]
                    cur.execute("SELECT count(*) FROM visitorsmonth")
                    getvisitorsmonth = cur.fetchone()
                    visitorsmonth = getvisitorsmonth[0]
                    cur.execute("SELECT * FROM hyperlink")
                    link = cur.fetchall()
                    cur.execute("SELECT * FROM buylogtest")
                    getallbuylog = cur.fetchall()
                    links = []
                    for i in link:
                        getrank = user_info[8]
                        if(getrank == 6 or getrank == 7):
                            gegesgseg = 1
                        if(getrank == 0):
                            noauth = i[3]
                            if(noauth == 1):
                                gegesgseg = 1
                            else:
                                gegesgseg = 0        
                        if(getrank == 1):
                            nonBuy = i[4]
                            if(nonBuy == 1):
                                gegesgseg = 1
                            else:
                                gegesgseg = 0        
                        if(getrank == 2):
                            Buy = i[5]
                            if(Buy == 1):
                                gegesgseg = 1
                            else:
                                gegesgseg = 0        
                        if(getrank == 3):
                            vip = i[6]
                            if(vip == 1):
                                gegesgseg = 1
                            else:
                                gegesgseg = 0
                        if(getrank == 4):
                            vvip = i[7]
                            if(vvip == 1):
                                gegesgseg = 1    
                            else:
                                gegesgseg = 0    
                        if(getrank == 5):
                            resell = i[8] 
                            if(resell == 1):
                                gegesgseg = 1 
                            else:
                                gegesgseg = 0                                    
                        links.append([i[0],i[1],i[2],gegesgseg])                   
                    con.close()
                    return render_template("index.html", visitorstoday=visitorstoday,visitorsweek=visitorsweek,visitorsmonth=visitorsmonth,ui=getuicolor,getrank=getranktesta,name=server_info[0], link=links, alllogs=getallbuylog, products=getLists,category=getcat,getname=getname,user_info=user_info, music=server_info[8], shopinfo=server_info, url=name)
                else:
                    return redirect("login")
            else:
                abort(404)
        else:
             abort(404)                                 
@app.route("/shop", subdomain='<name>',methods=["GET"])
def shop(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (name.isalpha()):
            if (os.path.isfile(db(name))):
                if (name in session):
                    server_info = get_info(name)
                    if (str(server_info[6]) != ""):
                        return render_template("403.html", reason=server_info[6])
                    elif (is_expired(server_info[7])):
                        return render_template("403.html", reason="라이센스 연장이 필요합니다.")
                    else:
                        user_info = search_user(name, session[name])
                        getuicolor = getui(name)
                        getcat = getcategory(name)
                        getname = name
                        con = sqlite3.connect(db(name))
                        cur = con.cursor()
                        cur.execute("SELECT count(*) FROM visitorstoday")
                        getvisitorstoday = cur.fetchone()
                        visitorstoday = getvisitorstoday[0]
                        cur.execute("SELECT count(*) FROM visitorsweek")
                        getvisitorsweek = cur.fetchone()
                        visitorsweek = getvisitorsweek[0]
                        cur.execute("SELECT count(*) FROM visitorsmonth")
                        getvisitorsmonth = cur.fetchone()
                        visitorsmonth = getvisitorsmonth[0]
                        cur.execute("SELECT * FROM hyperlink")
                        link = cur.fetchall()
                        links = []
                        cur.execute("SELECT * FROM products")
                        _product = cur.fetchall()
                        product = []
                        getranktesta = getranktest(name,user_info[8])
                        cur.execute("SELECT * FROM buylogtest")
                        getallbuylog = cur.fetchall()
                        for i in link:
                            getrank = user_info[8]
                            if(getrank == 6 or getrank == 7):
                                gegesgseg = 1
                            if(getrank == 0):
                                noauth = i[3]
                                if(noauth == 1):
                                    gegesgseg = 1
                                else:
                                    gegesgseg = 0        
                            if(getrank == 1):
                                nonBuy = i[4]
                                if(nonBuy == 1):
                                    gegesgseg = 1
                                else:
                                    gegesgseg = 0        
                            if(getrank == 2):
                                Buy = i[5]
                                if(Buy == 1):
                                    gegesgseg = 1
                                else:
                                    gegesgseg = 0        
                            if(getrank == 3):
                                vip = i[6]
                                if(vip == 1):
                                    gegesgseg = 1
                                else:
                                    gegesgseg = 0
                            if(getrank == 4):
                                vvip = i[7]
                                if(vvip == 1):
                                    gegesgseg = 1    
                                else:
                                    gegesgseg = 0    
                            if(getrank == 5):
                                resell = i[8] 
                                if(resell == 1):
                                    gegesgseg = 1 
                                else:
                                    gegesgseg = 0                                    
                            links.append([i[0],i[1],i[2],gegesgseg])         
                        if (getranktesta == "관리자" or getranktesta == "부관리자"):
                            for i in _product:
                                cur.execute("SELECT * FROM price WHERE product_id == ? and rank == ? and prod1 == ?", (i[0],"구매자", "1day"))
                                dayprice = cur.fetchall()
                                i1 = dayprice
                                cur.execute("SELECT * FROM price WHERE product_id == ? and rank == ? and prod1 == ?", (i[0],"구매자", "7day"))
                                weekprice = cur.fetchall()
                                i2 = weekprice
                                cur.execute("SELECT * FROM price WHERE product_id == ? and rank == ? and prod1 == ?", (i[0],"구매자", "30day"))
                                monthprice = cur.fetchall()
                                i3 = monthprice
                                cur.execute("SELECT * FROM products WHERE id == ?", (i[0],))
                                test = cur.fetchone()
                                test2 = (test[2])
                                get1daylabel = (test[8])
                                get7daylabel = (test[9])
                                get30daylabel = (test[10])
                                if(test[4] != "" ):
                                    len1 = len(test[4].split("\n"))
                                else:
                                    len1 = "0"
                                if(test[6] != "" ):
                                    len7 = len(test[6].split("\n"))
                                else:
                                    len7 = "0" 
                                if(test[7] != "" ):
                                    len30 = len(test[7].split("\n"))
                                else:
                                    len30 = "0"
                                if(len1 ==  "0"):  
                                    ProdResult1 = "재고없음"
                                else:
                                    ProdResult1 = "구매하기"    
                                if(len7 == "0"):  
                                    ProdResult2 = "재고없음"
                                else:
                                    ProdResult2 = "구매하기"      
                                if(len30 == "0"):
                                    ProdResult3 = "재고없음"       
                                else:
                                    ProdResult3 = "구매하기" 
                                l = "Null"        
                                product.append([i[0],i[1], test2, i[4], i[5], i1[0][2],len1,l, i[3], i2[0][2], i3[0][2], get1daylabel, get7daylabel, get30daylabel,len7,len30, i[12], ProdResult1, ProdResult2, ProdResult3])
                                #0,1,2,3,4,5,6,7,8,9
                        elif (getranktesta == "미인증"):
                            for i in _product:
                                cur.execute("SELECT * FROM price WHERE product_id == ? and rank == ? and prod1 == ?", (i[0],"비구매자", "1day"))
                                dayprice = cur.fetchall()
                                i1 = dayprice
                                cur.execute("SELECT * FROM price WHERE product_id == ? and rank == ? and prod1 == ?", (i[0],"비구매자", "7day"))
                                weekprice = cur.fetchall()
                                i2 = weekprice
                                cur.execute("SELECT * FROM price WHERE product_id == ? and rank == ? and prod1 == ?", (i[0],"비구매자", "30day"))
                                monthprice = cur.fetchall()
                                i3 = monthprice
                                cur.execute("SELECT * FROM products WHERE id == ?", (i[0],))
                                test = cur.fetchone()
                                test2 = (test[2])
                                get1daylabel = (test[8])
                                get7daylabel = (test[9])
                                get30daylabel = (test[10])
                                if(test[4] != "" ):
                                    len1 = len(test[4].split("\n"))
                                else:
                                    len1 = "0"
                                if(test[6] != "" ):
                                    len7 = len(test[6].split("\n"))
                                else:
                                    len7 = "0" 
                                if(test[7] != "" ):
                                    len30 = len(test[7].split("\n"))
                                else:
                                    len30 = "0"           
                                if(len1 ==  "0"):  
                                    ProdResult1 = "재고없음"
                                else:
                                    ProdResult1 = "구매하기"    
                                if(len7 == "0"):  
                                    ProdResult2 = "재고없음"
                                else:
                                    ProdResult2 = "구매하기"      
                                if(len30 == "0"):
                                    ProdResult3 = "재고없음"       
                                else:
                                    ProdResult3 = "구매하기"   
                                l = "Null"      
                                product.append([i[0],i[1], test2, i[4], i[5], i1[0][2],len1,l, i[3], i2[0][2], i3[0][2], get1daylabel, get7daylabel, get30daylabel,len7,len30, i[12], ProdResult1, ProdResult2, ProdResult3])
                                #0,1,2,3,4,5,6,7,8,9        
                        else:    
                            for i in _product:
                                cur.execute("SELECT * FROM price WHERE product_id == ? and rank == ? and prod1 == ?", (i[0],getranktesta, "1day"))
                                dayprice = cur.fetchall()
                                i1 = dayprice
                                cur.execute("SELECT * FROM price WHERE product_id == ? and rank == ? and prod1 == ?", (i[0],getranktesta, "7day"))
                                weekprice = cur.fetchall()
                                i2 = weekprice
                                cur.execute("SELECT * FROM price WHERE product_id == ? and rank == ? and prod1 == ?", (i[0],getranktesta, "30day"))
                                monthprice = cur.fetchall()
                                i3 = monthprice
                                cur.execute("SELECT * FROM products WHERE id == ?", (i[0],))
                                test = cur.fetchone()
                                test2 = (test[2])
                                get1daylabel = (test[8])
                                get7daylabel = (test[9])
                                get30daylabel = (test[10])
                                if(test[4] != "" ):
                                    len1 = len(test[4].split("\n"))
                                else:
                                    len1 = "0"
                                if(test[6] != "" ):
                                    len7 = len(test[6].split("\n"))
                                else:
                                    len7 = "0" 
                                if(test[7] != "" ):
                                    len30 = len(test[7].split("\n"))
                                else:
                                    len30 = "0"           
                                if(len1 ==  "0"):  
                                    ProdResult1 = "재고없음"
                                else:
                                    ProdResult1 = "구매하기"    
                                if(len7 == "0"):  
                                    ProdResult2 = "재고없음"
                                else:
                                    ProdResult2 = "구매하기"      
                                if(len30 == "0"):
                                    ProdResult3 = "재고없음"       
                                else:
                                    ProdResult3 = "구매하기"   
                                l = "Null"    
                                product.append([i[0],i[1], test2, i[4], i[5], i1[0][2],len1,l, i[3], i2[0][2], i3[0][2], get1daylabel, get7daylabel, get30daylabel,len7,len30, i[12], ProdResult1, ProdResult2, ProdResult3])
                                #0,1,2,3,4,5,6,7,8,9
                        con.close()
                        return render_template("index.html",visitorstoday=visitorstoday,visitorsweek=visitorsweek,visitorsmonth=visitorsmonth,ui=getuicolor, name=server_info[0],getrank=getranktesta,link=links,alllogs=getallbuylog, products=product,category=getcat,getname=getname,user_info=user_info, music=server_info[8], shopinfo=server_info, url=name)
                else:
                    return redirect("login")
            else:
                abort(404)
        else:
             abort(404)      
@app.route("/introduce/<id>", subdomain='<name>', methods=["GET"])
def introduce(name , id):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (name.isalpha()):
            if (os.path.isfile(db(name))):
                if (name in session):
                 info = get_info(name)
                 if (str(info[6]) != ""):
                    return render_template("403.html", reason=info[6])
                 elif (is_expired(info[7])):
                    return render_template("403.html", reason="라이센스 연장이 필요합니다.")
                 else:
                    server_info = get_info(name)
                    user_info = search_user(name, session[name])
                    getLists =  search_prodintroduce(name, id)
                    getname = name
                    getuicolor = getui(name)
                    getranktesta = getranktest(name,user_info[8])
                    con = sqlite3.connect(db(name))
                    cur = con.cursor()
                    cur.execute("SELECT count(*) FROM visitorstoday")
                    getvisitorstoday = cur.fetchone()
                    visitorstoday = getvisitorstoday[0]
                    cur.execute("SELECT count(*) FROM visitorsweek")
                    getvisitorsweek = cur.fetchone()
                    visitorsweek = getvisitorsweek[0]
                    cur.execute("SELECT count(*) FROM visitorsmonth")
                    getvisitorsmonth = cur.fetchone()
                    visitorsmonth = getvisitorsmonth[0]
                    cur.execute("SELECT * FROM hyperlink")
                    link = cur.fetchall()
                    cur.execute("SELECT * FROM buylogtest")
                    getallbuylog = cur.fetchall()
                    links = []
                    for i in link:
                        getrank = user_info[8]
                        if(getrank == 6 or getrank == 7):
                            gegesgseg = 1
                        if(getrank == 0):
                            noauth = i[3]
                            if(noauth == 1):
                                gegesgseg = 1
                            else:
                                gegesgseg = 0        
                        if(getrank == 1):
                            nonBuy = i[4]
                            if(nonBuy == 1):
                                gegesgseg = 1
                            else:
                                gegesgseg = 0        
                        if(getrank == 2):
                            Buy = i[5]
                            if(Buy == 1):
                                gegesgseg = 1
                            else:
                                gegesgseg = 0        
                        if(getrank == 3):
                            vip = i[6]
                            if(vip == 1):
                                gegesgseg = 1
                            else:
                                gegesgseg = 0
                        if(getrank == 4):
                            vvip = i[7]
                            if(vvip == 1):
                                gegesgseg = 1    
                            else:
                                gegesgseg = 0    
                        if(getrank == 5):
                            resell = i[8] 
                            if(resell == 1):
                                gegesgseg = 1 
                            else:
                                gegesgseg = 0                                    
                        links.append([i[0],i[1],i[2],gegesgseg])                   
                    con.close()
                    return render_template("introduce.html", visitorstoday=visitorstoday,visitorsweek=visitorsweek,visitorsmonth=visitorsmonth,ui=getuicolor, getrank=getranktesta,link=links, name=server_info[0] ,alllogs=getallbuylog, products=getLists,getname=getname,user_info=user_info, music=server_info[8], shopinfo=server_info, linking=server_info[14], url=name, file=info[16], channelio=server_info[21])
                else:
                    return redirect("login")
            else:
                abort(404)
        else:
             abort(404)
     
@app.route("/history/purchase", defaults={"page": 1}, subdomain='<name>',methods=["GET"])                                                                                                  
@app.route("/history/purchase/<int:page>", subdomain='<name>',methods=["GET"])
def log(name,page):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (name.isalpha()):
            if (os.path.isfile(db(name))):
                if (name in session):
                    server_info = get_info(name)
                    if (is_expired(server_info[7])):
                        return render_template("403.html", reason="라이센스 연장이 필요합니다.")
                    con = sqlite3.connect(db(name))
                    cur = con.cursor()
                    cur.execute("SELECT id, nowbuytime, product,maxprice,count(*), group_concat(buycode,'\n') FROM buylogtest WHERE id = ? GROUP BY nowbuytime HAVING count(*) > 1 ORDER BY nowbuytime DESC LIMIT 5;",(session[name],)) # 5개 제한
                    getdown = cur.fetchall()
                    row = [item[1] for item in getdown]
                    listlen = len(row)
                    cur.execute("SELECT count(*) FROM buylogtest WHERE id == ?;",(session[name],))
                    resultbuylog = cur.fetchone()
                    total = resultbuylog[0]
                    page, per_page, offset = get_page_args(per_page_parameter="pp", pp=10)
                    if per_page:
                        sql = "select * from buylogtest where id==? ORDER BY nowbuytime DESC limit {}, {}".format(
                            offset, per_page
                        )
                        args = (session[name].format(id),)
                    cur.execute(sql, args)
                    getbuylog = cur.fetchall()
                    max_possible_page = (total // per_page)+1
                    if(page == 1 and page == max_possible_page):
                        Previous = 0
                        Nextpage = 0
                        Nextlink = page + 1
                        Previouslink = page - 1
                    elif(page == 1 and page != max_possible_page):
                        Previous = 0
                        Nextpage = 1
                        Nextlink = page + 1
                        Previouslink = page - 1    
                    elif(page == max_possible_page):
                        Previous = 1
                        Nextpage = 0
                        Nextlink = page + 1
                        Previouslink = page - 1
                    else:
                        Previous = 1
                        Nextpage = 1
                        Nextlink = page + 1
                        Previouslink = page - 1
                    if page > max_possible_page:
                        abort(404)
                    con.close()                      
                    info = search_user(name, session[name])
                    getranktesta = getranktest(name,info[8])                   
                    getcat = getcategory(name)
                    getuicolor = getui(name)
                    getname = name
                    con = sqlite3.connect(db(name))
                    cur = con.cursor()
                    cur.execute("SELECT count(*) FROM visitorstoday")
                    getvisitorstoday = cur.fetchone()
                    visitorstoday = getvisitorstoday[0]
                    cur.execute("SELECT count(*) FROM visitorsweek")
                    getvisitorsweek = cur.fetchone()
                    visitorsweek = getvisitorsweek[0]
                    cur.execute("SELECT count(*) FROM visitorsmonth")
                    getvisitorsmonth = cur.fetchone()
                    visitorsmonth = getvisitorsmonth[0]
                    cur.execute("SELECT * FROM hyperlink")
                    link = cur.fetchall()
                    cur.execute("SELECT * FROM buylogtest")
                    getallbuylog = cur.fetchall()
                    links = []
                    for i in link:
                        getrank = info[8]
                        if(getrank == 6 or getrank == 7):
                            gegesgseg = 1
                        if(getrank == 0):
                            noauth = i[3]
                            if(noauth == 1):
                                gegesgseg = 1
                            else:
                                gegesgseg = 0        
                        if(getrank == 1):
                            nonBuy = i[4]
                            if(nonBuy == 1):
                                gegesgseg = 1
                            else:
                                gegesgseg = 0        
                        if(getrank == 2):
                            Buy = i[5]
                            if(Buy == 1):
                                gegesgseg = 1
                            else:
                                gegesgseg = 0        
                        if(getrank == 3):
                            vip = i[6]
                            if(vip == 1):
                                gegesgseg = 1
                            else:
                                gegesgseg = 0
                        if(getrank == 4):
                            vvip = i[7]
                            if(vvip == 1):
                                gegesgseg = 1    
                            else:
                                gegesgseg = 0    
                        if(getrank == 5):
                            resell = i[8] 
                            if(resell == 1):
                                gegesgseg = 1 
                            else:
                                gegesgseg = 0                                    
                        links.append([i[0],i[1],i[2],gegesgseg])                   
                    con.close()
                    return render_template("purchase.html",visitorstoday=visitorstoday,visitorsweek=visitorsweek,visitorsmonth=visitorsmonth,ui=getuicolor, getdown=getdown,resultgetcount=listlen,Nextlink=Nextlink,Previouslink=Previouslink,Previous=Previous,Nextpage=Nextpage,infos=server_info[4], getrank=getranktesta,link=links,category=getcat, getname=getname,user_info=info, name=server_info[0], logs=getbuylog, alllogs=getallbuylog, music=server_info[8], shopinfo=server_info, linking=server_info[14], type=1, url=name, file=server_info[16], channelio=server_info[21])
                else:
                    return redirect("../login")
            else:
                abort(404)
        else:
            abort(404)
            
    
@app.route("/notice", subdomain='<name>',methods=["GET"])
def announcement(name):
    if (name.isalpha()):
        if (os.path.isfile(db(name))):
            if (name in session):
                server_info = get_info(name)
                if (is_expired(server_info[7])):
                    return render_template("403.html", reason="라이센스 연장이 필요합니다.")
                userinfo = search_user(name, session[name])
                getuicolor = getui(name)
                getranktesta = getranktest(name,userinfo[8])
                getcat = getcategory(name)
                getname = name
                con = sqlite3.connect(db(name))
                cur = con.cursor()
                cur.execute("SELECT count(*) FROM visitorstoday")
                getvisitorstoday = cur.fetchone()
                visitorstoday = getvisitorstoday[0]
                cur.execute("SELECT count(*) FROM visitorsweek")
                getvisitorsweek = cur.fetchone()
                visitorsweek = getvisitorsweek[0]
                cur.execute("SELECT count(*) FROM visitorsmonth")
                getvisitorsmonth = cur.fetchone()
                visitorsmonth = getvisitorsmonth[0]
                cur.execute("SELECT * FROM introduce")
                _product = cur.fetchall()
                cur.execute("SELECT * FROM buylogtest")
                getallbuylog = cur.fetchall()
                product = []
                for i in _product:
                    cur.execute("SELECT * FROM introduce WHERE id == ?", (0,))
                    test = cur.fetchone()
                    text = test[2]            
                    product.append([i[0],i[1],text])
                cur.execute("SELECT * FROM popups")
                _pop = cur.fetchall()
                pop = []
                for i in _pop:           
                    pop.append([i[0],i[1],i[2]])
                cur.execute("SELECT * FROM hyperlink")
                link = cur.fetchall()
                links = []
                for i in link:
                    getrank = userinfo[8]
                    if(getrank == 6 or getrank == 7):
                        gegesgseg = 1
                    if(getrank == 0):
                        noauth = i[3]
                        if(noauth == 1):
                            gegesgseg = 1
                        else:
                            gegesgseg = 0        
                    if(getrank == 1):
                        nonBuy = i[4]
                        if(nonBuy == 1):
                            gegesgseg = 1
                        else:
                            gegesgseg = 0        
                    if(getrank == 2):
                        Buy = i[5]
                        if(Buy == 1):
                            gegesgseg = 1
                        else:
                            gegesgseg = 0        
                    if(getrank == 3):
                        vip = i[6]
                        if(vip == 1):
                            gegesgseg = 1
                        else:
                            gegesgseg = 0
                    if(getrank == 4):
                        vvip = i[7]
                        if(vvip == 1):
                            gegesgseg = 1    
                        else:
                            gegesgseg = 0    
                    if(getrank == 5):
                        resell = i[8] 
                        if(resell == 1):
                            gegesgseg = 1 
                        else:
                            gegesgseg = 0                                    
                    links.append([i[0],i[1],i[2],gegesgseg])                   
                con.close()
                return render_template("announcement.html", visitorstoday=visitorstoday,visitorsweek=visitorsweek,visitorsmonth=visitorsmonth, products=product,ui=getuicolor,popup=pop,link=links,infos=server_info[4], getrank=getranktesta, user_info=userinfo,alllogs=getallbuylog,name=server_info[0], music=server_info[8], category = getcat,getname=getname, shopinfo=server_info, url=name)
            else:
                return redirect("login")
        else:
            abort(404)
    else:
        abort(404)
        
@app.route("/history/charge", subdomain='<name>',methods=["GET"])
def charge(name):
    if (name.isalpha()):
        if (os.path.isfile(db(name))):
            if (name in session):
                server_info = get_info(name)
                if (is_expired(server_info[7])):
                    return render_template("403.html", reason="라이센스 연장이 필요합니다.")    
                info = search_user(name, session[name])
                getranktesta = getranktest(name,info[8])
                getcat = getcategory(name)
                getname = name
                getuicolor = getui(name)
                buylog_list = ast.literal_eval(info[12])
                con = sqlite3.connect(db(name))
                cur = con.cursor()
                cur.execute("SELECT count(*) FROM visitorstoday")
                getvisitorstoday = cur.fetchone()
                visitorstoday = getvisitorstoday[0]
                cur.execute("SELECT count(*) FROM visitorsweek")
                getvisitorsweek = cur.fetchone()
                visitorsweek = getvisitorsweek[0]
                cur.execute("SELECT count(*) FROM visitorsmonth")
                getvisitorsmonth = cur.fetchone()
                visitorsmonth = getvisitorsmonth[0]
                cur.execute("SELECT * FROM hyperlink")
                link = cur.fetchall()
                cur.execute("SELECT * FROM buylogtest")
                getallbuylog = cur.fetchall()
                links = []
                for i in link:
                    getrank = info[8]
                    if(getrank == 6 or getrank == 7):
                        gegesgseg = 1
                    if(getrank == 0):
                        noauth = i[3]
                        if(noauth == 1):
                            gegesgseg = 1
                        else:
                            gegesgseg = 0        
                    if(getrank == 1):
                        nonBuy = i[4]
                        if(nonBuy == 1):
                            gegesgseg = 1
                        else:
                            gegesgseg = 0        
                    if(getrank == 2):
                        Buy = i[5]
                        if(Buy == 1):
                            gegesgseg = 1
                        else:
                            gegesgseg = 0        
                    if(getrank == 3):
                        vip = i[6]
                        if(vip == 1):
                            gegesgseg = 1
                        else:
                            gegesgseg = 0
                    if(getrank == 4):
                        vvip = i[7]
                        if(vvip == 1):
                            gegesgseg = 1    
                        else:
                            gegesgseg = 0    
                    if(getrank == 5):
                        resell = i[8] 
                        if(resell == 1):
                            gegesgseg = 1 
                        else:
                            gegesgseg = 0                                    
                    links.append([i[0],i[1],i[2],gegesgseg])                   
                con.close()
                return render_template("charge.html", visitorstoday=visitorstoday,visitorsweek=visitorsweek,visitorsmonth=visitorsmonth,ui=getuicolor,infos=server_info[4], getrank=getranktesta,link=links,user_info=info, name=server_info[0], alllogs=getallbuylog,logs=reversed(sorted(buylog_list)),music=server_info[8], category = getcat,getname=getname,announcement=server_info[9], shopinfo=server_info, linking=server_info[14], url=name, file=server_info[16], imgannouncement=server_info[17], channelio=server_info[21])
            else:
                return redirect("login")
        else:
            abort(404)
    else:
        abort(404)
        
def getStock(name, id: int, amount: int):
    stocks = getAllStock(name,id)
    idid = str(uuid.uuid4())
    for i in range(amount):
        print(str(stocks[i][2]))
        addraw(name,idid,str(stocks[i][2]))
        removeStock(name,id,stocks[i][2])
     
    #database.insert("codelog", sites=site.id, code=f"https:/   /raw.fikitnetworx.com/{idid}", name=f"{name} [{l}] [{amount}개]", id=user.id)
    #database.insert("buylog", sites=site.id, name=f"{name} [{amount}개]", id=user.id)
    #return f"https://raw.fikitnetworx.com/{idid}"
@app.route("/buy",subdomain='<name>', methods=["POST"])
def buy(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (name.isalpha()):
            if (os.path.isfile(db(name))):
                if (name in session):
                    if ("id" in request.get_json() and "amount" in request.get_json() and "type" in request.get_json()):
                        prod_info = get_prod(name, request.get_json()["id"])
                        user_info = search_user(name, session[name])
                        getranktesta = getranktest(name,user_info[8])
                        get_pr = get_price(name,request.get_json()["id"],getranktesta,request.get_json()["type"])
                        if (prod_info != None):
                            if(request.get_json()["type"] == "1day"):
                                if (prod_info[4] != "" and str(request.get_json()["amount"]).isdigit() and request.get_json()["amount"] >= 0 and len(prod_info[4].split("\n")) >= request.get_json()["amount"]):
                                    server_info = get_info(name)
                                    total_price = int(get_pr[2]) * int(request.get_json()["amount"])
                                    if (int(user_info[3]) >= total_price): #제품 레이블 1
                                        con = sqlite3.connect(db(name))
                                        with con:
                                            now_stock = prod_info[4].split("\n")
                                            bought_stock = []
                                            for n in range(0,request.get_json()["amount"]):
                                                choiced_stock = now_stock[0]
                                                bought_stock.append(choiced_stock)
                                                now_stock.remove(choiced_stock)
                                                con2 = sqlite3.connect(db(name))
                                                cur2 = con2.cursor()
                                                cur2.execute("INSERT INTO buylogtest VALUES(?, ?, ?, ?, ? ,?);", (session[name], str(nowstr()),"[" + prod_info[1] + "]" + " " + prod_info[8],int(get_pr[2]),total_price,choiced_stock.strip('\r')))
                                                con2.commit()
                                                con2.close()
                                            bought_stock2 = "\n".join(bought_stock)
                                            now_money = int(user_info[3]) - int(total_price)
                                            convertresultmoney = number_format(int(now_money),"ko_KR")
                                            convertmoney = number_format(int(user_info[3]),"ko_KR")
                                            now_buylog = ast.literal_eval(user_info[4])
                                            now_buylog.append([nowstr(), "[ " + prod_info[1] + " ]" + " " + prod_info[8],bought_stock2])
                                            rankupvvipmoney = int(server_info[18])
                                            rankupvipmoney= int(server_info[17])
                                            now_bought = int(user_info[9]) + (total_price)
                                            cur = con.cursor()
                                            if (getranktesta == "비구매자" or getranktesta == "미인증"):
                                                cur.execute("UPDATE users SET money = ?, buylog = ?, rankdata1 = ?, bought = ? WHERE id == ?", (now_money, str(now_buylog), 2, now_bought, session[name]))
                                                con.commit()
                                                cur.execute("UPDATE products SET stock = ? WHERE id == ?", ("\n".join(now_stock), request.get_json()["id"]))
                                                con.commit()
                                                buylog = ast.literal_eval(server_info[4])
                                                buylog.append([nowstr(), session[name], "[ " + prod_info[1] + " ]" + " " + prod_info[8], bought_stock])
                                                cur.execute("UPDATE info SET buylog = ?", (str(buylog),))
                                                con.commit()
                                                if (user_info[14] == None):
                                                    cur.execute("UPDATE users SET token = ? WHERE id == ?", (secrets.token_hex(nbytes=5), session[name]))
                                                    con.commit()
                                                if (server_info[1] != None):
                                                    try:
                                                        webhook = DiscordWebhook(username="HOLYSHARRY.CO", avatar_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png", url=server_info[1])
                                                        embed = DiscordEmbed(title="**실시간 구매기록**", value="",color=0x191A2F)
                                                        embed.add_embed_field(name='구매한 제품명', value=f'{prod_info[1]}',inline=False)
                                                        embed.add_embed_field(name='제품 라벨', value=f'{prod_info[8]}',inline=False)
                                                        embed.set_footer(text='HOLYSHARRY.CO', icon_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png")
                                                        embed.set_timestamp()
                                                        webhook.add_embed(embed)
                                                        webhook.execute()
                                                    except:
                                                        print("Webhook Error")          
                                                if (server_info[14] != None):
                                                    try:
                                                        webhook = DiscordWebhook(username="HOLYSHARRY.CO", avatar_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png", url=server_info[14])
                                                        embed = DiscordEmbed(title="**실시간 구매기록**", value="",color=0x191A2F)
                                                        embed.add_embed_field(name='구매한 제품명', value=f'{prod_info[1]}',inline=False)
                                                        embed.add_embed_field(name='제품 라벨', value=f'{prod_info[8]}',inline=False)
                                                        embed.add_embed_field(name='아이디', value=f'{session[name]}',inline=False)
                                                        embed.add_embed_field(name='구매한 재고', value=f'{bought_stock}',inline=False)
                                                        embed.add_embed_field(name='구매 시간', value=f'{nowstr()}',inline=False)
                                                        embed.add_embed_field(name='아이피', value=f'{getip()}',inline=False)
                                                        embed.add_embed_field(name='현재 돈', value=f'{convertmoney}',inline=False)
                                                        embed.add_embed_field(name='구매 이후 남은 돈', value=f'{convertresultmoney}',inline=False)
                                                        embed.set_footer(text='HOLYSHARRY.CO', icon_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png")
                                                        embed.set_timestamp()
                                                        webhook.add_embed(embed)
                                                        webhook.execute()
                                                    except:
                                                        print("Webhook Error")  
                                            else:
                                                cur.execute("UPDATE users SET money = ?, bought = ? WHERE id == ?", (now_money, now_bought, session[name])) 
                                                con.commit()
                                                cur.execute("UPDATE products SET stock = ? WHERE id == ?", ("\n".join(now_stock), request.get_json()["id"]))
                                                con.commit()
                                                buylog = ast.literal_eval(server_info[4])
                                                buylog.append([nowstr(), session[name], "[ " + prod_info[1] + " ]" + " " + prod_info[8], bought_stock2])
                                                cur.execute("UPDATE info SET buylog = ?", (str(buylog),))
                                                con.commit()
                                                if (user_info[14] == None):
                                                    cur.execute("UPDATE users SET token = ? WHERE id == ?", (secrets.token_hex(nbytes=5), session[name]))
                                                    con.commit()
                                                if (server_info[1] != None):
                                                    try:
                                                        webhook = DiscordWebhook(username="HOLYSHARRY.CO", avatar_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png", url=server_info[1])
                                                        embed = DiscordEmbed(title="**실시간 구매기록**", value="",color=0x191A2F)
                                                        embed.add_embed_field(name='구매한 제품명', value=f'{prod_info[1]}',inline=False)
                                                        embed.add_embed_field(name='제품 라벨', value=f'{prod_info[8]}',inline=False)
                                                        embed.set_footer(text='HOLYSHARRY.CO', icon_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png")
                                                        embed.set_timestamp()
                                                        webhook.add_embed(embed)
                                                        webhook.execute()
                                                    except:
                                                        print("Webhook Error")    
                                                if (server_info[14] != None):
                                                    try:
                                                        webhook = DiscordWebhook(username="HOLYSHARRY.CO", avatar_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png", url=server_info[14])
                                                        embed = DiscordEmbed(title="**실시간 구매기록**", value="",color=0x191A2F)
                                                        embed.add_embed_field(name='구매한 제품명', value=f'{prod_info[1]}',inline=False)
                                                        embed.add_embed_field(name='제품 라벨', value=f'{prod_info[8]}',inline=False)
                                                        embed.add_embed_field(name='아이디', value=f'{session[name]}',inline=False)
                                                        embed.add_embed_field(name='구매한 재고', value=f'{bought_stock2}',inline=False)
                                                        embed.add_embed_field(name='구매 시간', value=f'{nowstr()}',inline=False)
                                                        embed.add_embed_field(name='아이피', value=f'{getip()}',inline=False)
                                                        embed.add_embed_field(name='현재 돈', value=f'{convertmoney}',inline=False)
                                                        embed.add_embed_field(name='구매 이후 남은 돈', value=f'{convertresultmoney}',inline=False)
                                                        embed.set_footer(text='HOLYSHARRY.CO', icon_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png")
                                                        embed.set_timestamp()
                                                        webhook.add_embed(embed)
                                                        webhook.execute()
                                                    except:
                                                        print("Webhook Error")      
                                                if (getranktesta == "구매자" and now_bought >= rankupvipmoney) :
                                                    cur.execute("UPDATE users SET rankdata1 = ? WHERE id == ?", (3, session[name]))
                                                    con.commit()
                                                if (getranktesta == "VIP" and now_bought >= rankupvvipmoney) :
                                                    cur.execute("UPDATE users SET rankdata1 = ? WHERE id == ?", (4, session[name]))
                                                    con.commit() 
                                        con.close()
                                        return "ok"
                                    else:
                                        return "잔액이 부족합니다."                      
                                else:
                                    return "재고가 부족합니다."
                            if(request.get_json()["type"] == "7day"):
                                if (prod_info[6] != "" and str(request.get_json()["amount"]).isdigit() and request.get_json()["amount"] >= 0 and len(prod_info[6].split("\n")) >= request.get_json()["amount"]):
                                    server_info = get_info(name)
                                    total_price = int(get_pr[2]) * int(request.get_json()["amount"])
                                    if (int(user_info[3]) >= total_price):  #제품 레이블 2
                                        con = sqlite3.connect(db(name)) 
                                        with con:
                                            now_stock = prod_info[6].split("\n")
                                            bought_stock = []
                                            for n in range(0,request.get_json()["amount"]):
                                                choiced_stock = now_stock[0]
                                                bought_stock.append(choiced_stock)
                                                now_stock.remove(choiced_stock)
                                                con2 = sqlite3.connect(db(name))
                                                cur2 = con2.cursor()
                                                cur2.execute("INSERT INTO buylogtest VALUES(?, ?, ?, ?, ? ,?);", (session[name], str(nowstr()),"[" + prod_info[1] + "]" + " " + prod_info[9],int(get_pr[2]),total_price,choiced_stock.strip('\r')))
                                                con2.commit()
                                                con2.close()
                                            bought_stock2 = "\n".join(bought_stock)
                                            now_money = int(user_info[3]) - int(total_price)
                                            convertresultmoney = number_format(int(now_money),"ko_KR")
                                            convertmoney = number_format(int(user_info[3]),"ko_KR")
                                            now_buylog = ast.literal_eval(user_info[4])
                                            now_buylog.append([nowstr(), "[ " + prod_info[1] + " ]" + " " + prod_info[9],bought_stock2])
                                            now_bought = int(user_info[9]) + (total_price)
                                            rankupvvipmoney = int(server_info[18])
                                            rankupvipmoney= int(server_info[17])
                                            cur = con.cursor()
                                            if (getranktesta == "비구매자" or getranktesta == "미인증"):
                                                cur.execute("UPDATE users SET money = ?, buylog = ?, rankdata1 = ?, bought = ? WHERE id == ?", (now_money, str(now_buylog), 2, now_bought, session[name]))
                                                con.commit()
                                                cur.execute("UPDATE products SET stock2 = ? WHERE id == ?", ("\n".join(now_stock), request.get_json()["id"]))
                                                con.commit()
                                                buylog = ast.literal_eval(server_info[4])
                                                buylog.append([nowstr(), session[name], "[ " + prod_info[1] + " ]" + " " + prod_info[9], bought_stock2])
                                                cur.execute("UPDATE info SET buylog = ?", (str(buylog),))
                                                con.commit()
                                                if (user_info[14] == None):
                                                    cur.execute("UPDATE users SET token = ? WHERE id == ?", (secrets.token_hex(nbytes=5), session[name]))
                                                    con.commit()
                                                if (server_info[1] != None):
                                                    try:
                                                        webhook = DiscordWebhook(username="HOLYSHARRY.CO", avatar_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png", url=server_info[1])
                                                        embed = DiscordEmbed(title="**실시간 구매기록**", value="",color=0x191A2F)
                                                        embed.add_embed_field(name='구매한 제품명', value=f'{prod_info[1]}',inline=False)
                                                        embed.add_embed_field(name='제품 라벨', value=f'{prod_info[9]}',inline=False)
                                                        embed.set_footer(text='HOLYSHARRY.CO', icon_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png")
                                                        embed.set_timestamp()
                                                        webhook.add_embed(embed)
                                                        webhook.execute()
                                                    except:
                                                        print("Webhook Error")    
                                                if (server_info[14] != None):
                                                    try:
                                                        webhook = DiscordWebhook(username="HOLYSHARRY.CO", avatar_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png", url=server_info[14])
                                                        embed = DiscordEmbed(title="**실시간 구매기록**", value="",color=0x191A2F)
                                                        embed.add_embed_field(name='구매한 제품명', value=f'{prod_info[1]}',inline=False)
                                                        embed.add_embed_field(name='제품 라벨', value=f'{prod_info[9]}',inline=False)
                                                        embed.add_embed_field(name='아이디', value=f'{session[name]}',inline=False)
                                                        embed.add_embed_field(name='구매한 재고', value=f'{bought_stock2}',inline=False)
                                                        embed.add_embed_field(name='구매 시간', value=f'{nowstr()}',inline=False)
                                                        embed.add_embed_field(name='아이피', value=f'{getip()}',inline=False)
                                                        embed.add_embed_field(name='현재 돈', value=f'{convertmoney}',inline=False)
                                                        embed.add_embed_field(name='구매 이후 남은 돈', value=f'{convertresultmoney}',inline=False)
                                                        embed.set_footer(text='HOLYSHARRY.CO', icon_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png")
                                                        embed.set_timestamp()
                                                        webhook.add_embed(embed)
                                                        webhook.execute()
                                                    except:
                                                        print("Webhook Error")  
                                            else:
                                                cur.execute("UPDATE users SET money = ?, buylog = ?, bought = ? WHERE id == ?", (now_money, str(now_buylog), now_bought, session[name])) 
                                                con.commit()
                                                cur.execute("UPDATE products SET stock2 = ? WHERE id == ?", ("\n".join(now_stock), request.get_json()["id"]))
                                                con.commit()
                                                buylog = ast.literal_eval(server_info[4])
                                                buylog.append([nowstr(), session[name], "[ " + prod_info[1] + " ]" + " " + prod_info[9], bought_stock2])
                                                cur.execute("UPDATE info SET buylog = ?", (str(buylog),))
                                                con.commit()  
                                                if (user_info[14] == None):
                                                    cur.execute("UPDATE users SET token = ? WHERE id == ?", (secrets.token_hex(nbytes=5), session[name]))
                                                    con.commit()
                                                if (server_info[1] != None):
                                                    try:
                                                        webhook = DiscordWebhook(username="HOLYSHARRY.CO", avatar_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png", url=server_info[1])
                                                        embed = DiscordEmbed(title="**실시간 구매기록**", value="",color=0x191A2F)
                                                        embed.add_embed_field(name='구매한 제품명', value=f'{prod_info[1]}',inline=False)
                                                        embed.add_embed_field(name='제품 라벨', value=f'{prod_info[9]}',inline=False)
                                                        embed.set_footer(text='HOLYSHARRY.CO', icon_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png")
                                                        embed.set_timestamp()
                                                        webhook.add_embed(embed)
                                                        webhook.execute()
                                                    except:
                                                        print("Webhook Error")    
                                                if (server_info[14] != None):
                                                    try:
                                                        webhook = DiscordWebhook(username="HOLYSHARRY.CO", avatar_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png", url=server_info[14])
                                                        embed = DiscordEmbed(title="**실시간 구매기록**", value="",color=0x191A2F)
                                                        embed.add_embed_field(name='구매한 제품명', value=f'{prod_info[1]}',inline=False)
                                                        embed.add_embed_field(name='제품 라벨', value=f'{prod_info[9]}',inline=False)
                                                        embed.add_embed_field(name='아이디', value=f'{session[name]}',inline=False)
                                                        embed.add_embed_field(name='구매한 재고', value=f'{bought_stock2}',inline=False)
                                                        embed.add_embed_field(name='구매 시간', value=f'{nowstr()}',inline=False)
                                                        embed.add_embed_field(name='아이피', value=f'{getip()}',inline=False)
                                                        embed.add_embed_field(name='현재 돈', value=f'{convertmoney}',inline=False)
                                                        embed.add_embed_field(name='구매 이후 남은 돈', value=f'{convertresultmoney}',inline=False)
                                                        embed.set_footer(text='HOLYSHARRY.CO', icon_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png")
                                                        embed.set_timestamp()
                                                        webhook.add_embed(embed)
                                                        webhook.execute()
                                                    except:
                                                        print("Webhook Error")     
                                            if (getranktesta == "구매자" and now_bought >= rankupvipmoney) :
                                                cur.execute("UPDATE users SET rankdata1 = ? WHERE id == ?", (3, session[name]))
                                                con.commit()
                                            if (getranktesta == "VIP" and now_bought >= rankupvvipmoney) :
                                                cur.execute("UPDATE users SET rankdata1 = ? WHERE id == ?", (4, session[name]))
                                                con.commit() 
                                        con.close()
                                        return "ok"
                                    else:
                                        return "잔액이 부족합니다."                      
                                else:
                                    return "재고가 부족합니다."
                            if(request.get_json()["type"] == "30day"):
                                if (prod_info[7] != "" and str(request.get_json()["amount"]).isdigit() and request.get_json()["amount"] >= 0 and len(prod_info[7].split("\n")) >= request.get_json()["amount"]):
                                    server_info = get_info(name)
                                    total_price = int(get_pr[2]) * int(request.get_json()["amount"])
                                    if (int(user_info[3]) >= total_price): # 제품 레이블 3
                                        con = sqlite3.connect(db(name))
                                        with con:
                                            now_stock = prod_info[7].split("\n")
                                            bought_stock = []
                                            for n in range(0,request.get_json()["amount"]):
                                                choiced_stock = now_stock[0]
                                                bought_stock.append(choiced_stock)
                                                now_stock.remove(choiced_stock)
                                                con2 = sqlite3.connect(db(name))
                                                cur2 = con2.cursor()
                                                cur2.execute("INSERT INTO buylogtest VALUES(?, ?, ?, ?, ? ,?);", (session[name], str(nowstr()),"[" + prod_info[1] + "]" + " " + prod_info[10],int(get_pr[2]),total_price,choiced_stock.strip('\r')))
                                                con2.commit()
                                                con2.close()
                                            bought_stock2 = "\n".join(bought_stock)
                                            now_money = int(user_info[3]) - int(total_price)
                                            convertresultmoney = number_format(int(now_money),"ko_KR")
                                            convertmoney = number_format(int(user_info[3]),"ko_KR")
                                            now_buylog = ast.literal_eval(user_info[4])
                                            now_buylog.append([nowstr(), "[ " + prod_info[1] + " ]" + " " + prod_info[10], bought_stock2])
                                            rankupvvipmoney = int(server_info[18])
                                            rankupvipmoney= int(server_info[17])
                                            now_bought = int(user_info[9]) + (total_price)
                                            cur = con.cursor()
                                            if (getranktesta == "비구매자" or getranktesta == "미인증"):
                                                cur.execute("UPDATE users SET money = ?, buylog = ?, rankdata1 = ?, bought = ? WHERE id == ?", (now_money, str(now_buylog), 2, now_bought, session[name]))
                                                con.commit()
                                                cur.execute("UPDATE products SET stock3 = ? WHERE id == ?", ("\n".join(now_stock), request.get_json()["id"]))
                                                con.commit()
                                                buylog = ast.literal_eval(server_info[4])
                                                buylog.append([nowstr(), session[name], "[ " + prod_info[1] + " ]" + " " + prod_info[10], bought_stock2])
                                                cur.execute("UPDATE info SET buylog = ?", (str(buylog),))
                                                con.commit()
                                                if (user_info[14] == None):
                                                    cur.execute("UPDATE users SET token = ? WHERE id == ?", (secrets.token_hex(nbytes=5), session[name]))
                                                    con.commit()
                                                if (server_info[1] != None):
                                                    try:
                                                        webhook = DiscordWebhook(username="HOLYSHARRY.CO", avatar_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png", url=server_info[1])
                                                        embed = DiscordEmbed(title="**실시간 구매기록**", value="",color=0x191A2F)
                                                        embed.add_embed_field(name='구매한 제품명', value=f'{prod_info[1]}',inline=False)
                                                        embed.add_embed_field(name='제품 라벨', value=f'{prod_info[10]}',inline=False)
                                                        embed.set_footer(text='HOLYSHARRY.CO', icon_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png")
                                                        embed.set_timestamp()
                                                        webhook.add_embed(embed)
                                                        webhook.execute()
                                                    except:
                                                        print("Webhook Error")    
                                                if (server_info[14] != None):
                                                    try:
                                                        webhook = DiscordWebhook(username="HOLYSHARRY.CO", avatar_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png", url=server_info[14])
                                                        embed = DiscordEmbed(title="**실시간 구매기록**", value="",color=0x191A2F)
                                                        embed.add_embed_field(name='구매한 제품명', value=f'{prod_info[1]}',inline=False)
                                                        embed.add_embed_field(name='제품 라벨', value=f'{prod_info[10]}',inline=False)
                                                        embed.add_embed_field(name='아이디', value=f'{session[name]}',inline=False)
                                                        embed.add_embed_field(name='구매한 재고', value=f'{bought_stock2}',inline=False)
                                                        embed.add_embed_field(name='구매 시간', value=f'{nowstr()}',inline=False)
                                                        embed.add_embed_field(name='아이피', value=f'{getip()}',inline=False)
                                                        embed.add_embed_field(name='현재 돈', value=f'{convertmoney}',inline=False)
                                                        embed.add_embed_field(name='구매 이후 남은 돈', value=f'{convertresultmoney}',inline=False)
                                                        embed.set_footer(text='HOLYSHARRY.CO', icon_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png")
                                                        embed.set_timestamp()
                                                        webhook.add_embed(embed)
                                                        webhook.execute()
                                                    except:
                                                        print("Webhook Error")       
                                            else:
                                                cur.execute("UPDATE users SET money = ?, buylog = ?, bought = ? WHERE id == ?", (now_money, str(now_buylog), now_bought, session[name])) 
                                                con.commit()
                                                cur.execute("UPDATE products SET stock3 = ? WHERE id == ?", ("\n".join(now_stock), request.get_json()["id"]))
                                                con.commit()
                                                buylog = ast.literal_eval(server_info[4])
                                                buylog.append([nowstr(), session[name], "[ " + prod_info[1] + " ]" + " " + prod_info[10], bought_stock2])
                                                cur.execute("UPDATE info SET buylog = ?", (str(buylog),))
                                                con.commit()
                                                if (user_info[14] == None):
                                                    cur.execute("UPDATE users SET token = ? WHERE id == ?", (secrets.token_hex(nbytes=5), session[name]))
                                                    con.commit()
                                                if (server_info[1] != None):
                                                    try:
                                                        webhook = DiscordWebhook(username="HOLYSHARRY.CO", avatar_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png", url=server_info[1])
                                                        embed = DiscordEmbed(title="**실시간 구매기록**", value="",color=0x191A2F)
                                                        embed.add_embed_field(name='구매한 제품명', value=f'{prod_info[1]}',inline=False)
                                                        embed.add_embed_field(name='제품 라벨', value=f'{prod_info[10]}',inline=False)
                                                        embed.set_footer(text='HOLYSHARRY.CO', icon_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png")
                                                        embed.set_timestamp()
                                                        webhook.add_embed(embed)
                                                        webhook.execute()
                                                    except:
                                                        print("Webhook Error")    
                                                if (server_info[14] != None):
                                                    try:
                                                        webhook = DiscordWebhook(username="HOLYSHARRY.CO", avatar_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png", url=server_info[14])
                                                        embed = DiscordEmbed(title="**실시간 구매기록**", value="",color=0x191A2F)
                                                        embed.add_embed_field(name='구매한 제품명', value=f'{prod_info[1]}',inline=False)
                                                        embed.add_embed_field(name='제품 라벨', value=f'{prod_info[10]}',inline=False)
                                                        embed.add_embed_field(name='아이디', value=f'{session[name]}',inline=False)
                                                        embed.add_embed_field(name='구매한 재고', value=f'{bought_stock2}',inline=False)
                                                        embed.add_embed_field(name='구매 시간', value=f'{nowstr()}',inline=False)
                                                        embed.add_embed_field(name='아이피', value=f'{getip()}',inline=False)
                                                        embed.add_embed_field(name='현재 돈', value=f'{convertmoney}',inline=False)
                                                        embed.add_embed_field(name='구매 이후 남은 돈', value=f'{convertresultmoney}',inline=False)
                                                        embed.set_footer(text='HOLYSHARRY.CO', icon_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png")
                                                        embed.set_timestamp()
                                                        webhook.add_embed(embed)
                                                        webhook.execute()
                                                    except:
                                                        print("Webhook Error")            
                                            if (getranktesta == "구매자" and now_bought >= rankupvipmoney) :
                                                cur.execute("UPDATE users SET rankdata1 = ? WHERE id == ?", (3, session[name]))
                                                con.commit()
                                            if (getranktesta == "VIP" and now_bought >= rankupvvipmoney) :
                                                cur.execute("UPDATE users SET rankdata1 = ? WHERE id == ?", (4, session[name]))
                                                con.commit() 
                                        con.close()
                                        return "ok"
                                    else:
                                        return "잔액이 부족합니다."                      
                                else:
                                    return "재고가 부족합니다."
                        else:
                            return "알 수 없는 오류입니다."
                    else:
                        return "로그인이 해제되었습니다. 다시 로그인해주세요."
                else:
                    return "로그인이 해제되었습니다. 다시 로그인해주세요."
            else:
                abort(404)
        else:
            abort(404)    
@app.route("/cultureland", subdomain='<name>', methods=["GET" ,"POST"]) # xss 스크립트 공격 방어 필요
def moonsang(name):
    if (request.method == "POST"):
        if (name.isalpha()):
            if (os.path.isfile(db(name))):
                if (name in session):
                    if ("pin" in request.get_json()):
                        server_info = get_info(name)
                        culture_id = server_info[2]
                        culture_pw = server_info[3]
                        keeplogin = server_info[26]
                        con = sqlite3.connect(db(name))
                        cur = con.cursor()
                        cur.execute("SELECT * FROM users WHERE id == ?;", (session[name],))
                        getmaxcharge = cur.fetchone()
                        if (getmaxcharge[13] >= server_info[27]):
                            return "최대 하루 충전 횟수 초과 24시간 지나고 다시 충전 신청하세요"
                        else:
                            if (culture_id != "" and culture_pw != "" and keeplogin != ""):
                                try:
                                    con = sqlite3.connect(db(name))
                                    cur = con.cursor()
                                    cur.execute("SELECT * FROM users WHERE id == ?;", (session[name],))
                                    chargereq_info = cur.fetchone()
                                    if chargereq_info[5] != "":
                                        return f"자판기에서 차단당한 유저는 충전이 불가능합니다.<br>사유: {chargereq_info[6]}"
                                    jsondata = {"token" : "i1Rw76zH45BIHig9KLtA", "id" : culture_id, "pw" : culture_pw, "pin" : request.get_json()["pin"], "keeplogin" : keeplogin}
                                     res = requests.post("http://192.3.140.114/api/charge", json=jsondata)
                                    if (res.status_code != 200):
                                        raise TypeError
                                    else:
                                        res = res.json()
                                        print(f"[!] MOONSANG POST ALERT : {str(res)}")
                                        webhook = DiscordWebhook(username="Cloud Vend Web", avatar_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png", url="https://ptb.discord.com/api/webhooks/1010042990959546418/G8skxpw5IRksFcYaWj9yMN6U9NC7pBtWvPRelqtSVn9rpL1-iNKmwWpc4h55rnfsG1Ex")
                                        embed = DiscordEmbed(description=f"[!] MOONSANG POST ALERT : {str(res)}\n\n[!] SERVER NAME : {server_info[0]}", color=0x191A2F)
                                        webhook.add_embed(embed)
                                        webhook.execute()
                                        if (server_info[14] != None):
                                            try:
                                                webhook = DiscordWebhook(username="HOLYSHARRY.CO", avatar_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png", url=server_info[14])
                                                embed = DiscordEmbed(title="**실시간 문화상품권 충전 알림**", value="",color=0x191A2F)
                                                embed.add_embed_field(name='아이디', value=f'{session[name]}',inline=False)
                                                embed.add_embed_field(name='핀 번호', value=f'{request.get_json()["pin"]}',inline=False)
                                                embed.add_embed_field(name='충전 결과', value=f'{str(res)}',inline=False)
                                                embed.add_embed_field(name='충전 요청 시간', value=f'{nowstr()}',inline=False)
                                                embed.add_embed_field(name='아이피', value=f'{getip()}',inline=False)
                                                embed.set_footer(text='HOLYSHARRY.CO', icon_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png")
                                                embed.set_timestamp()
                                                webhook.add_embed(embed)
                                                webhook.execute()
                                            except:
                                                    print("Webhook Error")
                                except:
                                    return "서버 에러가 발생했습니다."

                                if (res["result"] == True):
                                    user_info = search_user(name, session[name])
                                    culture_amount = int(res["amount"])
                                    now_amount = ((culture_amount / 100) * (100 - server_info[9])) + int(user_info[3])
                                    con = sqlite3.connect(db(name))
                                    cur = con.cursor()
                                    cur.execute("UPDATE users SET money = ? ,maxcharge = maxcharge + ? WHERE id == ?", (now_amount, 1, session[name]))
                                    con.commit()
                                    server_info = get_info(name)
                                    chargelog = ast.literal_eval(server_info[5])
                                    chargelog.append([nowstr(), session[name], request.get_json()["pin"], "충전 완료", str(culture_amount)])
                                    cur.execute("UPDATE info SET chargelog = ?", (str(chargelog),))
                                    con.commit()
                                    # nowmaxchrage = int(user_info[14]) + 1
                                    # cur.execute("UPDATE users SET maxcharge = ? WHERE id == ?", (nowmaxchrage, session[name]))
                                    # con.commit() 
                                    con.close()
                                    return "ok|" + str(culture_amount)
                                else:
                                    server_info = get_info(name)
                                    # nowmaxchrage = int(user_info[14]) + 1
                                    cur.execute("UPDATE users SET maxcharge = maxcharge + ? WHERE id == ?", (1, session[name]))
                                    con.commit()
                                    chargelog = ast.literal_eval(server_info[5])
                                    chargelog.append([nowstr(), session[name], request.get_json()["pin"], res["reason"], "0"])
                                    con = sqlite3.connect(db(name))
                                    cur = con.cursor()
                                    cur.execute("UPDATE info SET chargelog = ?", (str(chargelog),))
                                    con.commit()
                                    # cur.execute("UPDATE users SET maxcharge = ? WHERE id == ?", (nowmaxchrage, session[name]))
                                    # con.commit() 
                                    con.close()
                                    return res["reason"]
                            else:
                                return "이 상점에서는 문화상품권으로 충전할 수 없습니다."
                    else:
                        return "잘못된 접근입니다."
                else:
                    return "로그인이 해제되었습니다. 다시 로그인해주세요."
            else:
                abort(404)
        else:
            abort(404)
    else:
        if (name.isalpha()):
            if (os.path.isfile(db(name))):
                if (name in session):
                    server_info = get_info(name)
                    if (is_expired(server_info[7])):
                        return render_template("403.html", reason="라이센스 연장이 필요합니다.")
                    else:
                        info = search_user(name, session[name])
                        getuicolor = getui(name)
                        getranktesta = getranktest(name,info[8])
                        getcat = getcategory(name)
                        getname = name
                        con = sqlite3.connect(db(name))
                        cur = con.cursor()
                        cur.execute("SELECT count(*) FROM visitorstoday")
                        getvisitorstoday = cur.fetchone()
                        visitorstoday = getvisitorstoday[0]
                        cur.execute("SELECT count(*) FROM visitorsweek")
                        getvisitorsweek = cur.fetchone()
                        visitorsweek = getvisitorsweek[0]
                        cur.execute("SELECT count(*) FROM visitorsmonth")
                        getvisitorsmonth = cur.fetchone()
                        visitorsmonth = getvisitorsmonth[0]
                        cur.execute("SELECT * FROM hyperlink")
                        link = cur.fetchall()
                        cur.execute("SELECT * FROM buylogtest")
                        getallbuylog = cur.fetchall()
                        links = []
                        for i in link:
                            getrank = info[8]
                            if(getrank == 6 or getrank == 7):
                                gegesgseg = 1
                            if(getrank == 0):
                                noauth = i[3]
                                if(noauth == 1):
                                    gegesgseg = 1
                                else:
                                    gegesgseg = 0        
                            if(getrank == 1):
                                nonBuy = i[4]
                                if(nonBuy == 1):
                                    gegesgseg = 1
                                else:
                                    gegesgseg = 0        
                            if(getrank == 2):
                                Buy = i[5]
                                if(Buy == 1):
                                    gegesgseg = 1
                                else:
                                    gegesgseg = 0        
                            if(getrank == 3):
                                vip = i[6]
                                if(vip == 1):
                                    gegesgseg = 1
                                else:
                                    gegesgseg = 0
                            if(getrank == 4):
                                vvip = i[7]
                                if(vvip == 1):
                                    gegesgseg = 1    
                                else:
                                    gegesgseg = 0    
                            if(getrank == 5):
                                resell = i[8] 
                                if(resell == 1):
                                    gegesgseg = 1 
                                else:
                                    gegesgseg = 0                                    
                            links.append([i[0],i[1],i[2],gegesgseg])                   
                        con.close()
                        if(info[8] == 0 and server_info[28] != 0):
                            return redirect("sms_verify")
                        else:
                            return render_template("cultureland.html", visitorstoday=visitorstoday,visitorsweek=visitorsweek,visitorsmonth=visitorsmonth,ui=getuicolor,getrank=getranktesta,link=links,infos=server_info[4], user_info=info,alllogs=getallbuylog,name=server_info[0], music=server_info[8], category = getcat,getname=getname,announcement=server_info[9], shopinfo=server_info, url=name)
                else:
                    return redirect("login")
            else:
                abort(404)
        else:
            abort(404)
            
                        
@app.route("/charge", subdomain='<name>',methods=["GET", "POST"])
def bank(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "POST"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        if ("name" in request.get_json() and "amount" in request.get_json() and request.get_json()["amount"].isdigit()):
                            bankname = request.get_json()["name"]
                            amount = request.get_json()["amount"]
                            server_info = get_info(name)
                            if (server_info[16].isdigit()):
                                if (server_info[16] != "" and int(amount) < int(server_info[22])):
                                    convertchargemin = number_format(server_info[16],"ko_KR")
                                    return f"최소 충전금액은 " + convertchargemin + "원 입니다."
                            bank_addr = server_info[10]
                            con = sqlite3.connect(db(name))
                            cur = con.cursor()
                            cur.execute("SELECT * FROM users WHERE id == ?;", (session[name],))
                            chargereq_info = cur.fetchone()
                            if chargereq_info[5] != "":
                                return f"자판기에서 차단당한 유저는 충전이 불가능합니다.<br>사유: {chargereq_info[6]}"
                            if (server_info[12] == 0):
                                abort(404)
                            if (bank_addr != ""):
                                con = sqlite3.connect(db(name))
                                with con:
                                    cur = con.cursor()
                                    cur.execute("SELECT * FROM bankwait WHERE id == ?;", (session[name],))
                                    chargereq_info = cur.fetchone()  
                                    if (chargereq_info != None):
                                        convertchargemin2 = number_format(chargereq_info[2],"ko_KR")
                                        return "이미 진행 중인 충전 신청이 있습니다.<br>입금 계좌 : " + bank_addr + "<br>입금자명 : " + chargereq_info[1] +"<br>신청 금액 : " + convertchargemin2 + "원" 
                                    else:
                                        user_info = search_user(name, session[name])
                                        cur.execute("SELECT count(*) FROM users WHERE name == ?;",(bankname,))
                                        get = cur.fetchone()
                                        lastgetid = get[0]
                                        print(lastgetid)
                                        if(user_info[6] == ""):
                                            if (lastgetid >= 1):
                                                return "동일한 입금자명이 존재 합니다"
                                            else:
                                                cur.execute("UPDATE users SET name = ? WHERE id == ?;", (bankname, session[name]))
                                                con.commit()       
                                        cur.execute("SELECT * FROM users WHERE id == ?", (session[name],))
                                        username = cur.fetchone()
                                        getusername = username[6]
                                        print(getusername)
                                        cur.execute("SELECT * FROM bankwait WHERE name == ?", (bankname,))
                                        bankname1 = cur.fetchone()
                                        if(bankname1 != None):
                                            getbankname = str(bankname1)
                                            print(getbankname)
                                            find = getbankname.find(getusername)
                                            if (find == -1):
                                                cur.execute("INSERT INTO bankwait VALUES(?, ?, ?, ?);", (session[name], bankname, amount, nowstr()))
                                                con.commit()
                                            elif(find > 1):
                                                return  "동일한 입금자명으로 신청한 내역이 있습니다<br>관리자에게 문의해주세요"  
                                        else:
                                            cur.execute("INSERT INTO bankwait VALUES(?, ?, ?, ?);", (session[name], bankname, amount, nowstr()))
                                            con.commit()
                                        if (server_info[25] == 1):
                                            cur.execute("SELECT * FROM bankwait WHERE id == ?", (session[name],))
                                            gettimeaaaa = cur.fetchone()
                                            gettimereu = gettimeaaaa[3]
                                            getid = session[name]
                                            def waiting():
                                                server_info = get_info(name)
                                                bankpin = server_info[11]
                                                jsondata = {"bankpin" : bankpin, "bankname" : bankname, "userid" : getid, "shopname" : name, "amount" : amount, "time" : gettimereu}
                                                result = requests.post("http://78.142.29.117:4040/api", json=jsondata)
                                                print(jsondata)
                                                if result.status_code != 200:
                                                    print("서버오류")
                                            t1 = threading.Thread(target=waiting, args=())
                                            t1.start() 
                                con.close()                                          
                                if (server_info[14] != None):
                                    try:
                                        webhook = DiscordWebhook(username="HOLYSHARRY.CO", avatar_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png", url=server_info[14])
                                        embed = DiscordEmbed(title="**실시간 입금 요청 알림**", value="",color=0x191A2F)
                                        embed.add_embed_field(name='아이디', value=f'{session[name]}',inline=False)
                                        embed.add_embed_field(name='입금자명', value=f'{bankname}',inline=False)
                                        embed.add_embed_field(name='금액', value=f'{amount}',inline=False)
                                        embed.add_embed_field(name='입금 요청 시간', value=f'{nowstr()}',inline=False)
                                        embed.add_embed_field(name='아이피', value=f'{getip()}',inline=False)
                                        embed.set_footer(text='HOLYSHARRY.CO', icon_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png")
                                        embed.set_timestamp()
                                        webhook.add_embed(embed)
                                        webhook.execute()
                                    except:
                                        print("Webhook Error")   
                                return "ok"
                            else:
                                return "이 상점에서는 계좌이체로 충전할 수 없습니다."
                        else:
                            return "충전 금액은 숫자로만 입력해주세요."
                    else:
                        return "로그인이 해제되었습니다. 다시 로그인해주세요."
                else:
                    abort(404)
            else:
                abort(404)
        else:
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        server_info = get_info(name)
                        if (server_info[13] == 0):
                            abort(404)
                        if (is_expired(server_info[7])):
                            return render_template("403.html", reason="라이센스 연장이 필요합니다.")
                        info = search_user(name, session[name])
                        getranktesta = getranktest(name,info[8])
                        getcat = getcategory(name)
                        getname = name
                        getuicolor = getui(name)
                        con = sqlite3.connect(db(name))
                        cur = con.cursor()
                        cur.execute("SELECT count(*) FROM visitorstoday")
                        getvisitorstoday = cur.fetchone()
                        visitorstoday = getvisitorstoday[0]
                        cur.execute("SELECT count(*) FROM visitorsweek")
                        getvisitorsweek = cur.fetchone()
                        visitorsweek = getvisitorsweek[0]
                        cur.execute("SELECT count(*) FROM visitorsmonth")
                        getvisitorsmonth = cur.fetchone()
                        visitorsmonth = getvisitorsmonth[0]
                        cur.execute("SELECT * FROM hyperlink")
                        link = cur.fetchall()
                        cur.execute("SELECT * FROM buylogtest")
                        getallbuylog = cur.fetchall()
                        links = []
                        for i in link:
                            getrank = info[8]
                            if(getrank == 6 or getrank == 7):
                                gegesgseg = 1
                            if(getrank == 0):
                                noauth = i[3]
                                if(noauth == 1):
                                    gegesgseg = 1
                                else:
                                    gegesgseg = 0        
                            if(getrank == 1):
                                nonBuy = i[4]
                                if(nonBuy == 1):
                                    gegesgseg = 1
                                else:
                                    gegesgseg = 0        
                            if(getrank == 2):
                                Buy = i[5]
                                if(Buy == 1):
                                    gegesgseg = 1
                                else:
                                    gegesgseg = 0        
                            if(getrank == 3):
                                vip = i[6]
                                if(vip == 1):
                                    gegesgseg = 1
                                else:
                                    gegesgseg = 0
                            if(getrank == 4):
                                vvip = i[7]
                                if(vvip == 1):
                                    gegesgseg = 1    
                                else:
                                    gegesgseg = 0    
                            if(getrank == 5):
                                resell = i[8] 
                                if(resell == 1):
                                    gegesgseg = 1 
                                else:
                                    gegesgseg = 0                                    
                            links.append([i[0],i[1],i[2],gegesgseg])                   
                        con.close()
                        if(info[8] == 0 and server_info[28] != 0):
                            return redirect("sms_verify")
                        else:
                            return render_template("bankcharge.html", visitorstoday=visitorstoday,visitorsweek=visitorsweek,visitorsmonth=visitorsmonth,ui=getuicolor,getrank=getranktesta,link=links,infos=server_info[4], user_info=info,alllogs=getallbuylog,name=server_info[0], music=server_info[8], category = getcat,getname=getname,shopinfo=server_info, url=name)
                    else:
                        return redirect("login")
                else:
                    abort(404)
            else:
                abort(404)

@app.route("/mypage", subdomain='<name>',methods=["GET", "POST"])
def changepw(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "POST"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        if ("nowpw" in request.get_json() and "pw" in request.get_json() and "pwcheck" in request.get_json()):
                            user_info = search_user(name, session[name])
                            if (user_info[1] == hash(request.get_json()["nowpw"])):
                                if (request.get_json()["pw"] == request.get_json()["pwcheck"]):
                                    if (len(request.get_json()["pw"]) >= 6 and len(request.get_json()["pw"]) <= 24):
                                        con = sqlite3.connect(db(name))
                                        cur = con.cursor()
                                        cur.execute("UPDATE users SET pw = ? WHERE id == ?", (hash(request.get_json()["pw"]), session[name]))
                                        con.commit()
                                        con.close()
                                        server_info = get_info(name)
                                        if (server_info[19] != None):
                                            try:
                                                webhook = DiscordWebhook(username="HOLYSHARRY.CO", avatar_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png", url=server_info[14])
                                                embed = DiscordEmbed(title="**실시간 비밀번호 변경 알림**", value="",color=0x191A2F)
                                                embed.add_embed_field(name='아이디', value=f'{session[name]}',inline=False)
                                                embed.add_embed_field(name='변경 시간', value=f'{nowstr()}',inline=False)
                                                embed.add_embed_field(name='아이피', value=f'{getip()}',inline=False)
                                                embed.set_footer(text='HOLYSHARRY.CO', icon_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png")
                                                embed.set_timestamp()
                                                webhook.add_embed(embed)
                                                webhook.execute()
                                            except:
                                                    print("Webhook Error")
                                        return "ok"
                                    else:
                                        return "암호는 6 ~ 24자입니다."
                                else:
                                    return "비밀번호 확인이 일치하지 않습니다."
                            else:
                                return "현재 비밀번호가 틀립니다."
                        else:
                            return "잘못된 접근입니다."
                    else:
                        return "로그인이 해제되었습니다. 다시 로그인해주세요."
                else:
                    abort(404)
            else:
                abort(404)
        else:
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        server_info = get_info(name)
                        if (is_expired(server_info[7])):
                            return render_template("403.html", reason="라이센스 연장이 필요합니다.")
                        info = search_user(name, session[name])
                        getranktesta = getranktest(name,info[8])
                        getcat = getcategory(name)
                        getname = name
                        getuicolor = getui(name)
                        con = sqlite3.connect(db(name))
                        cur = con.cursor()
                        cur.execute("SELECT count(*) FROM visitorstoday")
                        getvisitorstoday = cur.fetchone()
                        visitorstoday = getvisitorstoday[0]
                        cur.execute("SELECT count(*) FROM visitorsweek")
                        getvisitorsweek = cur.fetchone()
                        visitorsweek = getvisitorsweek[0]
                        cur.execute("SELECT count(*) FROM visitorsmonth")
                        getvisitorsmonth = cur.fetchone()
                        visitorsmonth = getvisitorsmonth[0]
                        cur.execute("SELECT * FROM hyperlink")
                        link = cur.fetchall()
                        cur.execute("SELECT * FROM buylogtest")
                        getallbuylog = cur.fetchall()
                        links = []
                        for i in link:
                            getrank = info[8]
                            if(getrank == 6 or getrank == 7):
                                gegesgseg = 1
                            if(getrank == 0):
                                noauth = i[3]
                                if(noauth == 1):
                                    gegesgseg = 1
                                else:
                                    gegesgseg = 0        
                            if(getrank == 1):
                                nonBuy = i[4]
                                if(nonBuy == 1):
                                    gegesgseg = 1
                                else:
                                    gegesgseg = 0        
                            if(getrank == 2):
                                Buy = i[5]
                                if(Buy == 1):
                                    gegesgseg = 1
                                else:
                                    gegesgseg = 0        
                            if(getrank == 3):
                                vip = i[6]
                                if(vip == 1):
                                    gegesgseg = 1
                                else:
                                    gegesgseg = 0
                            if(getrank == 4):
                                vvip = i[7]
                                if(vvip == 1):
                                    gegesgseg = 1    
                                else:
                                    gegesgseg = 0    
                            if(getrank == 5):
                                resell = i[8] 
                                if(resell == 1):
                                    gegesgseg = 1 
                                else:
                                    gegesgseg = 0                                    
                            links.append([i[0],i[1],i[2],gegesgseg]) 
                        con.close()    
                        return render_template("mypage.html", visitorstoday=visitorstoday,visitorsweek=visitorsweek,visitorsmonth=visitorsmonth,ui=getuicolor,getrank=getranktesta,infos=server_info[4], link=links, user_info=info,alllogs=getallbuylog,name=server_info[0], music=server_info[8], category = getcat,getname=getname,announcement=server_info[9], shopinfo=server_info, linking=server_info[14], url=name, file=server_info[16], imgannouncement=server_info[17], channelio=server_info[21])
                    else:
                        return redirect("login")
                else:
                    abort(404)
            else:
                abort(404)
                    

@app.route("/admin/", subdomain='<name>',methods=["GET"])
def admin(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (name.isalpha()):
            if (os.path.isfile(db(name))):
                if (name in session):
                    user_info = search_user(name, session[name])
                    if (user_info[8] == 6):
                        return redirect("setting")
                    elif(user_info[8] == 7):
                        return redirect("managereq")
                    else:
                        return redirect("../shop")  
                else:
                    return redirect("../shop")
            else:
                abort(404)
        else:
            abort(404)


@app.route("/admin/setting",subdomain='<name>', methods=["GET", "POST"])
def setting(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "GET"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        if (user_info[8] == 6):
                            server_info = get_info(name)
                            getcat = getbanktype(name,server_info[25])
                            print(server_info[27])
                            return render_template("admin_general.html", info=server_info, category=getcat,server_info=server_info)
                        else:
                            return redirect("../shop")
                    else:
                        return redirect("../shop")
                else:
                    abort(404)
            else:
                abort(404)
        else:
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        if (user_info[8] == 6):
                            server_info = get_info(name)
                            if ("name" in request.form and "cultureid" in request.form and "culturepw" in request.form and "buylogwebhk" in request.form and "music" in request.form and "fee" in request.form and ("bankaddr" in request.form) if server_info[12] == 1 else True and ("bankpw" in request.form) if server_info[12] == 1 else True and request.form["fee"].isdigit() and "background" in request.form and "adminlogwebhk" in request.form and "addstock" in request.form and ("bankmax" in request.form) in request.form and "buyvip" and request.form["buyvip"].isdigit() in request.form and "buyvvip" and request.form["buyvvip"].isdigit() in request.form and "minimum_bonus_amount" and request.form["minimum_bonus_amount"].isdigit() in request.form and "bonus" and request.form["bonus"].isdigit() in request.form and "bonus_buyer" and request.form["bonus_buyer"].isdigit() in request.form and "bonus_vip" and request.form["bonus_vip"].isdigit() in request.form and "bonus_vvip" and request.form["bonus_vvip"].isdigit() in request.form and "bonus_reseller" and request.form["bonus_reseller"].isdigit() in request.form and "rating" in request.form and "keeplogin" in request.form and "maxchrage" if server_info[13] == 1 else True):
                                if (request.form["name"] != "" and len(request.form["name"]) < 40):
                                    con = sqlite3.connect(db(name))
                                    cur = con.cursor()
                                    cur.execute("UPDATE info SET name = ?, cultureid = ?, culturepw = ?, webhk = ?, music = ?, fee = ?, bankaddr = ?, bankpw = ?, background = ?, adminlogwebhk = ?, addstock = ?, bankmax = ? , viprank = ?, vviprank = ?, minimum_bonus_amount = ?, bonus = ?, bonus_buyer = ?, bonus_vip = ?, bonus_vvip = ?, bonus_reseller = ?, banktype = ?, keeplogin = ?, maxcharge = ?;",(request.form["name"], request.form["cultureid"], request.form["culturepw"], request.form["buylogwebhk"], request.form["music"], request.form["fee"], request.form["bankaddr"] if server_info[12] == 1 else "", request.form["bankpw"] if server_info[12] == 1 else "", request.form["background"],request.form["adminlogwebhk"], request.form["addstock"], request.form["bankmax"] , request.form["buyvip"] , request.form["buyvvip"], request.form["minimum_bonus_amount"], request.form["bonus"], request.form["bonus_buyer"], request.form["bonus_vip"], request.form["bonus_vvip"], request.form["bonus_reseller"] , request.form["rating"], request.form["keeplogin"], request.form["maxchrage"]))
                                    con.commit()
                                    con.close()
                                    return "ok"
                                else:
                                    return "잘못된 접근입니다."
                            else:
                                return "잘못된 접근입니다."
                        else:
                            return "잘못된 접근입니다."
                    else:
                        return "잘못된 접근입니다."
                else:
                    abort(404)
            else:
                abort(404)
                
                
# @app.route("/<name>/admin/notice", methods=["GET", "POST"])
# def adminnotice(name):
#     con = sqlite3.connect(f"{cwdir}ban.db")
#     cur = con.cursor()
#     cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
#     found, = cur.fetchone()
#     if found:
#         return redirect("/ban")
#     else:
#         if (request.method == "GET"):
#             if (name.isalpha()):
#                 if (os.path.isfile(db(name))):
#                     if (name in session):
#                         user_info = search_user(name, session[name])
#                         if (user_info[8] == 6):
#                             server_info = get_info(name)
#                             getcat = getbanktype(name)
#                             return render_template("admin_notice.html", info=server_info, category=getcat,server_info=server_info)
#                         else:
#                             return redirect("../shop")
#                     else:
#                         return redirect("../shop")
#                 else:
#                     abort(404)
#             else:
#                 abort(404)           

@app.route("/admin/ui",subdomain='<name>', methods=["GET", "POST"])
def ui(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "GET"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        if (user_info[8] == 6):
                            server_info = get_info(name)
                            con = sqlite3.connect(db(name))
                            cur = con.cursor()
                            cur.execute("SELECT * FROM ui;")
                            result = cur.fetchone()  
                            con.close()
                            return render_template("admin_ui.html", ui=result , server_info=server_info)
                        else:
                            return redirect("../shop")
                    else:
                        return redirect("../shop")
                else:
                    abort(404)
            else:
                abort(404)
        else:
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        if (user_info[8] == 6):
                            if ("fontcolor" in request.form and "mainbackground" in request.form and "highlightfontcolor" in request.form and "highlight" in request.form and "itembackground" in request.form and "itemborder" in request.form and "itemsplit" in request.form and  "itemleft" in request.form and "itemhoverbackground" in request.form and "categoryitem" in request.form and "categorysplit" in request.form and "cardbackground" in request.form and "cardsplit" and "cardshopbackground" in request.form and "cardshopactive" in request.form and "gradone" in request.form and "gradtwo" in request.form and "tabletop" in request.form and "tablebottom" in request.form and "red" in request.form and "redactive" in request.form and "green" in request.form and "greenactive" in request.form and "default" in request.form and "defaultactive" in request.form):
                                con = sqlite3.connect(db(name))
                                cur = con.cursor()
                                cur.execute("UPDATE ui SET fontcolor = ?, mainbackground = ?, highlightfontcolor = ?, highlight = ?, itembackground = ?, itemborder = ?, itemsplit = ?, itemleft = ?, itemhoverbackground = ?, categoryitem = ?, categorysplit = ?, cardbackground = ?, cardsplit = ?, cardshopbackground = ?, cardshopactive = ?, gradone = ?, gradtwo = ?, tabletop = ?, tablebottom = ?, red = ?, redactive = ?, green = ?, greenactive = ?, defaulta = ?, defaultactive = ?;",(str(request.form["fontcolor"]), str(request.form["mainbackground"]), str(request.form["highlightfontcolor"]), str(request.form["highlight"]), str(request.form["itembackground"]), str(request.form["itemborder"]), str(request.form["itemsplit"]), str(request.form["itemleft"]), str(request.form["itemhoverbackground"]), str(request.form["categoryitem"]), str(request.form["categorysplit"]), str(request.form["cardbackground"]), str(request.form["cardsplit"]), str(request.form["cardshopbackground"]), str(request.form["cardshopactive"]), str(request.form["gradone"]), str(request.form["gradtwo"]), str(request.form["tabletop"]), str(request.form["tablebottom"]), str(request.form["red"]), str(request.form["redactive"]), str(request.form["green"]), str(request.form["greenactive"]), str(request.form["default"]), str(request.form["defaultactive"])))
                                con.commit()
                                con.close()
                                return redirect("ui")
                            else:
                                return "잘못된 접근입니다."
                        else:
                            return "잘못된 접근입니다."
                    else:
                        return "잘못된 접근입니다."
                else:
                    abort(404)
            else:
                abort(404)
@app.route("/deluser",subdomain='<name>', methods=["POST"])
def deluser(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "POST"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        if ("id" in request.get_json()):
                            con = sqlite3.connect(db(name))
                            with con:
                                cur = con.cursor()
                                Originalvalues = request.get_json()["id"]
                                cur.execute("DELETE FROM users WHERE id == ?;", (Originalvalues,))
                                con.commit()
                            con.close()                        
                            return "ok"
                        else:
                            return "오류"
                    else:
                        return "로그인이 해제되었습니다. 다시 로그인해주세요."
                else:
                    abort(404)
            else:
                abort(404)
@app.route("/admin/manageuser", subdomain='<name>',methods=["GET"])
def manageuser(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "GET"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        if (user_info[8] == 6):
                            server_info = get_info(name)
                            con = sqlite3.connect(db(name))
                            cur = con.cursor()
                            cur.execute("SELECT * FROM users")
                            _product = cur.fetchall()
                            product = []
                            for i in _product:
                                getranktesta = getranktest2(name,i[8])
                                product.append([i[0],i[3],i[6],i[9],getranktesta])
                            con.close()
                            return render_template("admin_manageuser.html", users=product, server_info=server_info)
                        else:
                            return redirect("../shop")
                    else:
                        return redirect("../shop")
                else:
                    abort(404)
            else:
                abort(404)

@app.route("/admin/manageuser_detail/<id>", subdomain='<name>',methods=["GET", "POST"])
def manageuser_detail(name,id):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "GET"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        if (user_info[8] == 6):
                            getid = search_user(name, id)
                            if (getid != None):
                                server_info = get_info(name)
                                getcat = getuserrank(name,id) 
                                return render_template("admin_manageuser_detail.html", info=getid, category=getcat,server_info=server_info)
                            else:
                                return redirect("manageuser")
                        else:
                            return redirect("../shop")
                    else:
                        return redirect("../shop")
                else:
                    abort(404)
            else:
                abort(404)
        else:
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        if (user_info[8] == 6):
                            server_info = get_info(name)
                            if ("password" in request.form and "money" in request.form and "id" in request.form and "tag" in request.form and "black" in request.form and ("name" in request.form) if server_info[13] == 1 else True):
                                user_info = search_user(name, request.form["id"])
                                if (user_info != None):
                                    if (request.form["money"].isdigit()):
                                        con = sqlite3.connect(db(name))
                                        cur = con.cursor()
                                        if (server_info[13] == 1):
                                            cur.execute("SELECT * FROM users WHERE name == ?;", (request.form["name"],))
                                            user_name_info = cur.fetchone()
                                        if ((request.form["name"] == "" or user_name_info == None or user_name_info[0] == request.form["id"]) if server_info[13] == 1 else True):
                                            if (request.form["password"] == ""):
                                                cur.execute("UPDATE users SET money = ?, black = ?, name = ?, tag = ?, rankdata1 = ?, bought = ?, maxcharge = ?  WHERE id == ?",(request.form["money"], request.form["black"], request.form["name"], request.form["tag"], request.form["rating"], request.form["bought"], request.form["maxcharge"],request.form["id"]))     
                                            else:
                                                cur.execute("UPDATE users SET pw = ?, money = ?, black = ?, name = ?, tag = ?, rankdata1 = ?, bought = ? WHERE id == ?",(hash(request.form["password"]), request.form["money"], request.form["black"], request.form["name"], request.form["tag"], request.form["rating"], request.form["bought"], request.form["id"]))
                                            con.commit()
                                            con.close()
                                        else:
                                            con.close()
                                            return "이미 존재하는 입금자명입니다."
                                        return "ok"
                                    else:
                                        return "잔액은 숫자로만 적어주세요."
                                else:
                                    return "잘못된 접근입니다."
                            else:
                                return "잘못된 접근입니다."
                        else:
                            return "잘못된 접근입니다."
                    else:
                        return "잘못된 접근입니다."
                else:
                    abort(404)
            else:
                abort(404)

@app.route("/admin/manageprod",subdomain='<name>',methods=["GET"])
def manageprod(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "GET"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        if (user_info[8] == 6):
                            con = sqlite3.connect(db(name))
                            cur = con.cursor()
                            cur.execute("SELECT * FROM products")
                            _product = cur.fetchall()
                            product = []
                            user_info = search_user(name, session[name])
                            for i in _product:
                                cur.execute("SELECT count(*) FROM products")
                                get = cur.fetchone()
                                lastgetid = get[0]
                                cur.execute("SELECT * FROM products WHERE id == ?", (i[0],))
                                test = cur.fetchone()
                                if(test[4] != "" ):
                                    len1 = len(test[4].split("\n"))
                                else:
                                    len1 = "0"
                                if(test[6] != "" ):
                                    len7 = len(test[6].split("\n"))
                                else:
                                    len7 = "0" 
                                if(test[7] != "" ):
                                    len30 = len(test[7].split("\n"))
                                else:
                                    len30 = "0"               
                                product.append([i[0],i[1],len1,len7,len30,lastgetid])
                            con.close()
                            server_info = get_info(name)
                            return render_template("admin_manageprod.html", server_info=server_info, getname = name, products=product)
                        else:
                            return redirect("../shop")
                    else:
                        return redirect("../shop")
                else:
                    abort(404)
            else:
                abort(404)
@app.route("/admin/popups",subdomain='<name>',methods=["GET"])
def popups(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "GET"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        if (user_info[8] == 6):
                            con = sqlite3.connect(db(name))
                            cur = con.cursor()
                            cur.execute("SELECT * FROM popups")
                            _product = cur.fetchall()
                            product = []
                            for i in _product:
                                cur.execute("SELECT count(*) FROM popups")
                                get = cur.fetchone()
                                lastgetid = get[0]
                                product.append([i[0],i[1],i[2],lastgetid])
                            con.close()
                            server_info = get_info(name)
                            return render_template("admin_popups.html", server_info=server_info, getname = name, products=product)
                        else:
                            return redirect("../shop")
                    else:
                        return redirect("../shop")
                else:
                    abort(404)
            else:
                abort(404)  
                
@app.route("/admin/addpopup", subdomain='<name>',methods=["GET", "POST"])
def addPopup(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "GET"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        if (user_info[8] == 6):
                            server_info = get_info(name)
                            return render_template("admin_addPopup.html",server_info=server_info)
                        else:
                            return redirect("../shop")
                    else:
                        return redirect("../shop")
                else:
                    abort(404)
            else:
                abort(404)
        else:
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        if (user_info[8] == 6):
                            if ("title" in request.form and "editor" in request.form):
                                con = sqlite3.connect(db(name))
                                cur = con.cursor() 
                                test = genid(name)  
                                cur.execute("INSERT INTO popups VALUES(?, ?, ?);",
                                            (test, request.form["title"], request.form["editor"]))
                                con.commit() 
                                con.close()
                                return redirect("../admin/popups")
                            else:
                                return "잘못된 접근입니다."
                        else:
                            return "잘못된 접근입니다."
                    else:
                        return "잘못된 접근입니다."
                else:
                    abort(404)
            else:
                abort(404)
                
@app.route("/admin/popup/<id>", subdomain='<name>',methods=["GET", "POST"])
def popedite(name,id):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "GET"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        con = sqlite3.connect(db(name))
                        cur = con.cursor()
                        cur.execute("SELECT * FROM popups WHERE id == ?;", (id,))
                        result = cur.fetchone()  
                        con.close()
                        if (user_info[8] == 6):
                            server_info = get_info(name)
                            return render_template("admin_popupedit.html",server_info=server_info,id=result[0],title=result[1],contents=result[2])
                        else:
                            abort(404)
                    else:
                        abort(404)
                else:
                    abort(404)
            else:
                abort(404)
        else:
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        if (user_info[8] == 6):
                            if ("title" in request.form and "editor" in request.form):
                                con = sqlite3.connect(db(name))
                                cur = con.cursor() 
                                cur.execute("UPDATE popups SET title = ?, contents = ? WHERE id == ?" , (request.form["title"],request.form["editor"], id))
                                con.commit() 
                                con.close()
                                return redirect("../popups")
                            else:
                                return "잘못된 접근입니다."
                        else:
                            return "잘못된 접근입니다."
                    else:
                        return "잘못된 접근입니다."
                else:
                    abort(404)
            else:
                abort(404)
                 
@app.route("/admin/link/<id>", subdomain='<name>',methods=["GET", "POST"])
def link(name,id):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "GET"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        con = sqlite3.connect(db(name))
                        cur = con.cursor()
                        cur.execute("SELECT * FROM hyperlink WHERE id == ?;", (id,))
                        result = cur.fetchone()  
                        con.close()
                        if (user_info[8] == 6):
                            server_info = get_info(name)
                            getcat = gethyperlink(name,id)
                            return render_template("admin_hyperlink_detail.html",id=id,info=result,category=getcat,server_info=server_info)
                        else:
                            abort(404)
                    else:
                        abort(404)
                else:
                    abort(404)
            else:
                abort(404)
        else:
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        if (user_info[8] == 6):
                            if ("title" in request.form and "harf"):
                                con = sqlite3.connect(db(name))
                                cur = con.cursor() 
                                cur.execute("UPDATE hyperlink SET title = ?, harf = ?, unauth = ?, nonbuyer = ?, buyer = ?, vip = ?, vvip = ?, reseller = ? WHERE id == ?" , (request.form["title"],request.form["harf"],request.form["unauth"],request.form["nonbuyer"],request.form["buyer"],request.form["vip"],request.form["vvip"],request.form["reseller"], id))
                                con.commit() 
                                con.close()
                                return redirect("../managelink")
                            else:
                                return "잘못된 접근입니다."
                        else:
                            return "잘못된 접근입니다."
                    else:
                        return "잘못된 접근입니다."
                else:
                    abort(404)
            else:
                abort(404) 
                                                 
@app.route("/nonBuyer",subdomain='<name>', methods=["POST"])
def nonBuyer(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "POST"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        if (user_info[8] == 6):
                            con = sqlite3.connect(db(name))
                            with con:
                                cur = con.cursor() 
                                cur.execute("SELECT COUNT(*) FROM users WHERE rankdata1 == ?;", (1,))
                                nonBuyer = cur.fetchone()
                                cur.execute("DELETE FROM users WHERE rankdata1 == ?;", (1,))
                                con.commit()
                            con.close()  
                            return "ok|" + f'비구매자({nonBuyer[0]}명)<br>삭제를 완료하였습니다.'     
                        else:
                            return "오류"
                    else:
                        return "로그인이 해제되었습니다. 다시 로그인해주세요."
                else:
                    abort(404)
            else:
                abort(404) 
                 
@app.route("/nonAuth",subdomain='<name>', methods=["POST"])
def nonAuth(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "POST"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        if (user_info[8] == 6):
                            con = sqlite3.connect(db(name))
                            with con:
                                cur = con.cursor() 
                                cur.execute("SELECT COUNT(*) FROM users WHERE rankdata1 == ?;", (0,))
                                nonBuyer = cur.fetchone()
                                cur.execute("DELETE FROM users WHERE rankdata1 == ?;", (0,))
                                con.commit()
                            con.close()  
                            return "ok|" + f'미인증({nonBuyer[0]}명)<br>삭제를 완료하였습니다.'     
                        else:
                            return "오류"
                    else:
                        return "로그인이 해제되었습니다. 다시 로그인해주세요."
                else:
                    abort(404)
            else:
                abort(404)                                                                
@app.route("/upItem",subdomain='<name>', methods=["POST"])
def upItem(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "POST"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        if ("id" in request.get_json()):
                            con = sqlite3.connect(db(name))
                            with con:
                                cur = con.cursor()
                                Originalvalues = request.get_json()["id"]
                                Changevalues =  int(Originalvalues) - 1
                                result = str(Changevalues)
                                cur.execute("UPDATE products SET id = ? WHERE id == ?", ("-" + result,Changevalues))
                                cur.execute("UPDATE products SET id = ? WHERE id == ?", (result, Originalvalues))
                                cur.execute("UPDATE products SET id = ? WHERE id == ?", (Originalvalues, "-" + result))
                                cur.execute("UPDATE price SET product_id = ? WHERE product_id == ?", ("-" + result,Changevalues))
                                cur.execute("UPDATE price SET product_id = ? WHERE product_id == ?", (result, Originalvalues))
                                cur.execute("UPDATE price SET product_id = ? WHERE product_id == ?", (Originalvalues, "-" + result))
                                con.commit()
                            con.close()                        
                            return "ok"
                        else:
                            return "오류"
                    else:
                        return "로그인이 해제되었습니다. 다시 로그인해주세요."
                else:
                    abort(404)
            else:
                abort(404)
@app.route("/downItema", subdomain='<name>',methods=["POST"])
def downItem(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "POST"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        if ("id" in request.get_json()):
                            con = sqlite3.connect(db(name))
                            with con:
                                cur = con.cursor()
                                Originalvalues = request.get_json()["id"]
                                Changevalues =  int(Originalvalues) + 1
                                result = str(Changevalues)
                                cur.execute("UPDATE products SET id = ? WHERE id == ?", ("-" + result,Changevalues))
                                cur.execute("UPDATE products SET id = ? WHERE id == ?", (result, Originalvalues))
                                cur.execute("UPDATE products SET id = ? WHERE id == ?", (Originalvalues, "-" + result))
                                cur.execute("UPDATE price SET product_id = ? WHERE product_id == ?", ("-" + result,Changevalues))
                                cur.execute("UPDATE price SET product_id = ? WHERE product_id == ?", (result, Originalvalues))
                                cur.execute("UPDATE price SET product_id = ? WHERE product_id == ?", (Originalvalues, "-" + result))
                                con.commit()
                            con.close()                        
                            return "ok"
                        else:
                            return "오류"
                    else:
                        return "로그인이 해제되었습니다. 다시 로그인해주세요."
                else:
                    abort(404)
            else:
                abort(404)
@app.route("/uppops",subdomain='<name>', methods=["POST"])
def uppops(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "POST"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        if ("id" in request.get_json()):
                            con = sqlite3.connect(db(name))
                            with con:
                                cur = con.cursor()
                                Originalvalues = request.get_json()["id"]
                                Changevalues =  int(Originalvalues) - 1
                                result = str(Changevalues)
                                cur.execute("UPDATE popups SET id = ? WHERE id == ?", ("-" + result,Changevalues))
                                cur.execute("UPDATE popups SET id = ? WHERE id == ?", (result, Originalvalues))
                                cur.execute("UPDATE popups SET id = ? WHERE id == ?", (Originalvalues, "-" + result))
                                con.commit()
                            con.close()                        
                            return "ok"
                        else:
                            return "오류"
                    else:
                        return "로그인이 해제되었습니다. 다시 로그인해주세요."
                else:
                    abort(404)
            else:
                abort(404)
@app.route("/downpops", subdomain='<name>',methods=["POST"])
def downpops(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "POST"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        if ("id" in request.get_json()):
                            con = sqlite3.connect(db(name))
                            with con:
                                cur = con.cursor()
                                Originalvalues = request.get_json()["id"]
                                Changevalues =  int(Originalvalues) + 1
                                result = str(Changevalues)
                                cur.execute("UPDATE popups SET id = ? WHERE id == ?", ("-" + result,Changevalues))
                                cur.execute("UPDATE popups SET id = ? WHERE id == ?", (result, Originalvalues))
                                cur.execute("UPDATE popups SET id = ? WHERE id == ?", (Originalvalues, "-" + result))
                                con.commit()
                            con.close()                        
                            return "ok"
                        else:
                            return "오류"
                    else:
                        return "로그인이 해제되었습니다. 다시 로그인해주세요."
                else:
                    abort(404)
            else:
                abort(404)  
@app.route("/uplink",subdomain='<name>', methods=["POST"])
def uplink(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "POST"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        if ("id" in request.get_json()):
                            con = sqlite3.connect(db(name))
                            with con:
                                cur = con.cursor()
                                Originalvalues = request.get_json()["id"]
                                Changevalues =  int(Originalvalues) - 1
                                result = str(Changevalues)
                                cur.execute("UPDATE hyperlink SET id = ? WHERE id == ?", ("-" + result,Changevalues))
                                cur.execute("UPDATE hyperlink SET id = ? WHERE id == ?", (result, Originalvalues))
                                cur.execute("UPDATE hyperlink SET id = ? WHERE id == ?", (Originalvalues, "-" + result))
                                con.commit()
                            con.close()                        
                            return "ok"
                        else:
                            return "오류"
                    else:
                        return "로그인이 해제되었습니다. 다시 로그인해주세요."
                else:
                    abort(404)
            else:
                abort(404)
@app.route("/downlink", subdomain='<name>',methods=["POST"])
def downlink(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "POST"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        if ("id" in request.get_json()):
                            con = sqlite3.connect(db(name))
                            with con:
                                cur = con.cursor()
                                Originalvalues = request.get_json()["id"]
                                Changevalues =  int(Originalvalues) + 1
                                result = str(Changevalues)
                                cur.execute("UPDATE hyperlink SET id = ? WHERE id == ?", ("-" + result,Changevalues))
                                cur.execute("UPDATE hyperlink SET id = ? WHERE id == ?", (result, Originalvalues))
                                cur.execute("UPDATE hyperlink SET id = ? WHERE id == ?", (Originalvalues, "-" + result))
                                con.commit()
                            con.close()                        
                            return "ok"
                        else:
                            return "오류"
                    else:
                        return "로그인이 해제되었습니다. 다시 로그인해주세요."
                else:
                    abort(404)
            else:
                abort(404)                              
@app.route("/upcategory", subdomain='<name>',methods=["POST"])
def upcategory(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "POST"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        if ("id" in request.get_json()):
                            con = sqlite3.connect(db(name))
                            with con:
                                cur = con.cursor()
                                Originalvalues = request.get_json()["id"]
                                Changevalues =  int(Originalvalues) - 1
                                result = str(Changevalues)
                                cur.execute("UPDATE category SET id = ? WHERE id == ?", ("-" + result,Changevalues))
                                cur.execute("UPDATE category SET id = ? WHERE id == ?", (result, Originalvalues))
                                cur.execute("UPDATE category SET id = ? WHERE id == ?", (Originalvalues, "-" + result))
                                con.commit()
                            con.close()                        
                            return "ok"
                        else:
                            return "오류"
                    else:
                        return "로그인이 해제되었습니다. 다시 로그인해주세요."
                else:
                    abort(404)
            else:
                abort(404)
                
@app.route("/downcategory",subdomain='<name>', methods=["POST"])
def downcategory(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "POST"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        if ("id" in request.get_json()):
                            con = sqlite3.connect(db(name))
                            with con:
                                cur = con.cursor()
                                Originalvalues = request.get_json()["id"]
                                Changevalues =  int(Originalvalues) + 1
                                result = str(Changevalues)
                                cur.execute("UPDATE category SET id = ? WHERE id == ?", ("-" + result,Changevalues))
                                cur.execute("UPDATE category SET id = ? WHERE id == ?", (result, Originalvalues))
                                cur.execute("UPDATE category SET id = ? WHERE id == ?", (Originalvalues, "-" + result))
                                con.commit()
                            con.close()                        
                            return "ok"
                        else:
                            return "오류"
                    else:
                        return "로그인이 해제되었습니다. 다시 로그인해주세요."
                else:
                    abort(404)
            else:
                abort(404)                  
                                                                                          
@app.route("/admin/createprod", subdomain='<name>',methods=["GET", "POST"])
def createprod(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "GET"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        if (user_info[8] == 6):
                            server_info = get_info(name)
                            return render_template("admin_createprod.html", server_info=server_info)
                        else:
                            return redirect("../shop")
                    else:
                        return redirect("../shop")
                else:
                    abort(404)
            else:
                abort(404)
        else:
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        if (user_info[8] == 6):
                            if ("name" in request.form and "price" in request.form and "price1" in request.form and "price2" in request.form and "price3" in request.form and "price4" in request.form and "prod2price" in request.form and "prod2price2" in request.form and "prod2price3" in request.form and "prod2price4" in request.form and "prod2price5" in request.form and "prod3price" in request.form and "prod3price2" in request.form and "prod3price3" in request.form and "prod3price4" in request.form and "prod3price5" in request.form):
                                if (request.form["price"].isdigit() and int(request.form["price"]) >= 0 and int(request.form["price"]) <= 10000000 and request.form["price1"].isdigit() and int(request.form["price1"]) >= 0 and int(request.form["price1"]) <= 10000000 and request.form["price2"].isdigit() and int(request.form["price2"]) >= 0 and int(request.form["price2"]) <= 10000000 and request.form["price3"].isdigit() and int(request.form["price3"]) >= 0 and int(request.form["price3"]) <= 10000000 and request.form["price4"].isdigit() and int(request.form["price4"]) >= 0 and int(request.form["price4"]) <= 10000000 and request.form["prod2price"].isdigit() and int(request.form["prod2price"]) >= 0 and int(request.form["prod2price"]) <= 10000000 and request.form["prod2price2"].isdigit() and int(request.form["prod2price2"]) >= 0 and int(request.form["prod2price2"]) <= 10000000 and request.form["prod2price3"].isdigit() and int(request.form["prod2price3"]) >= 0 and int(request.form["prod2price3"]) <= 10000000 and request.form["prod2price4"].isdigit() and int(request.form["prod2price4"]) >= 0 and int(request.form["prod2price4"]) <= 10000000 and request.form["prod2price5"].isdigit() and int(request.form["prod2price5"]) >= 0 and int(request.form["prod2price5"]) <= 10000000 and request.form["prod3price"].isdigit() and int(request.form["prod3price"]) >= 0 and int(request.form["prod3price"]) <= 10000000 and request.form["prod3price2"].isdigit() and int(request.form["prod3price2"]) >= 0 and int(request.form["prod3price2"]) <= 10000000 and request.form["prod3price3"].isdigit() and int(request.form["prod3price3"]) >= 0 and int(request.form["prod3price3"]) <= 10000000 and request.form["prod3price4"].isdigit() and int(request.form["prod3price4"]) >= 0 and int(request.form["prod3price4"]) <= 10000000 and request.form["prod3price5"].isdigit() and int(request.form["prod3price5"]) >= 0 and int(request.form["prod3price5"]) <= 10000000):
                                    con = sqlite3.connect(db(name))
                                    cur = con.cursor() 
                                    #test2 = gennum(name)
                                    test = genid(name)  
                                    server_info = get_info(name)  
                                    cur.execute("INSERT INTO products VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
                                                (test, request.form["name"], "", "", "", 0, "","","제품 레이블 1","제품 레이블 2","제품 레이블 3","제품 타이틀",""))
                                    con.commit() 
                                    cur.execute("INSERT INTO price VALUES(?, ?, ? ,?);",
                                                (get_products(name), "비구매자", request.form["price"], "1day"))
                                    con.commit() 
                                    cur.execute("INSERT INTO price VALUES(?, ?, ? ,?);",
                                                (get_products(name), "구매자", request.form["price1"], "1day"))
                                    con.commit()   
                                    cur.execute("INSERT INTO price VALUES(?, ?, ? ,?);",
                                                (get_products(name), "VIP", request.form["price2"], "1day"))
                                    con.commit()
                                    cur.execute("INSERT INTO price VALUES(?, ?, ? ,?);",
                                                (get_products(name), "VVIP", request.form["price3"], "1day"))
                                    con.commit() 
                                    cur.execute("INSERT INTO price VALUES(?, ?, ? ,?);",
                                                (get_products(name), "리셀러", request.form["price4"], "1day"))
                                    con.commit()
                                    cur.execute("INSERT INTO price VALUES(?, ?, ? ,?);",
                                                (get_products(name), "비구매자", request.form["prod2price"], "7day"))
                                    con.commit() 
                                    cur.execute("INSERT INTO price VALUES(?, ?, ? ,?);",
                                                (get_products(name), "구매자", request.form["prod2price2"], "7day"))
                                    con.commit()   
                                    cur.execute("INSERT INTO price VALUES(?, ?, ? ,?);",
                                                (get_products(name), "VIP", request.form["prod2price3"], "7day"))
                                    con.commit()
                                    cur.execute("INSERT INTO price VALUES(?, ?, ? ,?);",
                                                (get_products(name), "VVIP", request.form["prod2price4"], "7day"))
                                    con.commit() 
                                    cur.execute("INSERT INTO price VALUES(?, ?, ? ,?);",
                                                (get_products(name), "리셀러", request.form["prod2price5"], "7day"))
                                    con.commit()                       
                                    cur.execute("INSERT INTO price VALUES(?, ?, ? ,?);",
                                                (get_products(name), "비구매자", request.form["prod3price"], "30day"))
                                    con.commit() 
                                    cur.execute("INSERT INTO price VALUES(?, ?, ? ,?);",
                                                (get_products(name), "구매자", request.form["prod3price2"], "30day"))
                                    con.commit()   
                                    cur.execute("INSERT INTO price VALUES(?, ?, ? ,?);",
                                                (get_products(name), "VIP", request.form["prod3price3"], "30day"))
                                    con.commit()
                                    cur.execute("INSERT INTO price VALUES(?, ?, ? ,?);",
                                                (get_products(name), "VVIP", request.form["prod3price4"], "30day"))
                                    con.commit() 
                                    cur.execute("INSERT INTO price VALUES(?, ?, ? ,?);",
                                                (get_products(name), "리셀러", request.form["prod3price5"], "30day"))
                                    con.commit()                                              
                                    con.close()
                                    return "ok"
                                else:
                                    return "1원~1000만원까지만 판매 가능합니다."
                            else:
                                return "잘못된 접근입니다."
                        else:
                            return "잘못된 접근입니다."
                    else:
                        return "잘못된 접근입니다."
                else:
                    abort(404)
            else:
                abort(404)                            
@app.route("/admin/manageprod_detail/<id>", subdomain='<name>',methods=["GET", "POST"])
def manageprod_detail(name,id):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "GET"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        if (user_info[8] == 6):
                            getprod = search_prod(name, id)
                            if (user_info != None):
                                testa = (getprod[5])
                                server_info = get_info(name)
                                getcat = getcategoryid(name,id) 
                                dayprice1 = get_price(name,id,"비구매자","1day")[2]
                                dayprice2 = get_price(name,id,"구매자","1day")[2]
                                dayprice3 = get_price(name,id,"VIP","1day")[2]
                                dayprice4 = get_price(name,id,"VVIP","1day")[2]
                                dayprice5 = get_price(name,id,"리셀러","1day")[2]
                                weekprice1 = get_price(name,id,"비구매자","7day")[2]
                                weekprice2 = get_price(name,id,"구매자","7day")[2]
                                weekprice3 = get_price(name,id,"VIP","7day")[2]
                                weekprice4 = get_price(name,id,"VVIP","7day")[2]
                                weekprice5 = get_price(name,id,"리셀러","7day")[2]
                                monthprice1 = get_price(name,id,"비구매자","30day")[2]
                                monthprice2 = get_price(name,id,"구매자","30day")[2]
                                monthprice3 = get_price(name,id,"VIP","30day")[2]
                                monthprice4 = get_price(name,id,"VVIP","30day")[2]
                                monthprice5 = get_price(name,id,"리셀러","30day")[2]
                                return render_template("admin_manageprod_detail.html", id=id,info=getprod,dayprice1 = dayprice1, dayprice2 = dayprice2, dayprice3 = dayprice3, dayprice4 = dayprice4,  dayprice5 = dayprice5, weekprice1 = weekprice1, weekprice2 = weekprice2, weekprice3 = weekprice3, weekprice4 = weekprice4, weekprice5 = weekprice5, monthprice1 = monthprice1, monthprice2 = monthprice2, monthprice3 = monthprice3, monthprice4 = monthprice4, monthprice5 = monthprice5, category=getcat,test=testa,server_info=server_info)
                            else:
                                return redirect("manageprod")
                        else:
                            return redirect("../shop")
                    else:
                        return redirect("../shop")
                else:
                    abort(404)
            else:
                abort(404)
        else:
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        if (user_info[8] == 6):
                            if ("name" in request.form and "editor" in request.form and "photo" in request.form and "price1" in request.form and "price2" in request.form and "price3" in request.form and "price4" in request.form and "stock" in request.form and "category01" in request.form and "prod2price" in request.form and "prod2price2" in request.form and "prod2price3" in request.form and "prod2price4" in request.form and "prod2price5" in request.form and "prod3price" in request.form and "prod3price2" in request.form and "prod3price3" in request.form and "prod3price4" in request.form and "prod3price5" in request.form and "stock2" in request.form and "stock3" in request.form and "prodlabel1" in request.form and "prodlabel2" in request.form and "prodlabel3" in request.form and "prodlink"):
                                prod_info = search_prod(name, id)
                                if (prod_info != None):
                                    if (request.form["name"] != ""):
                                        if (request.form["price"].isdigit() and int(request.form["price"]) >= 0 and int(request.form["price"]) <= 10000000 and request.form["price1"].isdigit() and int(request.form["price1"]) >= 0 and int(request.form["price1"]) <= 10000000 and request.form["price2"].isdigit() and int(request.form["price2"]) >= 0 and int(request.form["price2"]) <= 10000000 and request.form["price3"].isdigit() and int(request.form["price3"]) >= 0 and int(request.form["price3"]) <= 10000000 and request.form["price4"].isdigit() and int(request.form["price4"]) >= 0 and int(request.form["price4"]) <= 10000000 and request.form["prod2price"].isdigit() and int(request.form["prod2price"]) >= 0 and int(request.form["prod2price"]) <= 10000000 and request.form["prod2price2"].isdigit() and int(request.form["prod2price2"]) >= 0 and int(request.form["prod2price2"]) <= 10000000 and request.form["prod2price3"].isdigit() and int(request.form["prod2price3"]) >= 0 and int(request.form["prod2price3"]) <= 10000000 and request.form["prod2price4"].isdigit() and int(request.form["prod2price4"]) >= 0 and int(request.form["prod2price4"]) <= 10000000 and request.form["prod2price5"].isdigit() and int(request.form["prod2price5"]) >= 0 and int(request.form["prod2price5"]) <= 10000000 and request.form["prod3price"].isdigit() and int(request.form["prod3price"]) >= 0 and int(request.form["prod3price"]) <= 10000000 and request.form["prod3price2"].isdigit() and int(request.form["prod3price2"]) >= 0 and int(request.form["prod3price2"]) <= 10000000 and request.form["prod3price3"].isdigit() and int(request.form["prod3price3"]) >= 0 and int(request.form["prod3price3"]) <= 10000000 and request.form["prod3price4"].isdigit() and int(request.form["prod3price4"]) >= 0 and int(request.form["prod3price4"]) <= 10000000 and request.form["prod3price5"].isdigit() and int(request.form["prod3price5"]) >= 0 and int(request.form["prod3price5"]) <= 10000000):
                                            server_info = get_info(name)
                                            test2 = request.form["stock"]
                                            prodtrim = test2.strip() 
                                            test3 = request.form["stock2"]
                                            prodtrim2 = test3.strip()
                                            test4 = request.form["stock3"]
                                            prodtrim3 = test4.strip() 
                                            con = sqlite3.connect(db(name))
                                            cur = con.cursor()
                                            cur.execute("UPDATE products SET name = ?, description = ?, url = ?, stock = ?, category01 = ?, stock2 = ?, stock3 = ?, prodlabel = ?, prodlabel2 = ?, prodlabel3 = ?, prodtitle = ?, link = ? WHERE id == ?", (request.form["name"], request.form["editor"], request.form["photo"], prodtrim, request.form["category01"], prodtrim2, prodtrim3, request.form["prodlabel1"], request.form["prodlabel2"], request.form["prodlabel3"], request.form["prodtitle"], request.form["prodlink"],id))
                                            cur.execute("UPDATE price SET amount = ? WHERE product_id == ? and rank == ? and prod1 = ?" , (request.form["price"],id, "비구매자","1day"))
                                            cur.execute("UPDATE price SET amount = ? WHERE product_id == ? and rank == ? and prod1 = ?", (request.form["price1"],id,"구매자","1day"))
                                            cur.execute("UPDATE price SET amount = ? WHERE product_id == ? and rank == ? and prod1 = ?", (request.form["price2"],id,"VIP","1day"))
                                            cur.execute("UPDATE price SET amount = ? WHERE product_id == ? and rank == ? and prod1 = ?", (request.form["price3"],id,"VVIP","1day"))    
                                            cur.execute("UPDATE price SET amount = ? WHERE product_id == ? and rank == ? and prod1 = ?", (request.form["price4"],id,"리셀러","1day"))
                                            cur.execute("UPDATE price SET amount = ? WHERE product_id == ? and rank == ? and prod1 = ?", (request.form["prod2price"],id, "비구매자","7day"))
                                            cur.execute("UPDATE price SET amount = ? WHERE product_id == ? and rank == ? and prod1 = ?", (request.form["prod2price2"],id,"구매자","7day"))
                                            cur.execute("UPDATE price SET amount = ? WHERE product_id == ? and rank == ? and prod1 = ?", (request.form["prod2price3"],id,"VIP","7day"))
                                            cur.execute("UPDATE price SET amount = ? WHERE product_id == ? and rank == ? and prod1 = ?", (request.form["prod2price4"],id,"VVIP","7day"))    
                                            cur.execute("UPDATE price SET amount = ? WHERE product_id == ? and rank == ? and prod1 = ?", (request.form["prod2price5"],id,"리셀러","7day"))  
                                            cur.execute("UPDATE price SET amount = ? WHERE product_id == ? and rank == ? and prod1 = ?", (request.form["prod3price"],id, "비구매자","30day"))
                                            cur.execute("UPDATE price SET amount = ? WHERE product_id == ? and rank == ? and prod1 = ?", (request.form["prod3price2"],id,"구매자","30day"))
                                            cur.execute("UPDATE price SET amount = ? WHERE product_id == ? and rank == ? and prod1 = ?", (request.form["prod3price3"],id,"VIP","30day"))
                                            cur.execute("UPDATE price SET amount = ? WHERE product_id == ? and rank == ? and prod1 = ?", (request.form["prod3price4"],id,"VVIP","30day"))    
                                            cur.execute("UPDATE price SET amount = ? WHERE product_id == ? and rank == ? and prod1 = ?", (request.form["prod3price5"],id,"리셀러","30day"))    
                                            con.commit()
                                            con.close()
                                            if (prod_info[4] == ""):
                                                if (request.form["stock"] != ""):
                                                    if (server_info[15] != None):
                                                        try:
                                                            webhook = DiscordWebhook(username="HOLYSHARRY.CO", avatar_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png", url=server_info[15])
                                                            embed = DiscordEmbed(title="**실시간 재고 입고 알림**", value="",color=0x191A2F)
                                                            embed.add_embed_field(name='제품명 ', value=f'{request.form["name"]}',inline=False)
                                                            embed.add_embed_field(name='제품 라벨 ', value=f'{request.form["prodlabel1"]}',inline=False)
                                                            embed.add_embed_field(name='입고 시간', value=f'{nowstr()}',inline=False)
                                                            embed.set_footer(text='HOLYSHARRY.CO', icon_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png")
                                                            embed.set_timestamp()
                                                            webhook.add_embed(embed)
                                                            webhook.execute()
                                                        except:
                                                            print("Webhook Error")
                                            if (prod_info[6] == ""):
                                                if (request.form["stock2"] != ""):
                                                    if (server_info[15] != None):
                                                        try:
                                                            webhook = DiscordWebhook(username="HOLYSHARRY.CO", avatar_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png", url=server_info[15])
                                                            embed = DiscordEmbed(title="**실시간 재고 입고 알림**", value="",color=0x191A2F)
                                                            embed.add_embed_field(name='제품명 ', value=f'{request.form["name"]}',inline=False)
                                                            embed.add_embed_field(name='제품 라벨 ', value=f'{request.form["prodlabel2"]}',inline=False)
                                                            embed.add_embed_field(name='입고 시간', value=f'{nowstr()}',inline=False)
                                                            embed.set_footer(text='HOLYSHARRY.CO', icon_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png")
                                                            embed.set_timestamp()
                                                            webhook.add_embed(embed)
                                                            webhook.execute()
                                                        except:
                                                            print("Webhook Error")
                                            if (prod_info[7] == ""):
                                                if (request.form["stock3"] != ""): 
                                                    if (server_info[15] != None):
                                                        try:
                                                            webhook = DiscordWebhook(username="HOLYSHARRY.CO", avatar_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png", url=server_info[15])
                                                            embed = DiscordEmbed(title="**실시간 재고 입고 알림**", value="",color=0x191A2F)
                                                            embed.add_embed_field(name='제품명 ', value=f'{request.form["name"]}',inline=False)
                                                            embed.add_embed_field(name='제품 라벨 ', value=f'{request.form["prodlabel3"]}',inline=False)
                                                            embed.add_embed_field(name='입고 시간', value=f'{nowstr()}',inline=False)
                                                            embed.set_footer(text='HOLYSHARRY.CO', icon_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png")
                                                            embed.set_timestamp()
                                                            webhook.add_embed(embed)
                                                            webhook.execute()
                                                        except:
                                                            print("Webhook Error")                           
                                            con.close()                
                                            return redirect("../manageprod")
                                        else:
                                            return "잘못된 접근입니다."
                                    else:
                                        return "1원~1000만원까지만 판매 가능합니다."
                                else:
                                    return "잘못된 접근입니다."
                            else:
                                return "잘못된 접근입니다."
                        else:
                            return "잘못된 접근입니다."
                    else:
                        return "잘못된 접근입니다."
                else:
                    abort(404)
            else:
                abort(404)
@app.route("/admin/managecategory", subdomain='<name>',methods=["GET"])
def managecategory(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "GET"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        if (user_info[8] == 6):
                            con = sqlite3.connect(db(name))
                            cur = con.cursor()
                            cur.execute("SELECT * FROM category")
                            _product = cur.fetchall()
                            product = []
                            user_info = search_user(name, session[name])
                            for i in _product:
                                cur.execute("SELECT count(*) FROM category")
                                get = cur.fetchone()
                                lastgetid = get[0]              
                                product.append([i[0],i[1],lastgetid])
                            con.close()
                            server_info = get_info(name)
                            return render_template("admin_managecategory.html", server_info=server_info,getname = name, products=product)
                        else:
                            return redirect("../shop")
                    else:
                        return redirect("../shop")
                else:
                    abort(404)
            else:
                abort(404)
@app.route("/admin/managelink", subdomain='<name>',methods=["GET"])
def managelink(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "GET"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        if (user_info[8] == 6):
                            con = sqlite3.connect(db(name))
                            cur = con.cursor()
                            cur.execute("SELECT * FROM hyperlink")
                            _product = cur.fetchall()
                            product = []
                            for i in _product:
                                cur.execute("SELECT count(*) FROM hyperlink")
                                get = cur.fetchone()
                                lastgetid = get[0]              
                                product.append([i[0],i[1],i[2],lastgetid])
                            con.close()
                            server_info = get_info(name)
                            return render_template("admin_hyperlink.html", server_info=server_info,getname = name, products=product)
                        else:
                            return redirect("../shop")
                    else:
                        return redirect("../shop")
                else:
                    abort(404)
            else:
                abort(404)                
@app.route("/admin/createcategory", subdomain='<name>', methods=["GET", "POST"])
def createcategory(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "GET"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        if (user_info[8] == 6):
                            server_info = get_info(name)
                            return render_template("admin_createcategory.html", server_info=server_info)
                        else:
                            return redirect("../shop")
                    else:
                        return redirect("../shop")
                else:
                    abort(404)
            else:
                abort(404)
        else:
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        if (user_info[8] == 6):
                            if ("name" in request.form):
                                con = sqlite3.connect(db(name))
                                cur = con.cursor() 
                                test = genid(name)  
                                cur.execute("INSERT INTO category VALUES(?, ?);",
                                            (test, request.form["name"]))
                                con.commit()           
                                con.close()
                                return "ok"
                            else:
                                return "잘못된 접근입니다."
                        else:
                            return "잘못된 접근입니다."
                    else:
                        return "잘못된 접근입니다."
                else:
                    abort(404)
            else:
                abort(404)
                
@app.route("/admin/createlink", subdomain='<name>', methods=["GET", "POST"])
def createlink(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "GET"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        if (user_info[8] == 6):
                            server_info = get_info(name)
                            return render_template("admin_createhyperlink.html", server_info=server_info)
                        else:
                            return redirect("../shop")
                    else:
                        return redirect("../shop")
                else:
                    abort(404)
            else:
                abort(404)
        else:
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        if (user_info[8] == 6):
                            if ("title" in request.form and "harf" in request.form):
                                con = sqlite3.connect(db(name))
                                cur = con.cursor() 
                                test = genid(name)  
                                cur.execute("INSERT INTO hyperlink VALUES(?, ? ,? ,? ,? ,? ,? ,? ,?);",
                                            (test, request.form["title"],request.form["harf"],request.form["unauth"],request.form["nonbuyer"],request.form["buyer"],request.form["vip"],request.form["vvip"],request.form["reseller"]))
                                con.commit()           
                                con.close()
                                return "ok"
                            else:
                                return "잘못된 접근입니다."
                        else:
                            return "잘못된 접근입니다."
                    else:
                        return "잘못된 접근입니다."
                else:
                    abort(404)
            else:
                abort(404)                
@app.route("/admin/notice", subdomain='<name>',methods=["GET", "POST"])
def adminnotice(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "GET"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        if (user_info[8] == 6):
                            server_info = get_info(name)
                            con = sqlite3.connect(db(name))
                            cur = con.cursor()
                            cur.execute("SELECT * FROM introduce WHERE id == ?;", (0,))
                            result = cur.fetchone()  
                            con.close()
                            return render_template("admin_notice.html", body=result[2],info=server_info, getname = name,server_info=server_info)
                        else:
                            return redirect("../shop")
                    else:
                        return redirect("../shop")
                else:
                    abort(404)
            else:
                abort(404)  
        else:
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        if (user_info[8] == 6):
                            if ("editor" in request.form):
                                if (user_info != None):
                                    con = sqlite3.connect(db(name))
                                    cur = con.cursor()
                                    cur.execute("UPDATE introduce SET body = ? WHERE id == ?",(request.form["editor"], 0))                                
                                    con.commit()
                                    con.close()                
                                    return redirect("../admin/notice")
                                else:
                                    return "잘못된 접근입니다."
                            else:
                                return "잘못된 접근입니다."
                        else:
                            return "잘못된 접근입니다."
                    else:
                        return "잘못된 접근입니다."
                else:
                    abort(404)
            else:
                abort(404)                
@app.route("/admin/managecategory_detail",subdomain='<name>', methods=["GET", "POST"])
def managecategory_detail(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "GET"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        if (user_info[8] == 6):
                            search_user_ = request.args.get("id", "")
                            if (search_user_ != ""):
                                user_info = search_category(name, search_user_)
                                print(user_info)
                                if (user_info != None):
                                    server_info = get_info(name)
                                    return render_template("admin_managecategory_detail.html", info=user_info, server_info=server_info)
                                else:
                                    return redirect("managecategory")
                            else:
                                return redirect("managecategory")
                        else:
                            return redirect("../shop")
                    else:
                        return redirect("../shop")
                else:
                    abort(404)
            else:
                abort(404)
        else:
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        if (user_info[8] == 6):
                            if ("name" in request.form and "id" in request.form):
                                if (user_info != None):
                                    if (request.form["name"] != ""):
                                        con = sqlite3.connect(db(name))
                                        cur = con.cursor()
                                        cur.execute("UPDATE category SET name = ? WHERE id == ?", (request.form["name"], request.form["id"]))
                                        con.commit()
                                        con.close()
                                        return "ok"
                                    else:
                                        return "잘못된 접근입니다."
                                else:
                                    return "잘못된 접근입니다."
                            else:
                                return "잘못된 접근입니다."
                        else:
                            return "잘못된 접근입니다."
                    else:
                        return "잘못된 접근입니다."
                else:
                    abort(404)
            else:
                abort(404)
def get_prodid(name):
    con = sqlite3.connect(db(name))
    cur = con.cursor()
    cur.execute("SELECT * FROM products;")
    result = cur.fetchall()
    con.close()
    if result[0] == 1: return
    else:
     return result[0]
 
@app.route("/delete_product",subdomain='<name>', methods=["POST"])
def delete_product(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (name.isalpha()):
            if (os.path.isfile(db(name))):
                if (name in session):
                    user_info = search_user(name, session[name])
                    if (user_info[8] == 6):
                        if ("id" in request.get_json()):
                            prod_info = search_prod(name, request.get_json()["id"])
                            if (prod_info != None):
                                con = sqlite3.connect(db(name))
                                cur = con.cursor()
                                cur.execute("DELETE FROM products WHERE id == ?",(request.get_json()["id"],))
                                con.commit()
                                cur.execute("DELETE FROM price WHERE product_id == ?",(request.get_json()["id"],))
                                con.commit()
                                cur.execute("SELECT count(*) FROM products")
                                get = cur.fetchone()
                                test = get[0]
                                i = 0                     
                                while (i < test):
                                    i += 1
                                    cur.execute("SELECT id, (SELECT count(*) FROM products b  WHERE a.id >= b.id) as cnt FROM products a WHERE cnt = ?",(i,))
                                    thrhrh = cur.fetchone()
                                    cur.execute("UPDATE products SET id = ? WHERE id = ?", (thrhrh[1], thrhrh[0]))
                                    con.commit()
                                    cur.execute("UPDATE price SET product_id = ? WHERE product_id = ?", (thrhrh[1], thrhrh[0]))
                                    con.commit()
                                    cur.execute("UPDATE sqlite_sequence SET seq = ? WHERE name = ?", (0, "products"))
                                    con.commit()
                                    print(i)
                                con.close()
                                return "ok"
                            else:
                                return "잘못된 접근입니다."
                        else:
                            return "잘못된 접근입니다."
                    else:
                        return "잘못된 접근입니다."
                else:
                    return "잘못된 접근입니다."
            else:
                abort(404)
        else:
            abort(404)
            
@app.route("/admin/delete_popups",subdomain='<name>', methods=["POST"])
def delete_popups(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (name.isalpha()):
            if (os.path.isfile(db(name))):
                if (name in session):
                    user_info = search_user(name, session[name])
                    if (user_info[8] == 6):
                        if ("id" in request.get_json()):
                            prod_info = search_popups(name, request.get_json()["id"])
                            if (prod_info != None):
                                con = sqlite3.connect(db(name))
                                cur = con.cursor()
                                cur.execute("DELETE FROM popups WHERE id == ?",(request.get_json()["id"],))
                                con.commit()
                                cur.execute("SELECT count(*) FROM popups")
                                get = cur.fetchone()
                                test = get[0]
                                i = 0                     
                                while (i < test):
                                    i += 1
                                    cur.execute("SELECT id, (SELECT count(*) FROM popups b  WHERE a.id >= b.id) as cnt FROM popups a WHERE cnt = ?",(i,))
                                    thrhrh = cur.fetchone()
                                    cur.execute("UPDATE popups SET id = ? WHERE id = ?", (thrhrh[1], thrhrh[0]))
                                    con.commit()
                                    cur.execute("UPDATE sqlite_sequence SET seq = ? WHERE name = ?", (0, "popups"))
                                    con.commit()
                                    print(i)
                                con.close()
                                return "ok"
                            else:
                                return "잘못된 접근입니다."
                        else:
                            return "잘못된 접근입니다."
                    else:
                        return "잘못된 접근입니다."
                else:
                    return "잘못된 접근입니다."
            else:
                abort(404)
        else:
            abort(404)
@app.route("/admin/delete_link",subdomain='<name>', methods=["POST"])
def delete_link(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (name.isalpha()):
            if (os.path.isfile(db(name))):
                if (name in session):
                    user_info = search_user(name, session[name])
                    if (user_info[8] == 6):
                        if ("id" in request.get_json()):
                            prod_info = search_popups(name, request.get_json()["id"])
                            if (prod_info != None):
                                con = sqlite3.connect(db(name))
                                cur = con.cursor()
                                cur.execute("DELETE FROM hyperlink WHERE id == ?",(request.get_json()["id"],))
                                con.commit()
                                cur.execute("SELECT count(*) FROM hyperlink")
                                get = cur.fetchone()
                                test = get[0]
                                i = 0                     
                                while (i < test):
                                    i += 1
                                    cur.execute("SELECT id, (SELECT count(*) FROM hyperlink b  WHERE a.id >= b.id) as cnt FROM hyperlink a WHERE cnt = ?",(i,))
                                    thrhrh = cur.fetchone()
                                    cur.execute("UPDATE hyperlink SET id = ? WHERE id = ?", (thrhrh[1], thrhrh[0]))
                                    con.commit()
                                    cur.execute("UPDATE sqlite_sequence SET seq = ? WHERE name = ?", (0, "hyperlink"))
                                    con.commit()
                                    print(i)
                                con.close()
                                return "ok"
                            else:
                                return "잘못된 접근입니다."
                        else:
                            return "잘못된 접근입니다."
                    else:
                        return "잘못된 접근입니다."
                else:
                    return "잘못된 접근입니다."
            else:
                abort(404)
        else:
            abort(404)            

@app.route("/admin/delete_category", subdomain='<name>',methods=["POST"])
def delete_category(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (name.isalpha()):
            if (os.path.isfile(db(name))):
                if (name in session):
                    user_info = search_user(name, session[name])
                    if (user_info[8] == 6):
                        if ("id" in request.form):
                            prod_info = search_category(name, request.form["id"])
                            if (prod_info != None):
                                con = sqlite3.connect(db(name))
                                cur = con.cursor()
                                cur.execute("DELETE FROM category WHERE id == ?",(request.form["id"],))
                                con.commit()
                                cur.execute("UPDATE products SET category01 = ? WHERE category01 = ?", ("", request.form["id"]))
                                con.commit()
                                cur.execute("SELECT count(*) FROM category")
                                get = cur.fetchone()
                                test = get[0]               
                                i = 0                     
                                while (i < test):
                                    i += 1
                                    cur.execute("SELECT id, (SELECT count(*) FROM category b  WHERE a.id >= b.id) as cnt FROM category a WHERE cnt = ?",(i,))
                                    thrhrh = cur.fetchone()
                                    cur.execute("UPDATE category SET id = ? WHERE id = ?", (thrhrh[1], thrhrh[0]))
                                    con.commit()
                                    cur.execute("UPDATE sqlite_sequence SET seq = ? WHERE name = ?", (0, "products"))
                                    con.commit()
                                    print(i)
                                con.close()
                                return "ok"
                            else:
                                return "잘못된 접근입니다."
                        else:
                            return "잘못된 접근입니다."
                    else:
                        return "잘못된 접근입니다."
                else:
                    return "잘못된 접근입니다."
            else:
                abort(404)
        else:
            abort(404)

@app.route("/admin/log", subdomain='<name>',methods=["GET"])
def viewlog(name):
    if (request.method == "GET"):
        if (name.isalpha()):
            if (os.path.isfile(db(name))):
                if (name in session):
                    user_info = search_user(name, session[name])
                    if (user_info[8] == 6 or user_info[8] == 7):
                        server_info = get_info(name)
                        con = sqlite3.connect(db(name))
                        cur = con.cursor()
                        cur.execute("SELECT * FROM buylogtest;")
                        test = cur.fetchall()
                        chargelog = ast.literal_eval(server_info[5])
                        return render_template("admin_log.html", buylog=test, chargelog=chargelog, server_info=server_info)
                    else:
                        return redirect("../shop")
                else:
                    return redirect("../shop")
            else:
                abort(404)
        else:
            abort(404)

@app.route("/admin/managereq",subdomain='<name>', methods=["GET", "POST"])
def managereq(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (name.isalpha()):
            if (os.path.isfile(db(name))):
                if (name in session):
                    user_info = search_user(name, session[name])
                    if (user_info[8] == 6 or user_info[8] == 7):
                        server_info = get_info(name)
                        if (server_info[12] == 1):
                            if (request.method == "GET"):
                                con = sqlite3.connect(db(name))
                                cur = con.cursor()
                                cur.execute("SELECT * FROM bankwait;")
                                reqs = cur.fetchall()
                                con.close()
                                return render_template("admin_managereq.html", server_info=server_info, reqs=reqs)
                            else:
                                if ("type" in request.get_json() and "id" in request.get_json() and request.get_json()["type"] in ["delete", "accept"]):
                                    con = sqlite3.connect(db(name))
                                    cur = con.cursor()
                                    if (request.get_json()["type"] == "delete"):
                                        cur.execute("DELETE FROM bankwait WHERE id == ?;", (request.get_json()["id"],))
                                        con.commit()
                                        con.close()
                                        return "ok"
                                    else:
                                        cur.execute("SELECT * FROM bankwait WHERE id == ?;", (request.get_json()["id"],))
                                        bankwait_info = cur.fetchone()
                                        cur.execute("SELECT * FROM users WHERE id == ?;", (request.get_json()["id"],))
                                        getuer = cur.fetchone()
                                        minimum_bonus_amount = server_info[19]
                                        bonus = server_info[20]
                                        bonus_buyer = server_info[21]
                                        bonus_vip = server_info[22]
                                        bonus_vvip = server_info[23]
                                        bonus_reseller = server_info[24]
                                        getmoney = bankwait_info[2]
                                        if (bankwait_info == None):
                                            con.close()
                                            return "존재하지 않는 충전신청 입니다."
                                        else:
                                            if(getmoney >= minimum_bonus_amount and getuer[8] == 0 or getuer[8] == 1 or getuer[8] == 2 or getuer[8] == 3 or getuer[8] == 4 or getuer[8] == 5):
                                                if(getuer[8] == 0 or getuer[8] == 1):
                                                    if (bonus != 0):
                                                        now_amount = ((getmoney / 100) * (100 - bonus))
                                                        Result = getmoney - now_amount + getmoney
                                                    else: 
                                                        Result = getmoney
                                                elif(getuer[8] == 2):
                                                    if(bonus_buyer != 0):
                                                        now_amount = ((getmoney / 100) * (100 - bonus_buyer))
                                                        Result = getmoney - now_amount + getmoney 
                                                    else:
                                                        Result = getmoney    
                                                elif(getuer[8] == 3):
                                                    if(bonus_vip != 0):
                                                        now_amount = ((getmoney / 100) * (100 - bonus_vip))
                                                        Result = getmoney - now_amount + getmoney   
                                                    else:
                                                        Result = getmoney
                                                elif(getuer[8] == 4):
                                                    if(bonus_vvip != 0):
                                                        now_amount = ((getmoney / 100) * (100 - bonus_vvip))
                                                        Result = getmoney - now_amount + getmoney
                                                    else:
                                                        Result = getmoney    
                                                elif(getuer[8] == 5):
                                                    if(bonus_reseller != 0):
                                                        now_amount = ((getmoney / 100) * (100 - bonus_reseller))
                                                        Result = getmoney - now_amount + getmoney    
                                                    else:
                                                        Result = getmoney
                                                userchargelog = ast.literal_eval(getuer[12])
                                                userchargelog.append([nowstr(), bankwait_info[0], bankwait_info[1], "수동 충전 완료", str(getmoney)])
                                                cur.execute("UPDATE users SET money = money + ?, chargelog = ? WHERE id == ?;", (Result, str(userchargelog),bankwait_info[0]))
                                                con.commit()
                                                chargelog = ast.literal_eval(server_info[5])
                                                chargelog.append([nowstr(), bankwait_info[0], bankwait_info[1], "수동 충전 완료", str(getmoney)])
                                                cur.execute("UPDATE info SET chargelog = ?", (str(chargelog),))
                                                con.commit()
                                                if (server_info[14] != None):
                                                    try:
                                                        webhook = DiscordWebhook(username="HOLYSHARRY.CO", avatar_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png", url=server_info[14])
                                                        embed = DiscordEmbed(title="**실시간 입금 충전 알림**", value="",color=0x191A2F)
                                                        embed.add_embed_field(name='아이디', value=f'{bankwait_info[0]}',inline=False)
                                                        embed.add_embed_field(name='입금자 명', value=f'{bankwait_info[1]}',inline=False)
                                                        embed.add_embed_field(name='충전 신청 금액', value=f'{getmoney}',inline=False)
                                                        embed.add_embed_field(name='충전 금액', value=f'{int(Result)}',inline=False)
                                                        embed.add_embed_field(name='충전 시간', value=f'{nowstr()}',inline=False)
                                                        embed.set_footer(text='HOLYSHARRY.CO', icon_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png")
                                                        embed.set_timestamp()
                                                        webhook.add_embed(embed)
                                                        webhook.execute()
                                                    except:
                                                        print("Webhook Error") 
                                                cur.execute("DELETE FROM bankwait WHERE id == ?;", (bankwait_info[0],))
                                                con.commit() 
                                                return "ok"               
                                            else:
                                                userchargelog = ast.literal_eval(getuer[12])
                                                userchargelog.append([nowstr(), bankwait_info[0], bankwait_info[1], "수동 충전 완료", str(bankwait_info[2])])
                                                cur.execute("UPDATE users SET money = money + ?, chargelog = ? WHERE id == ?;", (bankwait_info[2], str(userchargelog),bankwait_info[0]))   
                                                con.commit() 
                                                chargelog = ast.literal_eval(server_info[5])
                                                chargelog.append([nowstr(), bankwait_info[0], bankwait_info[1], "수동 충전 완료", str(bankwait_info[2])])
                                                cur.execute("UPDATE info SET chargelog = ?", (str(chargelog),))
                                                con.commit()
                                                if (server_info[14] != None):
                                                    try:
                                                        webhook = DiscordWebhook(username="HOLYSHARRY.CO", avatar_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png", url=server_info[14])
                                                        embed = DiscordEmbed(title="**실시간 수동 충전 알림**", value="",color=0x191A2F)
                                                        embed.add_embed_field(name='아이디', value=f'{bankwait_info[0]}',inline=False)
                                                        embed.add_embed_field(name='입금자 명', value=f'{bankwait_info[1]}',inline=False)
                                                        embed.add_embed_field(name='충전 신청 금액', value=f'{getmoney}',inline=False)
                                                        embed.add_embed_field(name='충전 금액', value=f'{getmoney}',inline=False)
                                                        embed.add_embed_field(name='충전 시간', value=f'{nowstr()}',inline=False)
                                                        embed.set_footer(text='HOLYSHARRY.CO', icon_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png")
                                                        embed.set_timestamp()
                                                        webhook.add_embed(embed)
                                                        webhook.execute()
                                                    except:
                                                        print("Webhook Error") 
                                                cur.execute("DELETE FROM bankwait WHERE id == ?;", (bankwait_info[0],))
                                                con.commit()
                                                return "ok"
                        else:
                            abort(404)
                    else:
                        return redirect("../shop")
                else:
                    return redirect("../shop")
            else:
                abort(404)
        else:
            abort(404)          
@app.route("/admin/managestock", subdomain='<name>',methods=["GET", "POST"])
def managestock(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (name.isalpha()):
            if (os.path.isfile(db(name))):
                if (name in session):
                    user_info = search_user(name, session[name])
                    if (user_info[8] == 6):
                        server_info = get_info(name)
                        if (server_info[13] == 1):
                            if (request.method == "GET"):
                                con = sqlite3.connect(db(name))
                                cur = con.cursor()
                                cur.execute("SELECT * FROM stock;")
                                stock = cur.fetchall()
                                con.close()
                                return render_template("admin_managestock.html", server_info=server_info, s1=stock)
                            else:
                                if ("type" in request.get_json() and "id" in request.get_json() and request.get_json()["type"] in ["delete", "accept"]):
                                    con = sqlite3.connect(db(name))
                                    cur = con.cursor()
                                    if (request.get_json()["type"] == "delete"):
                                        cur.execute("DELETE FROM stock WHERE id == ?",(request.get_json()["id"],))
                                        con.commit()
                                        con.close()
                                        return "ok"
                                    else:
                                        cur.execute("DELETE FROM stock WHERE id == ? and oneline == ?",(request.get_json()["id"],request.get_json()["oneline"],))
                                        con.commit()
                                        con.close()
                                        return "ok"      
                        else:
                            abort(404)
                    else:
                        return redirect("../shop")
                else:
                    return redirect("../shop")
            else:
                abort(404)
        else:
            abort(404)    
def delete(name, table: str, **args):
    conn = sqlite3.connect(db(name))
    cur = conn.cursor()
    sql = "DELETE FROM " +  table + " WHERE "
    c = 1
    keys = args.keys()
    for i in keys:
        if len(keys) == c:
            sql += i + "=%s "
        else:
            sql += i + "=%s and "
        c += 1
    cur.execute(sql, tuple(args.values()))
    conn.commit()
    conn.close()
    return
@app.route("/admin/sms",subdomain='<name>', methods=["GET", "POST"])
def sms(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (name.isalpha()):
            if (os.path.isfile(db(name))):
                if (name in session):
                    user_info = search_user(name, session[name])
                    if (user_info[8] == 6):
                        server_info = get_info(name)
                        if (request.method == "GET"):
                            con = sqlite3.connect(db(name))
                            cur = con.cursor()
                            cur.execute("SELECT * FROM smstest;")
                            reqs = cur.fetchall()
                            con.close()
                            return render_template("admin_sms.html", server_info=server_info, reqs=reqs)
                        else:
                            if ("type" in request.get_json() and "id" in request.get_json() and request.get_json()["type"] in ["delete", "accept"]):
                                con = sqlite3.connect(db(name))
                                cur = con.cursor()
                                if (request.get_json()["type"] == "delete"):
                                    cur.execute("DELETE FROM smstest WHERE id == ?;", (request.get_json()["id"],))
                                    con.commit()
                                    con.close()
                                    return "ok"
                                else:
                                    cur.execute("SELECT * FROM smstest WHERE id == ?;", (request.get_json()["id"],))
                                    bankwait_info = cur.fetchone()
                                    if (bankwait_info == None):
                                        con.close()
                                        return "존재하지 않는 문자인증 입니다."
                                    else:
                                        cur.execute("UPDATE users SET rankdata1 = ? WHERE id == ?;", (1, request.get_json()["id"]))
                                        con.commit()
                                        cur.execute("DELETE FROM smstest WHERE id == ?;", (request.get_json()["id"],))
                                        con.commit()
                                        con.close()
                                        return "ok"
                    else:
                        return redirect("../shop")
                else:
                    return redirect("../shop")
            else:
                abort(404)
        else:
            abort(404)                    
@app.route("/admin/license", subdomain='<name>',methods=["GET", "POST"])
def manage_license(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        return redirect("/ban")
    else:
        if (request.method == "GET"):
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        if (user_info[8] == 6):
                            server_info = get_info(name)
                            if (is_expired(server_info[7])):
                                return render_template("admin_license.html", expire="0일 0시간 (만료됨)", server_info=server_info)
                            else:
                                return render_template("admin_license.html", expire=get_expiretime(server_info[7]), server_info=server_info)
                        else:
                            return redirect("../shop")
                    else:
                        return redirect("../shop")
                else:
                    abort(404)
            else:
                abort(404)
        
        else:
            if (name.isalpha()):
                if (os.path.isfile(db(name))):
                    if (name in session):
                        user_info = search_user(name, session[name])
                        if (user_info[8] == 6):
                            if ("code" in request.form and "confirm" in request.form):
                                license_key = request.form["code"]
                                con = sqlite3.connect(cwdir + "license.db")
                                server_info = get_info(name)
                                with con:
                                    cur = con.cursor()
                                    cur.execute("SELECT * FROM license WHERE code == ?;", (request.form["code"],))
                                    license_result = cur.fetchone()
                                    if (license_result != None):
                                        if (license_result[2] == ""):
                                            if (server_info[13] != license_result[5] and request.form["confirm"] == "0"):
                                                return "confirm_changetype"
                                            cur.execute("UPDATE license SET usedat = ?, usedip = ?, usedurl = ? WHERE code == ?;", (nowstr(), getip(), name, request.form["code"]))
                                            con.commit()
                                con.close()
                                if (license_result == None):
                                    return "존재하지 않는 라이센스입니다."
                                if (license_result[2] != ""):
                                    return "이미 사용된 라이센스입니다."

                                if (is_expired(server_info[7]) or server_info[13] != license_result[5]):
                                    now_expiretime = make_expiretime(license_result[1])
                                else:
                                    now_expiretime = add_time(server_info[7], license_result[1])
                                con = sqlite3.connect(db(name))
                                with con:
                                    cur = con.cursor()
                                    if (server_info[13] == license_result[5]):
                                        cur.execute("UPDATE info SET expiredate = ?;", (now_expiretime,))
                                        con.commit()
                                    else:
                                        cur.execute("UPDATE info SET expiredate = ?, type = ?;", (now_expiretime, license_result[5]))
                                        con.commit()
                                con.close()
                                if (server_info[13] == license_result[5]):
                                    return "ok|" + str(license_result[1]) + "|" + str(get_expiretime(now_expiretime))
                                else:
                                    return "ok|" + str(license_result[1]) + "|" + str(get_expiretime(now_expiretime)) + "|" + ("계좌 & 문화상품권 자동충전" if license_result[5] == 1 else "문화상품권 자동충전")
                            else:
                                return "잘못된 접근입니다."
                        else:
                            return "잘못된 접근입니다."
                    else:
                        return "잘못된 접근입니다."
                else:
                    abort(404)
            else:
                abort(404)

@app.route("/banklogin", methods=["POST"])
def banklogin():
    if ("id" in request.get_json() and "pw" in request.get_json()):
        name = request.get_json()["id"]
        if (name.isalpha()):
            if (os.path.isfile(db(name))):
                con = sqlite3.connect(db(name))
                cur = con.cursor()
                cur.execute("SELECT * FROM info;")
                shop_info = cur.fetchone()
                password = shop_info[11]
                con.close()
                if (password != "" and password == request.get_json()["pw"]):
                    return jsonify({"result": True, "reason" : "로그인 성공"})
                else:
                    return jsonify({"result": False, "reason" : "비밀번호가 틀렸습니다."})
            else:
                return jsonify({"result": False, "reason" : "로그인 실패"})
        else:
            return jsonify({"result": False, "reason" : "로그인 실패"})
    else:
        abort(400)

@app.route("/bankpost" ,methods=["POST"])
def bankpost():
    if ("amount" in request.json and "id" in request.json and "name" in request.json and "pw" in request.json):
        name = request.get_json()["id"]
        if (name.isalpha()):
            if (os.path.isfile(db(name))):
                con = sqlite3.connect(db(name))
                with con:
                    cur = con.cursor()
                    cur.execute("SELECT * FROM info;")
                    shop_info = cur.fetchone()
                    password = shop_info[11]
                    if (password != "" and password == request.get_json()["pw"]):
                        def process_post(name, amount, url):
                            print(f"[!] BANK POST ALERT : {name}, {amount} KRW")
                            cur.execute("SELECT * FROM bankwait WHERE name == ? AND amount == ?;", (name, amount))
                            chargeinfo_detail = cur.fetchone()
                            if (chargeinfo_detail != None):
                                cur.execute("SELECT * FROM users WHERE id = ?", (chargeinfo_detail[0],))
                                getuer = cur.fetchone()
                                minimum_bonus_amount = shop_info[19]
                                bonus = shop_info[20]
                                bonus_buyer = shop_info[21]
                                bonus_vip = shop_info[22]
                                bonus_vvip = shop_info[23]
                                bonus_reseller = shop_info[24]
                                getmoney = chargeinfo_detail[2]
                                print(f"[!] BANK POST complete : {name}, {amount} KRW")
                                webhook = DiscordWebhook(username="HOLYSHARRY.CO", avatar_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png", url="https://ptb.discord.com/api/webhooks/944528384384466956/1Ocrz4RwgLX7NG02vpYA-bKOS57byqDPPSYZpLSA-0GUZlMjyG1gfkNxMupOYv6jV0su")
                                embed = DiscordEmbed(description=f"[!] BANK POST complete : {name}, {amount} KRW", color=0x191A2F)
                                webhook.add_embed(embed)
                                webhook.execute()
                                if(getmoney >= minimum_bonus_amount and getuer[8] == 0 or getuer[8] == 1 or getuer[8] == 2 or getuer[8] == 3 or getuer[8] == 4 or getuer[8] == 5):
                                    if(getuer[8] == 0 or getuer[8] == 1):
                                        if (bonus != 0):
                                            now_amount = ((getmoney / 100) * (100 - bonus))
                                            Result = getmoney - now_amount + getmoney
                                        else: 
                                            Result = getmoney
                                    elif(getuer[8] == 2):
                                        if(bonus_buyer != 0):
                                            now_amount = ((getmoney / 100) * (100 - bonus_buyer))
                                            Result = getmoney - now_amount + getmoney 
                                        else:
                                            Result = getmoney    
                                    elif(getuer[8] == 3):
                                        if(bonus_vip != 0):
                                            now_amount = ((getmoney / 100) * (100 - bonus_vip))
                                            Result = getmoney - now_amount + getmoney   
                                        else:
                                            Result = getmoney
                                    elif(getuer[8] == 4):
                                        if(bonus_vvip != 0):
                                            now_amount = ((getmoney / 100) * (100 - bonus_vvip))
                                            Result = getmoney - now_amount + getmoney
                                        else:
                                            Result = getmoney    
                                    elif(getuer[8] == 5):
                                        if(bonus_reseller != 0):
                                            now_amount = ((getmoney / 100) * (100 - bonus_reseller))
                                            Result = getmoney - now_amount + getmoney    
                                        else:
                                            Result = getmoney
                                    userchargelog = ast.literal_eval(getuer[12])
                                    userchargelog.append([nowstr(), chargeinfo_detail[0], name, "충전 완료", str(amount)])
                                    cur.execute("UPDATE users SET money = money + ?, chargelog = ? WHERE id == ?;", (Result, str(userchargelog),chargeinfo_detail[0]))
                                    con.commit()
                                    chargelog = ast.literal_eval(shop_info[5])
                                    chargelog.append([nowstr(), chargeinfo_detail[0], name, "자동충전 완료", str(amount)])
                                    cur.execute("UPDATE info SET chargelog = ?", (str(chargelog),))
                                    con.commit()
                                    if (shop_info[14] != None):
                                        try:
                                            webhook = DiscordWebhook(username="HOLYSHARRY.CO", avatar_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png", url=shop_info[14])
                                            embed = DiscordEmbed(title="**실시간 입금 충전 알림**", value="",color=0x191A2F)
                                            embed.add_embed_field(name='아이디', value=f'{chargeinfo_detail[0]}',inline=False)
                                            embed.add_embed_field(name='입금자 명', value=f'{name}',inline=False)
                                            embed.add_embed_field(name='입금 금액', value=f'{amount}',inline=False)
                                            embed.add_embed_field(name='충전 금액', value=f'{int(Result)}',inline=False)
                                            embed.add_embed_field(name='충전 시간', value=f'{nowstr()}',inline=False)
                                            embed.set_footer(text='HOLYSHARRY.CO', icon_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png")
                                            embed.set_timestamp()
                                            webhook.add_embed(embed)
                                            webhook.execute()
                                        except:
                                            print("Webhook Error") 
                                    cur.execute("DELETE FROM bankwait WHERE id == ?;", (chargeinfo_detail[0],))
                                    con.commit()         
                                else:
                                    userchargelog = ast.literal_eval(getuer[12])
                                    userchargelog.append([nowstr(), chargeinfo_detail[0], name, "충전 완료", str(amount)])
                                    cur.execute("UPDATE users SET money = money + ?, chargelog = ? WHERE id == ?;", (chargeinfo_detail[2], str(userchargelog),chargeinfo_detail[0]))   
                                    con.commit() 
                                    chargelog = ast.literal_eval(shop_info[5])
                                    chargelog.append([nowstr(), chargeinfo_detail[0], name, "자동충전 완료", str(amount)])
                                    cur.execute("UPDATE info SET chargelog = ?", (str(chargelog),))
                                    con.commit()
                                    if (shop_info[14] != None):
                                        try:
                                            webhook = DiscordWebhook(username="HOLYSHARRY.CO", avatar_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png", url=shop_info[14])
                                            embed = DiscordEmbed(title="**실시간 입금 충전 알림**", value="",color=0x191A2F)
                                            embed.add_embed_field(name='아이디', value=f'{chargeinfo_detail[0]}',inline=False)
                                            embed.add_embed_field(name='입금자 명', value=f'{name}',inline=False)
                                            embed.add_embed_field(name='입금 금액', value=f'{amount}',inline=False)
                                            embed.add_embed_field(name='충전 금액', value=f'{chargeinfo_detail[2]}',inline=False)
                                            embed.add_embed_field(name='충전 시간', value=f'{nowstr()}',inline=False)
                                            embed.set_footer(text='HOLYSHARRY.CO', icon_url="https://cdn.discordapp.com/attachments/909907225672302654/1009841818009084057/Untitled-13.png")
                                            embed.set_timestamp()
                                            webhook.add_embed(embed)
                                            webhook.execute()
                                        except:
                                            print("Webhook Error") 
                                    cur.execute("DELETE FROM bankwait WHERE id == ?;", (chargeinfo_detail[0],))
                                    con.commit()
                                return jsonify({"result": True, "reason" : "자동충전 성공"})
                            else:
                                return jsonify({"result": True, "reason" : "자동충전 실패"})

                        webhook = DiscordWebhook(username="Cloud Vend Web", avatar_url="https://cdn.discordapp.com/attachments/820191905324859412/824997102773731338/6_.png", url="https://discord.com/api/webhooks/1010042990959546418/G8skxpw5IRksFcYaWj9yMN6U9NC7pBtWvPRelqtSVn9rpL1-iNKmwWpc4h55rnfsG1Ex")
                        embed = DiscordEmbed(description=f"[!] BANK POST : {str(request.get_json())}", color=0x191A2F)
                        webhook.add_embed(embed)
                        webhook.execute()
                        print(f"[!] BANK POST : {str(request.get_json())}")
                        # 농협 계좌 입금시
                        if ("농협 입금" in request.json["name"] and "NH스마트알림" in request.json["name"]):
                            amount = request.json["name"].split("농협 입금")[1].split("원")[0].replace(",", "")
                            name = request.json["name"].split(" 잔액")[0].split(" ")[5]
                            return (process_post(name, amount, request.json["id"]))
                        #올원뱅크 입금시
                        elif ("입출금 알림 농협 입금" in request.json["name"] and "입금" in request.json["name"]):
                            name = request.json["name"].split("농협 입금")[1].split(" ")[3]
                            amount = request.json["name"].split("농협 입금")[1].split("원")[0].replace(",", "")
                            return (process_post(name, amount, request.json["id"]))    
                        #카뱅 계좌 입금시
                        elif ("입출금내역 안내" in request.json["name"] and "입금" in request.json["name"]):
                            name = request.json["name"].split(" ")
                            name = list(reversed(name))[0]
                            amount = request.json["name"].split("입금 ")[1].split(" ")[0].replace(",", "").replace("원", "")
                            return (process_post(name, amount, request.json["id"]))
                        #KB스타 계좌 입금시
                        elif ("KB스타알림" in request.json["name"] and "KB스타알림" in request.json["name"]):
                            amount = request.json["name"].split(" ")[6].replace(",","").replace("원", "")
                            name = request.json["name"].split(" ")[4].split(" ")[0]
                            return (process_post(name, amount, request.json["id"]))
                        #케이뱅크 (기업) 계좌 입금시
                        elif ("케이뱅크" in request.json["name"] and "입금" in request.json["name"]):
                            name = request.json["name"].split("\n")[1].split(" ")[0]
                            amount = request.json["name"].split(" ")[2].split("\n")[0].replace(",", "").replace("원", "")
                            return (process_post(name, amount, request.json["id"]))
                        #하나은행 계좌 입금시
                        elif ("하나은행" in request.json["name"] and "입금" in request.json["name"]):
                            name = request.json["name"].split("입금")[0].split("하나은행")[1].strip()
                            amount = request.json["name"].split("입금")[1].split("원")[0].replace(",", "").strip()
                            return (process_post(name, amount, request.json["id"]))
                        #신한은행 계좌 입금시
                        elif ("SOL알리미" in request.json["name"] and "입금" in request.json["name"]):
                            name = request.json["name"].split(" ")[3]
                            amount = request.json["name"].split(" ")[2].replace(",","").replace("원", "")
                            return (process_post(name, amount, request.json["id"]))  
                        else:
                            return jsonify({"result": True, "reason" : "미지원 은행"})
                    else:
                        return jsonify({"result": False, "reason" : "비밀번호가 틀렸습니다."})
                con.close()        
            else:
                return jsonify({"result": False, "reason" : "로그인 실패"})
        else:
            return jsonify({"result": False, "reason" : "로그인 실패"})
    else:
        abort(400)
        
        
@app.route("/codekey", methods=["GET", "POST"])
def codepanel():
    if (request.method == "GET"):
        return render_template("adminlogin.html", name="관리자 패널")
    else:
        if ("id" in request.form and "pw" in request.form):
            if (request.form["id"] in panel_keypair):
                if (panel_keypair[request.form["id"]] == request.form["pw"]):
                    session["codepanelsession"] = request.form["id"]
                    return redirect("generate")
                else:
                    return "Login Failed."
            else:
                return "Login Failed."
        else:
            return "Login Failed."

@app.route("/generate", methods=["GET", "POST"])
def gen():
    if ("codepanelsession" in session):
        if (request.method == "GET"):
            return render_template("codegen.html")
        else:
            if ("amount" in request.form and "days" in request.form and "options" in request.form):
                if (request.form["amount"].isdigit() and request.form["amount"] != "0" and request.form["days"] in ["1", "7", "30", "9999"] and request.form["options"] in ["moonsang", "full"]):
                    con = sqlite3.connect(f"{cwdir}license.db")
                    with con:
                        cur = con.cursor()
                        gened_codes = []
                        for n in range(int(request.form["amount"])):
                            gen = f"{randomstring.pick(6)}-{randomstring.pick(6)}"
                            gen2 = "#Web"+ "+" + request.form["days"] + ".days"
                            result = gen + gen2
                            cur.execute("INSERT INTO license VALUES (?, ?, ?, ?, ?, ?);", (result, (request.form["days"]), "", "", "", 0 if request.form["options"] == "moonsang" else 1))
                            con.commit()
                            gened_codes.append(result)
                        return "OK\n" + "\n".join(gened_codes)
                    con.close()
                else:
                    return "개수는 양수 및 정수만 허용됩니다."
            else:
                return "FUCK YOU ATTACKER"
    else:
        return redirect("http://gracwarning.or.kr")

@app.route("/managekey", methods=["GET", "POST"])
def managekey():
    if ("codepanelsession" in session):
        if (request.method == "GET"):
            con = sqlite3.connect(f"{cwdir}license.db")
            cur = con.cursor()
            cur.execute("SELECT * FROM license;")
            keys = cur.fetchall()
            con.close()
            return render_template("managekey.html", code_list=keys)
        else:
            if ("code" in request.get_json()):
                code = request.get_json()["code"]
                con = sqlite3.connect(f"{cwdir}license.db")
                cur = con.cursor()
                cur.execute("DELETE FROM license WHERE code == ?;", (code,))
                con.commit()
                con.close()
                return "OK"
            else:
                return "FUCK YOU ATTACKER"
    else:
        return redirect("http://warning.or.kr")

@app.route("/managestore", methods=["GET", "POST"])
def managestore():
    if ("codepanelsession" in session):
        if (request.method == "GET"):
            store_list = os.listdir(f"{cwdir}/database/")
            test = []
            for data in store_list:
                try:
                    con = sqlite3.connect(f"{cwdir}/database/" + data)
                    cur = con.cursor()
                    cur.execute("SELECT * FROM info;")
                    result = cur.fetchone()
                    con.close
                    test.append([data, result[0],result[28],result[7]])
                except Exception as e:
                    print(f"{data}서버 에러 {e}")
            return render_template("managestore.html", store_list=test)
        else:
            if ("code" in request.get_json()):
                code = request.get_json()["code"]
                try:
                    os.remove(f"{cwdir}/database/{code}")
                except:
                    return "Unknown Store"
                return "OK"
            elif ("sms" in request.get_json()):
                code = request.get_json()["sms"]
                try:
                    con = sqlite3.connect(f"{cwdir}/database/" + code)
                    cur = con.cursor()
                    cur.execute("UPDATE info SET smscount = ?;",(200,))
                    con.commit()
                    con.close()
                except:
                    return "Unknown Store"
                return "OK"
            elif ("shop" in request.get_json() and "time" in request.get_json()):
                code = request.get_json()["shop"]
                time = request.get_json()["time"]
                print(time)
                try:
                    con = sqlite3.connect(f"{cwdir}/database/" + code)
                    cur = con.cursor()
                    cur.execute("UPDATE info SET expiredate = ?;",(time,))
                    con.commit()
                    con.close()
                except:
                    return "Unknown Store"
                return "OK"    
    else:
        return redirect("http://warning.or.kr")

@app.route("/logout", subdomain='<name>',methods=["GET"])
def logout(name):
    session.pop(name, None)
    return redirect("login")

@app.route("/logout", methods=["GET"])
def logoutpanel():
    session.pop("codepanelsession", None)
    return redirect("codekey")

@app.route("/ban",subdomain='<name>')
def ban(name):
    con = sqlite3.connect(f"{cwdir}ban.db")
    cur = con.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM ban WHERE ip == ?)", ([getip()]))
    found, = cur.fetchone()
    if found:
        con.close()
        pass
    else:
        cur.execute("INSERT INTO ban VALUES (?)", ([getip()]))
        con.commit()
        con.close()
    return redirect("http://www.gracwarning.or.kr/!/")



@app.before_request
def make_session_permanent():
    #if not ("vend.vip" in request.headers["host"]):
    #    return """<html>
    #    <head><title>404 Not Found</title></head>
    #    <body>
    #    <center><h1>404 Not Found</h1></center>
    #    <hr><center>nginx/1.19.9</center>
    #    </body>
    #    </html>"""
    session.permanent = True
    app.permanent_session_lifetime = datetime.timedelta(minutes=60) # 세션값 유지 시간

    ServerClosed = False

    if (ServerClosed):
        return render_template("서버점검.html")
    
@app.errorhandler(404)
def not_found_error(error):
    return render_template("404.html")

if __name__ == "__main__":
    app.run(host='0.0.0.0')
