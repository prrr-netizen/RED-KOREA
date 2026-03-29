import websocket, json, os
from websocket._exceptions import WebSocketConnectionClosedException
from flask import Flask, render_template, request, session, redirect,jsonify
import sqlite3 , ast , datetime
from discord_webhook import DiscordWebhook, DiscordEmbed

app = Flask(__name__)
cwdir =  os.path.dirname(__file__) + "/"

def db(name):
        return cwdir + "database/" + name + ".db"
def nowstr():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M')    

@app.route("/api", methods=["POST"])
def bankpost():
    if ("bankpin" in request.json and "bankname" in request.json and "userid" in request.json and "shopname" in request.json and "amount" in request.json and "time" in request.json):
        shopname = request.get_json()["shopname"]
        if (os.path.isfile(db(shopname))):
            con = sqlite3.connect(db(shopname))
            with con:
                cur = con.cursor()
                cur.execute("SELECT * FROM info;")
                shop_info = cur.fetchone()
                password = shop_info[11]
                if (password != "" and password == request.get_json()["bankpin"]):
                    def process_post(name, amount,shopname,title,body,notification_id):
                        con2 = sqlite3.connect("push.db")
                        cur2 = con2.cursor()
                        cur2.execute("UPDATE getresult SET result = ? WHERE notification_id == ?", (1,notification_id))
                        con2.commit()
                        con2.close()       
                        webhook = DiscordWebhook(username="Cloud Vend Web", avatar_url="https://cdn.discordapp.com/attachments/820191905324859412/824997102773731338/6_.png", url=os.environ.get("DISCORD_WEBHOOK_URL", ""))
                        embed = DiscordEmbed(description=f"[!] BANK POST  : 서브 도메인 : {shopname} \n앱 타이틀 : {title} 앱 내용 : {body} \n입금자명 : {name}, 입금 금액 : {amount} KRW", color=0x191A2F)
                        webhook.add_embed(embed)
                        webhook.execute()
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
                            webhook = DiscordWebhook(username="Cloud Vend Web", avatar_url="https://cdn.discordapp.com/attachments/820191905324859412/824997102773731338/6_.png", url=os.environ.get("DISCORD_WEBHOOK_URL", ""))
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
                                        webhook = DiscordWebhook(username="E X O D U X", avatar_url="https://cdn.discordapp.com/attachments/920964201781018624/985126636280217620/Comp_10.png", url=shop_info[14])
                                        embed = DiscordEmbed(title="**실시간 입금 충전 알림**", value="",color=0x191A2F)
                                        embed.add_embed_field(name='아이디', value=f'{chargeinfo_detail[0]}',inline=False)
                                        embed.add_embed_field(name='입금자 명', value=f'{name}',inline=False)
                                        embed.add_embed_field(name='입금 금액', value=f'{amount}',inline=False)
                                        embed.add_embed_field(name='충전 금액', value=f'{Result}',inline=False)
                                        embed.add_embed_field(name='충전 시간', value=f'{nowstr()}',inline=False)
                                        embed.set_footer(text='E X O D U X', icon_url="https://cdn.discordapp.com/attachments/920964201781018624/985126636280217620/Comp_10.png")
                                        embed.set_timestamp()
                                        webhook.add_embed(embed)
                                        webhook.execute()
                                    except:
                                        print("Webhook Error")   
                                cur.execute("DELETE FROM bankwait WHERE name == ?;", (name,))
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
                                        webhook = DiscordWebhook(username="E X O D U X", avatar_url="https://cdn.discordapp.com/attachments/920964201781018624/985126636280217620/Comp_10.png", url=shop_info[14])
                                        embed = DiscordEmbed(title="**실시간 입금 충전 알림**", value="",color=0x191A2F)
                                        embed.add_embed_field(name='아이디', value=f'{chargeinfo_detail[0]}',inline=False)
                                        embed.add_embed_field(name='입금자 명', value=f'{name}',inline=False)
                                        embed.add_embed_field(name='입금 금액', value=f'{amount}',inline=False)
                                        embed.add_embed_field(name='충전 금액', value=f'{Result}',inline=False)
                                        embed.add_embed_field(name='충전 시간', value=f'{nowstr()}',inline=False)
                                        embed.set_footer(text='E X O D U X', icon_url="https://cdn.discordapp.com/attachments/920964201781018624/985126636280217620/Comp_10.png")
                                        embed.set_timestamp()
                                        webhook.add_embed(embed)
                                        webhook.execute()
                                    except:
                                        print("Webhook Error")   
                                cur.execute("DELETE FROM bankwait WHERE name == ?;", (name,))
                                con.commit()      
                            return {"result": True, "reason" : "자동충전 성공"}
                                
                    def on_message(ws, message):
                        try:
                            obj = json.loads(message)
                            if obj["type"] == "push":
                                push = obj["push"]
                                title = push["title"].replace("\n"," ")
                                body = push["body"].replace("\n"," ")
                                NotificationApplicationName = str(push["package_name"])
                                if NotificationApplicationName == "com.kakaobank.channel":
                                    displayname = body.split(" ")[5].split(" ")[0]
                                    count = body.split("입금 ")[1].split(" ")[0].replace(",", "").replace("원", "")
                                    money = int(count)
                                    if ("입금" in body):
                                        cur.execute("SELECT * FROM bankwait WHERE name == ? AND amount == ?;", (displayname, money))
                                        chargeinfo_detail = cur.fetchone()
                                        if ("입금" in body and chargeinfo_detail != None):
                                            ws.close()
                                            con2 = sqlite3.connect("push.db")
                                            cur2 = con2.cursor()
                                            cur2.execute("SELECT * FROM getresult WHERE notification_id == ?", (push["notification_id"],))
                                            result1 = cur2.fetchone()
                                            if(result1 == None):
                                                cur2.execute("INSERT OR IGNORE INTO getresult VALUES(?, ?, ?, ?, ? ,? ,?);", (displayname,money,shopname,title,body,push["notification_id"],0))
                                                con2.commit()
                                            cur2.execute("SELECT * FROM getresult WHERE notification_id == ?", (push["notification_id"],))
                                            result2 = cur2.fetchone()
                                            if(result2 != None and result2[6] == 0):
                                                return (process_post(result2[0], result2[1],result2[2],result2[3],result2[4],result2[5]))  
                                            con2.close()
                                elif NotificationApplicationName == "viva.republica.toss":
                                    displayname = body.split("님")[0].split(" ")[0]
                                    count = title.split("원")[0].replace(",","").replace("원", "")
                                    money = int(count)
                                    if ("→" in body): 
                                        cur.execute("SELECT * FROM bankwait WHERE name == ? AND amount == ?;", (displayname, money))
                                        chargeinfo_detail = cur.fetchone()
                                        if ("→" in body and chargeinfo_detail != None):
                                            ws.close()
                                            con2 = sqlite3.connect("push.db")
                                            cur2 = con2.cursor()
                                            cur2.execute("SELECT * FROM getresult WHERE notification_id == ?", (push["notification_id"],))
                                            result1 = cur2.fetchone()
                                            if(result1 == None):
                                                cur2.execute("INSERT OR IGNORE INTO getresult VALUES(?, ?, ?, ?, ? ,? ,?);", (displayname,money,shopname,title,body,push["notification_id"],0))
                                                con2.commit()
                                            cur2.execute("SELECT * FROM getresult WHERE notification_id == ?", (push["notification_id"],))
                                            result2 = cur2.fetchone()
                                            if(result2 != None and result2[6] == 0):
                                                return (process_post(result2[0], result2[1],result2[2],result2[3],result2[4],result2[5]))  
                                            con2.close()
                                else:
                                    return {"result": False, "reason" : "not found NotificationApplicationName"}
                        except Exception as e:
                            print(f"BankAPI[ERROR]: {e}")
                    def on_error(ws, error):
                        return {"result": False, "reason" : error}  
                    websocket.enableTrace(True)
                    ws = websocket.WebSocketApp("wss://stream.pushbullet.com/websocket/"+password,on_message = on_message,on_error=on_error)
                    ws.run_forever()                      
                else:
                    return {"reason": "Error"}            
            con.close()
        else:
            return {"reason": "Error"}                   
    else:
        return {"reason": "Error"} 
    return {"result": True, "reason" : "Charge Done"}                          
                             
app.run("0.0.0.0", port=4040)