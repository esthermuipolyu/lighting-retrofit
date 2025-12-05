from flask import Flask, render_template_string, request, redirect, flash, send_from_directory
import sqlite3, os, json
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "campus2025"
os.makedirs("static/uploads", exist_ok=True)

# 初始數據
data = [("2024-12-01",3246),("2025-01-01",2145),("2025-02-01",1631),
        ("2025-03-01",2016),("2025-04-01",1883),("2025-05-01",1112),
        ("2025-06-01",2295),("2025-07-01",2153),("2025-08-01",1480),
        ("2025-09-01",811),("2025-10-01",1939)]
goals = {"2026-06-30":31500,"2027-06-30":58500,"2028-06-30":76500,"2029-06-30":90000}

def init():
    c = sqlite3.connect("data.db").cursor()
    c.execute("CREATE TABLE IF NOT EXISTS r(id INTEGER PRIMARY KEY,date TEXT,qty INTEGER,img TEXT)")
    if c.execute("SELECT COUNT(*) FROM r").fetchone()[0]==0:
        c.executemany("INSERT INTO r(date,qty,img)VALUES(?,?,?)",( (d,q,"") for d,q in data))
    c.connection.commit()

def total():
    c = sqlite3.connect("data.db").cursor()
    c.execute("SELECT date,qty FROM r ORDER BY date")
    rows = c.fetchall()
    dates = [r[0][:7] for r in rows]
    monthly = [r[1] for r in rows]
    t = sum(monthly)
    cum = []; s=0
    for q in monthly: s+=q; cum.append(s)
    return t, dates, monthly, cum

def days_left(tgt):
    c = sqlite3.connect("data.db").cursor()
    c.execute("SELECT date,qty FROM r ORDER BY date DESC LIMIT 30")
    r = c.fetchall()
    if len(r)<2: return None
    try:
        days = (datetime.strptime(r[0][0][:10],"%Y-%m-%d") - datetime.strptime(r[-1][0][:10],"%Y-%m-%d")).days + 1
        return max(1,int((tgt-total()[0])/(sum(q for _,q in r)/days))))
    except: return None

BASE = """<!DOCTYPE html><html lang="zh-HK"><head><meta charset="UTF-8"><title>Lighting Retrofit</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>body{font-family:"Microsoft JhengHei";padding-top:80px;background:#f8f9fa;}
.progress{height:40px;}.progress-bar{font-size:1.3rem;font-weight:bold;}</style></head><body>
<nav class="navbar navbar-dark bg-dark fixed-top"><div class="container-fluid">
<a class="navbar-brand" href="/">Lighting Retrofit 即時進度</a>
<span class="navbar-text text-white"><a href="/up" class="text-white">上載</a> | <a href="/hist" class="text-white">歷史</a></span>
</div></nav><div class="container">%BODY%</div></body></html>"""

@app.route("/")
def home():
    init(); t,d,m,c=total()
    cards=""
    for deadline,goal in goals.items():
        remain=max(0,goal-t); day=days_left(goal); txt=f"（約 {day} 日）" if day else "（數據不足）"
        pct=min(100,t/goal*100); col="bg-success" if t>=goal else "bg-warning text-dark"
        cards+=f'<div class="card mb-3 shadow"><div class="card-body"><h5>{deadline} 目標 {goal:,} 支</h5><div class="progress"><div class="progress-bar {col}" style="width:{pct:.1f}%">{pct:.1f}%</div></div><div class="row text-center mt-3"><div class="col"><h4 class="text-primary">{t:,}</h4>已完成</div><div class="col"><h4 class="text-danger">{remain:,}</h4>尚餘</div><div class="col"><h5 class="text-success">{txt}</h5>預計</div></div></div></div>'
    body=f'<div class="text-center my-5"><h1 class="display-5 text-secondary">目前累積</h1><h1 class="display-1 text-primary fw-bold">{t:,}</h1><p class="lead">支燈管</p></div><div class="row"><div class="col-lg-8"><canvas id="c"></canvas></div><div class="col-lg-4"><h3>階段目標</h3>{cards}</div></div><script>new Chart("c",{{type:"bar",data:{{labels:{json.dumps(d)},datasets:[{{label:"每月",data:{json.dumps(m)},backgroundColor:"#0d6efd"}},{{label:"累積",type:"line",data:{json.dumps(c)},borderColor:"#dc3545",yAxisID:"y1"}}]}},options:{{responsive:true,scales:{{y:{{beginAtZero:true}},y1:{{position:"right",beginAtZero:true}}}}}}}});</script>'
    return render_template_string(BASE.replace("%BODY%",body))

@app.route("/up",methods=["GET","POST"])
def up():
    if request.method=="POST":
        if request.form.get("p")!="campus2025": flash("密碼錯","danger"); return redirect("/up")
        date=request.form["date"]; qty=int(request.form.get("qty","0")or"0")
        f=request.files.get("image")
        fn=""
        if f and f.filename:
            fn=datetime.now().strftime("%Y%m%d_%H%M%S_")+secure_filename(f.filename)
            f.save("static/uploads/"+fn)
        sqlite3.connect("data.db").execute("INSERT INTO r(date,qty,img)VALUES(?,?,?)",(date,qty,fn)).connection.commit()
        flash("上載成功","success"); return redirect("/")
    body='''<h2>上載每日數據</h2><form method="post" enctype="multipart/form-data">
    <input type="password" name="p" class="form-control mb-3" placeholder="密碼: campus2025" required>
    <input type="date" name="date" class="form-control mb-3" value="'''+datetime.now().strftime("%Y-%m-%d")+'''" required>
    <input type="file" name="image" class="form-control mb-3">
    <input type="number" name="qty" class="form-control mb-3" placeholder="或手動輸入數量">
    <button class="btn btn-success btn-lg">儲存</button></form>'''
    return render_template_string(BASE.replace("%BODY%",body))

@app.route("/hist")
def hist():
    rows=sqlite3.connect("data.db").execute("SELECT id,date,qty,img FROM r ORDER BY date DESC").fetchall()
    tbl="".join(f"<tr><td>{d[:10]}</td><td>{q}</td><td>{f'<img src=\"/static/uploads/{i}\" width=\"100\">'if i else'無'}</td><td><a href=\"/del/{id}\" class=\"btn btn-danger btn-sm\" onclick=\"return confirm('確定？')\">刪除</a></td></tr>" for id,d,q,i in rows)
    return render_template_string(BASE.replace("%BODY%",f"<h2>歷史記錄</h2><table class='table table-striped'><thead class='table-dark'><tr><th>日期</th><th>數量</th><th>相片</th><th></th></tr></thead><tbody>{tbl}</tbody></table>"))

@app.route("/del/<int:i>")
def dele(i):
    img=sqlite3.connect("data.db").execute("SELECT img FROM r WHERE id=?",(i,)).fetchone()
    if img and img[0]: os.remove("static/uploads/"+img[0])
    sqlite3.connect("data.db").execute("DELETE FROM r WHERE id=?",(i,)).connection.commit()
    return redirect("/hist")

@app.route('/static/uploads/<f>')
def img(f): return send_from_directory('static/uploads',f)

if __name__=="__main__":
    init()
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",3000)))
