import os

from flask import Blueprint, flash, redirect, render_template, request, url_for, jsonify
from flask_login import login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from .factory import db
from .models.user import User

auth = Blueprint("auth", __name__)


@auth.route("/login")
def login():
    return render_template("login.html")


@auth.route("/login", methods=["POST"])
def login_post():
    # login code goes here

    username = request.form.get("username")
    password = request.form.get("password")
    remember = True if request.form.get("remember") else False

    user = User.query.filter_by(username=username).first()

    # check if the user actually exists
    # take the user-supplied password, hash it, and compare it to the hashed password in the database
    if not user or not check_password_hash(user.password, password):
        flash("Nesprávné uživatelské jméno nebo heslo!")
        return redirect(
            url_for("auth.login")
        )  # if the user doesn't exist or password is wrong, reload the page
    login_user(user, remember=remember)

    return redirect(url_for("main.race_current"))


@auth.route("/signup")
def signup():
    return jsonify({"status": 200, "action": "show reg page"})


@auth.route("/signup", methods=["POST"])
def signup_post():
    if os.getenv("REG_LOCKED", ""):
        return jsonify({"status": 400, "action": "registration closed"})

    else:
        # code to validate and add user to database goes here
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(
            username=username
        ).first()  # if this returns a user, then the username already exists in database

        if (
            user
        ):  # if a user is found, we want to redirect back to signup page so user can try again
            ###flash("Uživatelské jméno již existuje")

            ###return redirect(url_for("auth.signup"))
            out = {"status": 203, "payload": "User exists"}
            return jsonify(out)
        # create a new user with the form data. Hash the password so the plaintext version isn't saved.
        new_user = User(
            username=username,
            password=generate_password_hash(password, method="sha256"),
        )

        # add the new user to the database
        db.session.add(new_user)
        db.session.commit()

    #return redirect(url_for("auth.login"))
    return jsonify({"redirect": "login"})


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))
