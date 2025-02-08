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
    if current_user.is_anonymous:
        return redirect("/login")
    
    trips = pd.read_sql("select * from trips", get_db())
    reviews = pd.read_sql("select * from points where nickname = 'Chris9012'", get_db())
    reviews["trip_id"] = pd.merge(
        left=reviews["id"], right=trips, how="left", left_on="id", right_on="ride_id"
    )["trip_id"].astype(pd.Int64Dtype())

    reviews = reviews[reviews["trip_id"].isnull()]
    reviews = reviews[reviews["ride_datetime"].notnull()]
    reviews = reviews.sort_values(by="ride_datetime", ascending=True)

    # heuristic for trip: rides on the same day are part of the same trip
    reviews["ride_datetime"] = pd.to_datetime(reviews["ride_datetime"])
    reviews["date"] = reviews['ride_datetime'].dt.date
    day_groups = reviews.groupby("date")
    if len(day_groups) > 0:
        conn = get_db()
        cursor = conn.cursor()
        for trip in day_groups:
            trip_df = trip[1]
            if len(trip_df) < 2:
                continue
            trip_id = random.randint(0, 2**63)
            logger.info(f"Creating trip {trip_id} for user {current_user.id}")
            df = pd.DataFrame(
                [
                    {
                        "user_id": current_user.id,
                    }
                ],
                index=[trip_id],
            )

            df.to_sql("user_trips", get_db(), index_label="trip_id", if_exists="append")

            for _, ride in trip_df.iterrows():
               

                # Insert or replace existing entry
                cursor.execute("INSERT OR REPLACE INTO trips (ride_id, trip_id) VALUES (?, ?)", (ride["id"], trip_id))

                conn.commit()

        conn.close()

    return redirect("/trips")




@user_bp.route("/create-new-trip", methods=["GET", "POST"])
def create_new_trip():
    """Endpoint to create a new trip."""
    if current_user.is_anonymous:
        return jsonify({"error": "You need to be logged in to create a trip."})

    df = pd.DataFrame(
        [
            {
                "user_id": current_user.id,
            }
        ],
        index=[str(random.randint(0, 2**63))],
    )

    df.to_sql("user_trips", get_db(), index_label="trip_id", if_exists="append")
    return redirect("/trips")


@user_bp.route("/trips", methods=["GET", "POST"])
def trips():
    """Shows a list of the rewievs of the user."""
    if current_user.is_anonymous:
        return redirect("/login")
    
    trips = pd.read_sql("select * from trips", get_db())

    current_user_reviews = pd.read_sql(f"select * from points where nickname = '{current_user.username}'", get_db())
    current_user_reviews["trip_id"] = pd.merge(
        left=current_user_reviews["id"], right=trips, how="left", left_on="id", right_on="ride_id"
    )["trip_id"].astype(pd.Int64Dtype())
    current_user_trips = pd.read_sql(f"select * from user_trips where user_id = {current_user.id}", get_db())

    link = "<a href='/create-new-trip'>Create a new trip</a>"
    link1 = "<a href='/create-trips'>Create trips</a>"
    link2 = "<a href='/edit-review'>Edit a review</a>"
    res = link + "<br>" + link1 + "<br>" + link2 + "<br>"

    for _, trip in current_user_trips.iterrows():
        res += f"Trip id: {trip.trip_id}<br>"
        for _, row in pd.read_sql(f"select * from trips where trip_id = {trip.trip_id}", get_db()).iterrows():
            res += f"____Ride id: {row.ride_id}<br>"

    return res + current_user_reviews.to_html()


@user_bp.route("/edit-review", methods=["GET", "POST"])
def edit_review():
    form = ReviewForm()

    if form.validate_on_submit():
        ride_id = form.ride_id.data
        trip_id = form.trip_id.data
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""CREATE TABLE IF NOT EXISTS trips (
                    ride_id INTEGER UNIQUE,
                    trip_id INTEGER)""")

        # Insert or replace existing entry
        cursor.execute("INSERT OR REPLACE INTO trips (ride_id, trip_id) VALUES (?, ?)", (ride_id, trip_id))

        conn.commit()
        conn.close()
        return redirect("/trips")

    form.ride_id.data = 1
    form.trip_id.data = 1

    return render_template("security/edit_review.html", form=form)
