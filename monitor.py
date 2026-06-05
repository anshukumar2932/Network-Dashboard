from database import SessionLocal
from models import Device
from models import PingHistory

from datetime import datetime

import asyncio
from ping import ping_device

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

def run_monitoring_cycle():

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

            device.status = result["status"]

            if result["status"]:

                device.last_seen = datetime.utcnow()

            else:

                down_devices.append(device)

            history = PingHistory(
                device_id=device.id,
                ping_time=datetime.utcnow(),
                latency_ms=result["latency"],
                status=result["status"]
            )

            session.add(history)

    session.commit()

    session.close()

    print(
        f"Cycle Complete. Down Devices: {len(down_devices)}"
    )