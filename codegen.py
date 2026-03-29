import sqlite3, randomstring, os
cwdir =  os.path.dirname(__file__) + "/"
count = 1
ex = int(input('생성 기간 : '))
number = int(input('생성 개수 : '))
os.system('cls')
while True:
    con = sqlite3.connect(f"{cwdir}license.db")
    cur = con.cursor()
    gen = f"{randomstring.pick(6)}-{randomstring.pick(6)}"
    gen2 = "#Web"+ "+" + str(ex) + ".days"
    result = gen + gen2
    cur.execute("INSERT INTO license VALUES (?, ?, ?, ?, ?, ?);", (result, str(ex), "", "", "", 1 ))
    con.commit()
    con.close()
    print(result)
    if number == count:
        os.system("PAUSE")
        break
    count = count + 1 