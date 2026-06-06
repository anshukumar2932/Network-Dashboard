from db.models import *
from monitor.monitor import check_device
from db.database import login
from flask import Flask,request, redirect, flash, render_template, session
from flask_login import login_required
from flask_socketio import SocketIO
from monitor.scheduler import scheduler
import random
import string

def generate_captcha(length=6):
    return ''.join(
        random.choices(
            string.ascii_uppercase + string.digits,
            k=length
        )
    )

app = Flask(__name__)
app.secret_key = "change_this_to_random_secret"
sockeio=SocketIO(app,cors_allowed_origins="*")

@app.route("/", methods=["GET","POST"])
def index():
    if request.method =="POST":
        user= request.form.get("user")
        passwd= request.form.get("passwd")
        captcha= request.form.get("captcha")
        if captcha != session.get("captcha"):
            flash("Invalid Captcha")
            redirect("/")
        response=login(username=user,password=passwd)#return True,False and error if occured 
        if isinstance(response, bool):
            if response:
                return redirect("/dashboard")
            else:
                flash("Invalid Credentials")
        else:
            flash("Error Occured")

    else:
        session["captcha"] = generate_captcha()
        return render_template("index.html",captcha=session["captcha"])


@app.route("/dashboard/radio",methods=['GET','POST'])
@login_required
def radio():
    if request.method=="GET":
        ...




if __name__ == "__main__":

    scheduler.start()
    Base.metadata.create_all(engine)
    print("Database tables created.")
    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        debug=True
    )