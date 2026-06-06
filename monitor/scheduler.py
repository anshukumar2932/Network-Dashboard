from apscheduler.schedulers.background import BackgroundScheduler
from monitor.monitor import run

scheduler = BackgroundScheduler()

scheduler.add_job(run,trigger="interval",minutes=5,id="network_monitor")

