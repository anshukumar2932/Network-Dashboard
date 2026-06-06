from db.models import *
from monitor.monitor import check_device
from flask import Flask
from monitor.scheduler import scheduler

app = Flask(__name__)









if __name__ == "__main__":

    scheduler.start()
    Base.metadata.create_all(engine)
    print("Database tables created.")
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )