import os
import json
import torch
import pymysql

from functools import wraps
from flask import Flask,request,jsonify,render_template,redirect,session
from flask_bcrypt import Bcrypt

from preprocess2 import preprocess_lstm
from models.model2 import LSTMClassifier


# =========================
# 基础配置
# =========================

app = Flask(__name__)
app.secret_key="your_secret_key"

UPLOAD_FOLDER="uploads"
os.makedirs(UPLOAD_FOLDER,exist_ok=True)

bcrypt=Bcrypt(app)

THRESHOLD=0.3


# =========================
# 模型
# =========================

model=LSTMClassifier(
    input_dim=4,
    hidden_dim=64
)

model.load_state_dict(
 torch.load(
  r"D:/Projects/Python/demo/models/lstm_model.pth",
  map_location="cpu"
 )
)

model.eval()


# =========================
# DB
# =========================

def get_db():
    return pymysql.connect(
        host="localhost",
        user="root",
        passwd="feng1234567",
        database="demo",
        charset="utf8"
    )


# =========================
# 登录保护装饰器
# =========================

def login_required(f):

    @wraps(f)
    def wrapper(*args,**kwargs):

        if "user" not in session:
            return redirect("/login_page")

        return f(*args,**kwargs)

    return wrapper


# =========================
# 登录注册
# =========================

@app.route("/")
@login_required
def index():
    if "user" not in session:
        return redirect("/login_page")
    return render_template("index.html")


@app.route("/login_page")
def login_page():
    if "user" in session:
        return redirect("/")
    return render_template("login.html")

@app.route("/register_page")
def register_page():
    return render_template("register.html")

@app.route("/register",methods=["POST"])
def register():

    data=request.json

    username=data["username"]
    password=data["password"]

    pw_hash=bcrypt.generate_password_hash(
        password
    ).decode()

    db=get_db()
    c=db.cursor()

    try:
        c.execute("""
        insert into users(
          username,
          password_hash
        )
        values(%s,%s)
        """,(username,pw_hash))

        db.commit()

        return jsonify(
            msg="注册成功"
        )

    except Exception as e:

        return jsonify(
            msg="用户已存在",
            error=str(e)
        ),400

    finally:
        c.close()
        db.close()



@app.route("/login",methods=["POST"])
def login():

    data=request.json

    user=data["username"]
    password=data["password"]

    db=get_db()
    c=db.cursor()

    c.execute(
      "select password_hash from users where username=%s",
      (user,)
    )

    row=c.fetchone()

    c.close()
    db.close()

    if not row:
        return jsonify(msg="用户不存在"),400


    if bcrypt.check_password_hash(
        row[0],
        password
    ):
        session["user"]=user

        return jsonify(
            msg="登录成功",
            redirect="/"
        )

    return jsonify(
      msg="密码错误"
    ),400



@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login_page")



# =========================
# 检测存储核心
# =========================

def detect_and_store(
    file_path,
    system_name
):

    db=get_db()
    c=db.cursor()

    X,y,raw_X,_=preprocess_lstm(
        file_path
    )

    user_dict={}

    # 推理
    for i,seq in enumerate(X):

        prob=float(
          model(
            torch.tensor(
              seq
            ).unsqueeze(0)
          ).item()
        )

        user=raw_X[i][-1]["user"]

        user_dict.setdefault(
            user,
            []
        ).append(
            {
             "seq_id":i,
             "prob":prob,
             "raw_seq":raw_X[i]
            }
        )


    seen=set()


    # windows + logs
    for user,seqs in user_dict.items():

        for s in seqs:

            p=s["prob"]

            c.execute("""
            insert into windows(
             system_name,
             seq_id,
             user,
             start_time,
             end_time,
             prob,
             risk_level,
             raw_seq
            )
            values(
             %s,%s,%s,%s,%s,%s,%s,%s
            )
            """,(
             system_name,
             s["seq_id"],
             user,
             s["raw_seq"][0]["timestamp"],
             s["raw_seq"][-1]["timestamp"],
             p,
             "high" if p>.7 else
             "medium" if p>.4 else
             "low",
             json.dumps(
                 s["raw_seq"],
                 default=str
             )
            ))


            for log in s["raw_seq"]:

                key=(
                    system_name,
                    log["user"],
                    log["timestamp"],
                    log["ip"]
                )

                if key in seen:
                    continue

                seen.add(key)

                c.execute("""
                insert into logs(
                 system_name,
                 user,
                 timestamp,
                 ip,
                 status,
                 prob,
                 seq_id
                )
                values(
                %s,%s,%s,%s,%s,%s,%s
                )
                """,(
                 system_name,
                 log["user"],
                 log["timestamp"],
                 log["ip"],
                 log["status"],
                 p,
                 s["seq_id"]
                ))



    # alerts聚合
    for user,seqs in user_dict.items():

        attacks=[
          x for x in seqs
          if x["prob"]>THRESHOLD
        ]

        if not attacks:
            continue


        c.execute("""
        insert into alerts(
         system_name,
         user,
         time,
         attack_count,
         max_prob,
         status
        )
        values(
         %s,%s,%s,%s,%s,%s
        )
        """,(
         system_name,
         user,
         attacks[-1]["raw_seq"][-1]["timestamp"],
         len(attacks),
         max(
          x["prob"] for x in attacks
         ),
         "pending"
        ))

    db.commit()

    c.close()
    db.close()



# =========================
# 当前用户系统列表
# =========================

@app.route("/my_systems")
@login_required
def my_systems():

    db=get_db()
    c=db.cursor()

    c.execute("""
    select system_name
    from systems
    where user=%s
    """,(session["user"],))

    rows=c.fetchall()

    c.close()
    db.close()

    return jsonify([
        x[0]
        for x in rows
    ])



# =========================
# Alerts
# =========================

@app.route("/alerts")
@login_required
def alerts():

    db = get_db()
    cursor = db.cursor()

    try:
        page = int(request.args.get("page", 1))
        page_size = 10
        offset = (page - 1) * page_size
        system = request.args.get("system")

        cursor.execute("""
            SELECT user, time, attack_count, max_prob, status
            FROM alerts
            WHERE system_name=%s
            ORDER BY time
            LIMIT %s OFFSET %s
        """, (system, page_size, offset))

        results = cursor.fetchall()

        data = []

        for r in results:
            user = r[0]

            cursor2 = db.cursor()

            cursor2.execute("""
                SELECT seq_id, prob
                FROM windows
                WHERE user=%s AND system_name=%s
                ORDER BY seq_id
            """, (user, system))

            timeline = []
            for row in cursor2.fetchall():
                timeline.append({
                    "seq_id": row[0],
                    "prob": float(row[1])
                })

            cursor2.close()

            data.append({
                "user": user,
                "time": str(r[1]),
                "attack_count": r[2],
                "max_prob": float(r[3]),
                "timeline": timeline,
                "status": r[4]
            })

        return jsonify({"data": data})

    finally:
        cursor.close()
        db.close()

@app.route("/window_detail")
def window_detail():
    seq_id = request.args.get("seq_id")
    system = request.args.get("system")
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(""" 
        SELECT prob, raw_seq 
        FROM windows 
        WHERE seq_id=%s 
        AND system_name=%s 
        """,(seq_id, system))
        row = cursor.fetchone()
        return jsonify({
            "prob": float(row[0]), "seq": json.loads(row[1]) })
    finally:
        cursor.close()
        db.close()

@app.route("/trend")
def trend():
    db = get_db()
    cursor = db.cursor()
    system = request.args.get("system")
    sql = """ 
    SELECT DATE_FORMAT(timestamp, '%%Y-%%m-%%d %%H:%%i') as t, COUNT(*) 
    FROM logs 
    WHERE system_name=%s 
    GROUP BY t 
    ORDER BY t """
    cursor.execute(sql, system)
    results = cursor.fetchall()
    cursor.close()
    db.close()
    times = [r[0] for r in results]
    counts = [r[1] for r in results]
    return jsonify({ "times": times, "counts": counts })

@app.route("/rank")
@login_required
def rank():

    system=request.args.get("system")

    db=get_db()
    c=db.cursor()

    c.execute("""
    select user,max_prob
    from alerts
    where system_name=%s
    order by max_prob desc
    limit 10
    """,(system,))

    rows=c.fetchall()

    c.close()
    db.close()

    return jsonify([
      {
       "user":r[0],
       "risk":float(r[1])
      }
      for r in rows
    ])



# =========================
# 系统管理
# =========================

@app.route("/system_manage")
@login_required
def system_manage():

    return render_template(
      "system_manage.html"
    )



@app.route(
"/add_system",
methods=["POST"]
)
@login_required
def add_system():

    f=request.files["file"]

    system_name=request.form["name"]

    owner=session["user"]

    path=os.path.join(
        UPLOAD_FOLDER,
        f.filename
    )

    f.save(path)

    db=get_db()
    c=db.cursor()

    c.execute("""
    insert into systems(
      system_name,
      log_file,
      status,
      owner
    )
    values(
     %s,%s,%s,%s
    )
    """,(
     system_name,
     f.filename,
     "online",
     owner
    ))

    db.commit()

    c.close()
    db.close()


    detect_and_store(
       path,
       system_name
    )

    return jsonify(
      msg="接入成功"
    )



@app.route(
"/delete_system/<id>"
)
@login_required
def delete_system(id):

    db=get_db()
    c=db.cursor()

    c.execute(
      "delete from systems where id=%s",
      (id,)
    )

    db.commit()

    c.close()
    db.close()

    return jsonify(
      msg="删除成功"
    )
@app.route("/systems")
def get_systems():

    if "user" not in session:
        return jsonify([])

    db=get_db()
    cursor=db.cursor()

    cursor.execute("""
    SELECT system_name
    FROM systems
    WHERE owner=%s
    """,(session["user"],))

    rows=cursor.fetchall()

    cursor.close()
    db.close()

    return jsonify([
        {"system_name":r[0]}
        for r in rows
    ])

@app.route("/systems_manage_data")
def systems_manage_data():

    if "user" not in session:
        return jsonify([])

    db=get_db()
    cursor=db.cursor()

    cursor.execute("""
    SELECT id,system_name,log_file,status
    FROM systems
    WHERE owner=%s
    """,(session["user"],))

    rows=cursor.fetchall()

    cursor.close()
    db.close()

    return jsonify([
        {
          "id":r[0],
          "system_name":r[1],
          "log_file":r[2],
          "status":r[3]
        }
        for r in rows
    ])
@app.route("/kpi")
def kpi():

    system = request.args.get("system")
    db = get_db()
    cursor = db.cursor()

    # 活跃告警
    cursor.execute("""
        SELECT COUNT(*)
        FROM alerts
        WHERE system_name=%s AND status='pending'
    """, (system,))
    alerts = cursor.fetchone()[0]

    # 高风险用户
    cursor.execute("""
        SELECT COUNT(DISTINCT user)
        FROM alerts
        WHERE system_name=%s AND max_prob > 0.7
    """, (system,))
    high_risk_users = cursor.fetchone()[0]

    # 攻击窗口
    cursor.execute("""
        SELECT COUNT(*)
        FROM windows
        WHERE system_name=%s
    """, (system,))
    windows = cursor.fetchone()[0]

    cursor.close()
    db.close()

    return jsonify({
        "alerts": alerts,
        "users": high_risk_users,
        "windows": windows
    })
@app.route("/set_threshold", methods=["POST"])
def set_threshold():
    global THRESHOLD
    data=request.json
    THRESHOLD=float(data["threshold"])
    system_name=data["system"]
    # 从systems表取该系统日志路径
    db=get_db()
    cursor=db.cursor()
    cursor.execute( "DELETE FROM alerts WHERE system_name=%s", (system_name,) )
    cursor.execute( "DELETE FROM logs WHERE system_name=%s", (system_name,) )
    cursor.execute( "DELETE FROM windows WHERE system_name=%s", (system_name,) )
    db.commit()
    try:
        cursor.execute(""" 
        SELECT log_file 
        FROM systems 
        WHERE system_name=%s """,(system_name,))
        row=cursor.fetchone()
        if not row:
            return jsonify({ "msg":"system not found" }),404
        log_file=row[0]
        path = "uploads/"+log_file
        detect_and_store(
            path,
            system_name
        )
        return jsonify({
            "msg":"threshold updated"
        })
    finally:
        cursor.close()
        db.close()
@app.route("/update_status", methods=["POST"])
def update_status():
    db = get_db()
    cursor = db.cursor()
    user = request.json["user"]
    status = request.json["status"]
    system = request.json["system"]
    sql = "UPDATE alerts SET status=%s WHERE user=%s AND system_name=%s"
    cursor.execute(sql, (status, user, system))
    db.commit()
    cursor.close()
    db.close()
    return jsonify({"msg": "ok"})
# =========================
# 用户详情页面
# =========================
@app.route("/user/<username>")
def user_detail(username):
    return render_template("user_detail.html", user_id=username)
# =========================
# 用户数据（稳定版）
# =========================
@app.route("/user_data")
def user_data():

    system = request.args.get("system")
    username = request.args.get("username")

    if not system or not username:
        return jsonify({
            "error": "missing system or username"
        }), 400

    db = get_db()
    cursor = db.cursor()

    # =========================
    # 窗口数据
    # =========================
    cursor.execute("""
        SELECT seq_id, prob, start_time, end_time
        FROM windows
        WHERE user=%s AND system_name=%s
        ORDER BY seq_id
    """, (username, system))

    windows = cursor.fetchall()

    window_list = []
    probs = []

    for w in windows:
        window_list.append({
            "seq_id": w[0],
            "prob": float(w[1]),
            "start": str(w[2]),
            "end": str(w[3])
        })
        probs.append(float(w[1]))

    # =========================
    # KPI统计
    # =========================
    attack_count = len(probs)
    max_prob = max(probs) if probs else 0

    if max_prob > 0.7:
        risk_level = "high"
    elif max_prob > 0.4:
        risk_level = "medium"
    else:
        risk_level = "low"

    # =========================
    # IP统计
    # =========================
    cursor.execute("""
        SELECT ip, COUNT(*) as c
        FROM logs
        WHERE user=%s AND system_name=%s
        GROUP BY ip
        ORDER BY c DESC
        LIMIT 5
    """, (username, system))

    ips = cursor.fetchall()

    ip_list = [{
        "ip": i[0],
        "count": i[1]
    } for i in ips]

    cursor.close()
    db.close()

    return jsonify({
        "windows": window_list,
        "summary": {
            "attack_count": attack_count,
            "max_prob": max_prob,
            "risk_level": risk_level
        },
        "ips": ip_list
    })

    # =========================
    # 4. 返回统一结构
    # =========================
    return jsonify({
        "summary": {
            "attack_count": attack_count,
            "max_prob": max_prob,
            "risk_level": risk_level
        },
        "windows": window_list,
        "ips": ip_list
    })
@app.route("/find_user_page")
@login_required
def find_user_page():

    db = get_db()
    cursor = db.cursor()

    try:
        system = request.args.get("system")
        user = request.args.get("user")

        page_size = 10

        """
        找当前用户在该系统告警列表中的排名位置
        （按 alerts 查询默认顺序）
        """

        # 先拿当前用户时间（假设按time排序更合理）
        cursor.execute("""
            SELECT time
            FROM alerts
            WHERE user=%s AND system_name=%s
            LIMIT 1
        """,(user,system))

        result = cursor.fetchone()

        if not result:
            return jsonify({"page":1})

        user_time = result[0]


        # 统计它前面有多少条
        cursor.execute("""
            SELECT COUNT(*)
            FROM alerts
            WHERE system_name=%s
            AND time <= %s
        """,(system,user_time))

        position = cursor.fetchone()[0]

        page = (position-1)//page_size + 1

        return jsonify({
            "page":page
        })

    finally:
        cursor.close()
        db.close()
if __name__=="__main__":
    app.run(
      debug=True
    )