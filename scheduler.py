from apscheduler.schedulers.background import BackgroundScheduler

from monitor import run_monitoring_cycle

scheduler = BackgroundScheduler()

scheduler.add_job(
    run_monitoring_cycle,
    trigger="interval",
    minutes=5,
    id="network_monitor"
)

scheduler.start()