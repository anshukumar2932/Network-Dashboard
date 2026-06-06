from db.database import SessionLocal
from db.models import Device, PingHistory

from datetime import datetime
import asyncio

from monitor.ping import ping_device
from monitor.alert import send_alert_down, send_alert_up
async def check_device(device):

    for attempt in range(3):
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

def run():
    down=[]
    up=[]

    print("Monitoring Started")
    session = SessionLocal()
    devices = session.query(Device).all()
    down_devices = []
    for batch in chunk(devices, 50):
        results = asyncio.run(
            process_batch(batch)
        )

        for result in results:
            device = result["device"]
            prev=device.status
            curr=result["status"]
            device.status = result["status"]

            if result["status"]:
                device.last_seen = datetime.utcnow()
            else:
                down_devices.append(device)
                
            if prev== None:
                pass
            elif prev and not curr:
                down.append(device)
            elif prev == False and curr:
                up.append(device)

            history = PingHistory(
                device_id=device.id,
                ping_time=datetime.utcnow(),
                latency_ms=result["latency"],
                status=result["status"]
            )
            session.add(history)

    session.commit()
    session.close()

    if down:
        send_alert_down(down)
    if up:
        send_alert_up(up)

    print(
        f"Cycle Complete. Down Devices: {len(down_devices)}"
    )