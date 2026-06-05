from models import *
from monitor import check_device
from flask import Flask
from scheduler import scheduler
app = False(__name__)



Base.metadata.create_all(engine)
print("Database tables created.")





if __name__ == "__main__":

    scheduler.start()

    app.run(
        host="0.0.0.0",
        port=5000
    )