from ping3 import ping
import asyncio


async def ping_device(ip: str):

    loop = asyncio.get_running_loop()

    response = await loop.run_in_executor(
        None,
        lambda: ping(ip, timeout=1)
    )

    return response