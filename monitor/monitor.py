import os
from db.database import SessionLocal, invalidate_cache_for
from db.models import Device, PingHistory, NetworkLink
from sqlalchemy import delete
from datetime import datetime, timedelta, timezone
import asyncio
import time as _time

from monitor.ping import ping_device
from monitor.alert import send_alert_down, send_alert_up

from extensions import socketio

monitor_status = {
    "last_run": None,
    "last_success": None,
    "last_duration": None,
    "last_device_count": 0,
    "last_up": 0,
    "last_down": 0,
    "running": False,
}


async def check_device(device):
    print(f"[MONITOR] check_device({device.device_name}, {device.ip})")
    for attempt in range(3):
        print(f"[MONITOR]   attempt {attempt+1}/3 for {device.ip}")
        latency = await ping_device(device.ip)

        if latency is not None:
            print(f"[MONITOR]   {device.ip} -> UP ({round(latency*1000,1)}ms)")
            return {
                "device": device,
                "status": True,
                "latency": latency * 1000
            }
        print(f"[MONITOR]   attempt {attempt+1}/3 failed for {device.ip}")

    print(f"[MONITOR]   {device.ip} -> DOWN after 3 attempts")
    return {
        "device": device,
        "status": False,
        "latency": None
    }


def chunk(devices, size=50):
    for i in range(0, len(devices), size):
        yield devices[i:i + size]


async def process_batch(batch):
    tasks = [
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
    links = session.query(NetworkLink).all()
    for link in links:
        src = session.query(Device).filter(Device.ip == link.source_ip).first()
        dst = session.query(Device).filter(Device.ip == link.destination_ip).first()
        if not src or not dst:
            continue
        link.status = src.status and dst.status
        link.last_checked = datetime.now(timezone.utc).replace(tzinfo=None)


def run():
    print(f"[MONITOR] ===== Monitoring Cycle Start =====")
    start_ts = _time.time()

    monitor_status["running"] = True
    session = SessionLocal()

    devices = []
    down = []
    up = []
    ping_ok = 0
    ping_fail = 0
    elapsed = 0

    try:
        devices = session.query(Device).all()
        print(f"[MONITOR] Loaded {len(devices)} devices from DB")
        results = asyncio.run(monitor_devices(devices))
        status_change = False
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        for result in results:
            device = result["device"]
            previous_status = device.status
            current_status = result["status"]
            device.status = current_status

            print(f"[MONITOR] {device.ip} previous={previous_status} current={current_status}")

            if current_status:
                device.last_seen = now
                ping_ok += 1
            else:
                ping_fail += 1

            history = PingHistory(
                device_ip=device.ip,
                ping_time=now,
                latency_ms=result["latency"],
                status=current_status
            )
            session.add(history)

            if previous_status and not current_status:
                status_change = True
                down.append(device)
                print(f"[MONITOR] {device.ip} went DOWN")

            elif not previous_status and current_status:
                status_change = True
                up.append(device)
                print(f"[MONITOR] {device.ip} recovered UP")

        # Cleanup old ping history
        retention_hours = int(os.getenv("PING_HISTORY_RETENTION_HOURS", "24"))
        cutoff = now - timedelta(hours=retention_hours)
        session.execute(delete(PingHistory).where(PingHistory.ping_time < cutoff))
        update_link_status(session)
        session.commit()
        invalidate_cache_for("topology")

        print(f"[MONITOR] Ping results: {ping_ok} OK, {ping_fail} FAIL")

        if status_change:
            print(f"[MONITOR] Status change detected, emitting device_status_update")
            changes = []
            for d in down:
                changes.append({"id": d.ip, "status": False, "ip": d.ip})
            for d in up:
                changes.append({"id": d.ip, "status": True, "ip": d.ip})
            socketio.emit("device_status_update", {"changes": changes})

        elapsed = round(_time.time() - start_ts, 2)
        monitor_status["last_success"] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        monitor_status["last_device_count"] = len(devices)
        monitor_status["last_up"] = ping_ok
        monitor_status["last_down"] = ping_fail
        monitor_status["last_duration"] = elapsed

        socketio.emit("monitor_heartbeat", {
            "timestamp": monitor_status["last_success"],
            "devices": len(devices),
            "up": ping_ok,
            "down": ping_fail,
            "duration": elapsed
        })

    except Exception as e:
        session.rollback()
        elapsed = round(_time.time() - start_ts, 2)
        print(f"[MONITOR] ERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        monitor_status["running"] = False
        monitor_status["last_run"] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        monitor_status["last_duration"] = elapsed

    if down:
        print(f"[MONITOR] Sending alert for {len(down)} down devices")
        send_alert_down(down)

    if up:
        print(f"[MONITOR] Sending alert for {len(up)} recovered devices")
        send_alert_up(up)

    session.close()

    result = {
        "total": len(devices),
        "up": ping_ok,
        "down": ping_fail,
        "recovered": len(up),
        "new_down": len(down),
        "duration": elapsed
    }

    print(
        f"[MONITOR] Cycle Complete | Devices={len(devices)} "
        f"| OK={ping_ok} FAIL={ping_fail} "
        f"| NewDown={len(down)} Recovered={len(up)} "
        f"| Duration={elapsed}s"
    )

    return result
