from flask import Flask, redirect
from flask import send_file, request, redirect
import re
from flask import g
import pandas as pd
import requests
import datetime
import sqlite3
import random
import os
import math

from flask_babel import Babel
from flask import Flask, render_template_string, current_app, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_security import (
    Security,
    SQLAlchemyUserDatastore,
    auth_required,
    hash_password,
    current_user,
    RegisterForm,
)
from flask_security.models import fsqla_v3 as fsqla
from wtforms import StringField, IntegerField, SelectField, widgets
from wtforms.validators import DataRequired
from wtforms.widgets import NumberInput
from datetime import datetime


DATABASE = (
    "prod-points.sqlite" if os.path.exists("prod-points.sqlite") else "points.sqlite"
)

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


# Create app
app = Flask(__name__)

### Define user management ###

app.config["DEBUG"] = True
# generated using: secrets.token_urlsafe()
app.config["SECRET_KEY"] = "pf9Wkove4IKEAXvy-cQkeDPhv9Cb3Ag-wyJILbq_dFw" # TODO from environ
app.config["SECURITY_PASSWORD_HASH"] = "argon2"
# argon2 uses double hashing by default - so provide key.
# For python3: secrets.SystemRandom().getrandbits(128)
app.config["SECURITY_PASSWORD_SALT"] = "146585145368132386173505678016728509634" # TODO from environ

# Take password complexity seriously
app.config["SECURITY_PASSWORD_COMPLEXITY_CHECKER"] = "zxcvbn"

# Allow registration of new users without confirmation
app.config["SECURITY_REGISTERABLE"] = True
app.config["SECURITY_SEND_REGISTER_EMAIL"] = False
app.config["SECURITY_CONFIRMABLE"] = False

app.config["SECURITY_USERNAME_ENABLE"] = True
app.config["SECURITY_USERNAME_REQUIRED"] = True
app.config["SECURITY_USERNAME_MIN_LENGTH"] = 1
app.config["SECURITY_USERNAME_MAX_LENGTH"] = 32

app.config["SECURITY_POST_REGISTER_VIEW"] = "/login"

app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///../{DATABASE}" # relative to /instance directory
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# As of Flask-SQLAlchemy 2.4.0 it is easy to pass in options directly to the
# underlying engine. This option makes sure that DB connections from the pool
# are still valid. Important for entire application since many DBaaS options
# automatically close idle connections.
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}

### Initiate user management ###
db = SQLAlchemy(app)
fsqla.FsModels.set_db_info(db)

class Role(db.Model, fsqla.FsRoleMixin):
    pass

class User(db.Model, fsqla.FsUserMixin):
    gender = db.Column(db.String(255))
    year_of_birth = db.Column(db.Integer)

class ExtendedRegisterForm(RegisterForm):
    gender = SelectField('Gender', choices=[('-', 'Prefer not to say'), ('f', 'Female'), ('m', 'Male'), ('d', 'Other')])
    year_of_birth = IntegerField('Year of Birth', widget=NumberInput(min=1900, max=datetime.now().year))


user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore, register_form=ExtendedRegisterForm)

### One time setup for user management ###

with app.app_context():
    # create necessary sql tables
    security.datastore.db.create_all()
    # deine roles - not really needed
    security.datastore.find_or_create_role(
        name="admin",
        permissions={"admin-read", "admin-write", "user-read", "user-write"},
    )
    security.datastore.find_or_create_role(
        name="monitor", permissions={"admin-read", "user-read"}
    )
    security.datastore.find_or_create_role(
        name="user", permissions={"user-read", "user-write"}
    )
    security.datastore.find_or_create_role(name="reader", permissions={"user-read"})
    security.datastore.db.session.commit()


### Endpoints related to user management ###

@app.route("/get_user", methods=["GET"])
def get_user():
    print("Received request to get user.")
    # Check if the user is logged in
    if not current_user.is_anonymous:
        return jsonify({"logged_in": True, "username": current_user.username})
    else:
        return jsonify({"logged_in": False, "username": ""})


@app.route("/user", methods=["GET"])
def user():
    if current_user.is_anonymous:
        return "You are not logged in."
    
    result = f"""
<b>Logged in as:</b><br>
Username: {current_user.username}<br>
Email: {current_user.email}<br>
Gender: {current_user.gender}<br>
Year of Birth: {current_user.year_of_birth}<br><br>
<a href="/#user:{current_user.username}">See my Spots</a><br><br>
<a href="/logout">Logout</a><br><br>
<a href="/">Back to Map</a>
"""
    return result

@app.route('/is_username_used/<username>', methods=['GET'])
def is_username_used(username):
    print(f"Received request to check if username {username} is used.")
    user = security.datastore.find_user(username=username)
    if user:
        return jsonify({"used": True})
    else:
        return jsonify({"used": False})


### App content ###

@app.route("/", methods=["GET"])
def index():
    return send_file("index.html")


@app.route("/light.html", methods=["GET"])
def light():
    return send_file("light.html")


@app.route("/lines.html", methods=["GET"])
def lines():
    return send_file("lines.html")


@app.route("/dashboard.html", methods=["GET"])
def dashboard():
    return send_file("dashboard.html")


@app.route("/heatmap.html", methods=["GET"])
def heatmap():
    return send_file("heatmap.html")


@app.route("/tiny-world-map.json", methods=["GET"])
def tinyworldmap():
    return send_file("tiny-world-map.json")


@app.route("/heatmap-wait.html", methods=["GET"])
def heatmapwait():
    return send_file("heatmap-wait.html")


@app.route("/heatmap-distance.html", methods=["GET"])
def heatmapdistance():
    return send_file("heatmap-distance.html")


@app.route("/new.html", methods=["GET"])
def new():
    return send_file("new.html")


@app.route("/recent.html", methods=["GET"])
def recent():
    return send_file("recent.html")


@app.route("/recent-dups.html", methods=["GET"])
def recent_dups():
    return send_file("recent-dups.html")


@app.route("/favicon.ico", methods=["GET"])
def favicon():
    return send_file("favicon.ico")


@app.route("/icon.png", methods=["GET"])
def icon():
    return send_file("hitchwiki-high-contrast-no-car-flipped.png")


### App functionality ###

@app.route("/content/report_duplicate.png", methods=["GET"])
def report_duplicate_image():
    return send_file("content/report_duplicate.png")


@app.route("/content/route_planner.png", methods=["GET"])
def route_planner_image():
    return send_file("content/route_planner.png")


@app.route("/manifest.json", methods=["GET"])
def manifest():
    return send_file("manifest.json")


@app.route("/sw.js", methods=["GET"])
def sw():
    return send_file("sw.js")


@app.route("/.well-known/assetlinks.json", methods=["GET"])
def assetlinks():
    return send_file("android/assetlinks.json")


@app.route("/Hitchmap.apk", methods=["GET"])
def android_app():
    return send_file("android/Hitchmap.apk")


@app.route("/content/<path:path>")
def send_report(path):
    return send_from_directory("content", path)


@app.route("/experience", methods=["POST"])
def experience():
    data = request.form
    rating = int(data["rate"])
    wait = int(data["wait"]) if data["wait"] != "" else None
    assert wait is None or wait >= 0
    assert rating in range(1, 6)
    comment = None if data["comment"] == "" else data["comment"]
    assert comment is None or len(comment) < 10000
    nickname = data["nickname"] if re.match(r"^\w{1,32}$", data["nickname"]) else None

    signal = data["signal"] if data["signal"] != "null" else None
    assert signal in ["thumb", "sign", "ask", "ask-sign", None]

    datetime_ride = data["datetime_ride"]

    now = str(datetime.utcnow())

    if request.headers.getlist("X-Real-IP"):
        ip = request.headers.getlist("X-Real-IP")[-1]
    else:
        ip = request.remote_addr

    lat, lon, dest_lat, dest_lon = map(float, data["coords"].split(","))

    assert -90 <= lat <= 90
    assert -180 <= lon <= 180
    assert (-90 <= dest_lat <= 90 and -180 <= dest_lon <= 180) or (
        math.isnan(dest_lat) and math.isnan(dest_lon)
    )

    for _i in range(10):
        resp = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            {
                "lat": lat,
                "lon": lon,
                "format": "json",
                "zoom": 3,
                "email": "info@hitchmap.com",
            },
        )
        if resp.ok:
            break
        else:
            print(resp)

    res = resp.json()
    country = "XZ" if "error" in res else res["address"]["country_code"].upper()
    pid = random.randint(0, 2**63)

    df = pd.DataFrame(
        [
            {
                "rating": rating,
                "wait": wait,
                "comment": comment,
                "name": nickname,
                "datetime": now,
                "ip": ip,
                "reviewed": False,
                "banned": False,
                "lat": lat,
                "dest_lat": dest_lat,
                "lon": lon,
                "dest_lon": dest_lon,
                "country": country,
                "signal": signal,
                "ride_datetime": datetime_ride,
                "user_id": current_user.id if not current_user.is_anonymous else None,
            }
        ],
        index=[pid],
    )

    df.to_sql("points", get_db(), index_label="id", if_exists="append")

    return redirect("/#success")


@app.route("/report-duplicate", methods=["POST"])
def report_duplicate():
    data = request.form

    now = str(datetime.datetime.utcnow())

    if request.headers.getlist("X-Real-IP"):
        ip = request.headers.getlist("X-Real-IP")[-1]
    else:
        ip = request.remote_addr

    from_lat, from_lon, to_lat, to_lon = map(float, data["report"].split(","))

    df = pd.DataFrame(
        [
            {
                "datetime": now,
                "ip": ip,
                "reviewed": False,
                "accepted": False,
                "from_lat": from_lat,
                "to_lat": to_lat,
                "from_lon": from_lon,
                "to_lon": to_lon,
            }
        ]
    )

    df.to_sql("duplicates", get_db(), index=None, if_exists="append")

    return redirect("/#success-duplicate")


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
