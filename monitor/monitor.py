from db.database import SessionLocal
from db.models import Device, PingHistory, Link
from sqlalchemy import delete


from datetime import datetime, timedelta
import asyncio

from monitor.ping import ping_device
from monitor.alert import send_alert_down, send_alert_up

from app import socketio

async def check_device(device):

    for _ in range(3):
        latency = await ping_device(device.ip)

        if latency is not None:

            return {
                "device": device,
                "status": True,
                "latency": latency * 1000
            }

    return {
        "device": device,
        "status": False,
        "latency": None
    }

def chunk(devices, size=50):

    for i in range(0, len(devices), size):
        yield devices[i:i + size]

async def process_batch(batch):
    tasks=[
        check_device(device=device)
        for device in batch
    ]

    return await asyncio.gather(*tasks)

async def monitor_devices(devices):

    all_results = []

    for batch in chunk(devices):
        results = await process_batch(batch)
        all_results.extend(results)

    return all_results

def update_link_status(session):

    links = session.query(Link).all()

    for link in links:

        if not link.device_a_ref or not link.device_b_ref:
            continue

        link.status = (
            link.device_a_ref.status and
            link.device_b_ref.status
        )

        link.last_checked = datetime.utcnow()

def run():

    print("Monitoring Started")

    session = SessionLocal()

    try:
        devices = session.query(Device).all()
        results = asyncio.run(monitor_devices(devices))
        down = []
        up = []

        now = datetime.utcnow()

        for result in results:

            device = result["device"]
            previous_status = device.status
            current_status = result["status"]
            device.status = current_status

            if current_status:
                device.last_seen = now

            history = PingHistory(
                device_id=device.id,
                ping_time=now,
                latency_ms=result["latency"],
                status=current_status
            )

            session.add(history)

            if previous_status and not current_status:
                down.append(device)

            elif not previous_status and current_status:
                up.append(device)

        # Cleanup old ping history
        cutoff = now - timedelta(hours=1)

        session.execute(delete(PingHistory).where(PingHistory.ping_time < cutoff))
        update_link_status(session)
        session.commit()

    except Exception as e:

        session.rollback()
        print(f"Monitoring Error: {e}")

    finally:
        session.close()

    if down:
        send_alert_down(down)

    if up:
        send_alert_up(up)

    print(
        f"Cycle Complete | Devices={len(devices)} "
        f"| Down={len(down)} "
        f"| Recovered={len(up)}"
    )    

def send_topology_update(data):
    socketio.emit("topology_update",data)

def send_alert(alert):
    socketio.emit("alert",alert)