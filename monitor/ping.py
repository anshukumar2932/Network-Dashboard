import asyncio
import time


async def ping_device(ip: str) -> float | None:
    print(f"[PING] pinging {ip}...")
    start = time.time()
    loop = asyncio.get_running_loop()

    async def _ping():
        proc = await asyncio.create_subprocess_exec(
            "ping", "-c", "1", "-W", "2", ip,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        try:
            await asyncio.wait_for(proc.wait(), timeout=5)
            return proc.returncode == 0
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            return False

    success = await _ping()
    elapsed = round((time.time() - start) * 1000, 1)
    if not success:
        print(f"[PING] {ip} -> TIMEOUT ({elapsed}ms)")
        return None
    else:
        latency = round(elapsed, 1)
        print(f"[PING] {ip} -> {latency}ms")
        return latency / 1000.0
