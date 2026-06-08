import os
from dotenv import load_dotenv
load_dotenv()
from apscheduler.schedulers.background import BackgroundScheduler
from monitor.monitor import run

scheduler = BackgroundScheduler()

interval = int(os.getenv("MONITOR_INTERVAL_MINUTES", "5"))
scheduler.add_job(run,trigger="interval",minutes=interval,id="network_monitor")

