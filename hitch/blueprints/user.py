import logging
import random

import pandas as pd
from flask import Blueprint, current_app, jsonify, redirect, render_template
from flask_security import current_user

from hitch.extensions import security
from hitch.forms import ReviewForm, UserEditForm
from hitch.helpers import get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

user_bp = Blueprint("user", __name__)


@user_bp.route("/edit-user", methods=["GET", "POST"])
def form():
    if current_user.is_anonymous:
        return redirect("/login")

    form = UserEditForm()

    if form.validate_on_submit():
        updated_user = security.datastore.find_user(username=current_user.username)
        updated_user.gender = form.gender.data
        updated_user.year_of_birth = form.year_of_birth.data
        updated_user.hitchhiking_since = form.hitchhiking_since.data
        updated_user.origin_country = form.origin_country.data
        updated_user.origin_city = form.origin_city.data
        updated_user.hitchwiki_username = form.hitchwiki_username.data
        updated_user.trustroots_username = form.trustroots_username.data
        security.datastore.put(updated_user)
        security.datastore.commit()
        return redirect("/me")

    form.gender.data = current_user.gender
    form.year_of_birth.data = current_user.year_of_birth
    form.hitchhiking_since.data = current_user.hitchhiking_since
    form.origin_country.data = current_user.origin_country
    form.origin_city.data = current_user.origin_city
    form.hitchwiki_username.data = current_user.hitchwiki_username
    form.trustroots_username.data = current_user.trustroots_username

    return render_template("security/edit_user.html", form=form)


@user_bp.route("/user", methods=["GET"])
def get_user():
    """Endpoint to get the currently logged in user."""
    current_app.logger.info("Received request to get user.")

    # Check if the user is logged in
    if not current_user.is_anonymous:
        return jsonify({"logged_in": True, "username": current_user.username})
    else:
        return jsonify({"logged_in": False, "username": ""})


# TODO: properly delete the user after their confirmation
@user_bp.route("/delete-user", methods=["GET"])
def delete_user():
    return f"To delete your account please send an email to {current_app.config['EMAIL']} with the subject 'Delete my account'."


@user_bp.route("/is_username_used/<username>", methods=["GET"])
def is_username_used(username):
    """Endpoint to check if a username is already used."""
    current_app.logger.info(f"Received request to check if username {username} is used.")

    user = security.datastore.find_user(username=username)

    if user:
        return jsonify({"used": True})
    else:
        return jsonify({"used": False})


@user_bp.route("/me", methods=["GET"], defaults={"username": None, "is_me": True})
@user_bp.route("/account/<username>", methods=["GET"])
def show_account(username, is_me: bool = False):
    """Returns either the current account or the requested user

    Args:
        username: The user to show, None if current_user
        is_me: Whether the current_user should be shown, True if current_user
    """
    if is_me and current_user.is_anonymous:
        return redirect("/login")

    user = current_user if is_me else security.datastore.find_user(username=username)

    current_app.logger.info(
        f"Received request to show user account for {current_user.username}"
        if is_me
        else f"Received request to show user {username}."
    )

    # TODO: Proper 404
    if user is None:
        return "User not found."

    return render_template("security/account.html", user=user, is_me=is_me)


@user_bp.route("/create-trips", methods=["GET", "POST"])
def create_trips():
    """Creates new trips where reviews from the same day become a trip."""
    if current_user.is_anonymous:
        return redirect("/login")

    query = """
    SELECT 
        DATE(p.ride_datetime) AS date, 
        GROUP_CONCAT(p.id) AS point_ids, 
        COUNT(*) AS total_rides
    FROM points p
    LEFT JOIN ride_trips rt ON p.id = rt.ride_id
    WHERE (p.nickname = ? OR p.user_id = ?)
        AND rt.trip_id IS NULL
        AND date IS NOT NULL
    GROUP BY date
    ORDER BY date ASC;
    """

    conn = get_db()
    cursor = conn.cursor()
    day_groups = cursor.execute(query, (current_user.username, current_user.id)).fetchall()

    if len(day_groups) > 0:
        for new_trip in day_groups:
            date, ride_ids, total_rides = new_trip
            if total_rides < 2:
                continue
            trip_id = random.randint(0, 2**63)
            logger.info(f"Creating trip {trip_id} for user {current_user.id} on {date}")
            cursor.execute(
                "INSERT OR REPLACE INTO trips (trip_id, user_id, name) VALUES (?, ?, ?)",
                (trip_id, current_user.id, f"Trip on {date}"),
            )

            for ride_id in ride_ids.split(","):
                # Insert or replace existing entry
                cursor.execute("INSERT OR REPLACE INTO ride_trips (ride_id, trip_id) VALUES (?, ?)", (ride_id, trip_id))

            conn.commit()

    conn.close()

    return redirect("/trips")


@user_bp.route("/create-new-trip", methods=["GET", "POST"])
def create_new_trip():
    """Endpoint to create a new trip."""
    if current_user.is_anonymous:
        return jsonify({"error": "You need to be logged in to create a trip."})

    trip_id = random.randint(0, 2**63)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "insert or replace into trips (trip_id, user_id, name) values (?, ?, ?)",
        (trip_id, current_user.id, f"Trip with ID {trip_id}"),
    )
    conn.commit()
    conn.close()

    return redirect("/trips")


@user_bp.route("/trips", methods=["GET", "POST"])
def trips():
    """Shows a list of the rewievs of the user."""
    if current_user.is_anonymous:
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""CREATE TABLE IF NOT EXISTS ride_trips (
                    ride_id INTEGER UNIQUE,
                    trip_id INTEGER)""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS trips (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trip_id INTEGER UNIQUE,
                    user_id INTEGER,
                    name TEXT)""")

    query = f"""SELECT id, datetime, ride_datetime, country, lat, lon, dest_lat, dest_lon, rating, signal, wait, comment
    FROM points p
    LEFT JOIN ride_trips rt ON p.id = rt.ride_id
    WHERE (p.nickname = '{current_user.username}' OR p.user_id = {current_user.id})
    ORDER BY p.datetime DESC;"""

    current_user_reviews = pd.read_sql(query, get_db())

    query = f"""SELECT
        t.trip_id AS trip_id,
        t.name AS trip_name,
        GROUP_CONCAT(rt.ride_id) AS ride_ids
    from trips t left join ride_trips rt on t.trip_id = rt.trip_id 
    where t.user_id = {current_user.id}
        and rt.ride_id is not null
    group by t.trip_id;"""

    trips = cursor.execute(query).fetchall()

    return render_template("security/trips.html", trips=trips, reviews=current_user_reviews.to_html())


@user_bp.route("/edit-review/<trip_id>", methods=["GET", "POST"])
def edit_review(trip_id: int):
    form = ReviewForm()

    conn = get_db()
    cursor = conn.cursor()

    if form.validate_on_submit():
        ride_id = form.ride_id.data
        user_id_for_trip = cursor.execute("SELECT user_id FROM trips WHERE trip_id = ?", (trip_id,)).fetchone()
        if user_id_for_trip is None:
            return "Trip does not exist."
        elif user_id_for_trip[0] != current_user.id:
            return "You are not allowed to edit this trip."

        user_for_ride = cursor.execute("SELECT nickname, user_id FROM points WHERE id = ?", (ride_id,)).fetchone()
        if user_for_ride is None:
            return "Ride does not exist."
        elif user_for_ride[0] != current_user.username and user_for_ride[1] != current_user.id:
            return "You are not allowed to edit this ride."

        # Insert or replace existing entry
        cursor.execute("INSERT OR REPLACE INTO ride_trips (ride_id, trip_id) VALUES (?, ?)", (ride_id, trip_id))

        conn.commit()
        return redirect("/trips")

    form.ride_id.data = None
    trip_name = cursor.execute("SELECT name FROM trips WHERE trip_id = ?", (trip_id,)).fetchone()[0]
    conn.close()

    return render_template("security/edit_review.html", form=form, trip_name=trip_name, trip_id=trip_id)
