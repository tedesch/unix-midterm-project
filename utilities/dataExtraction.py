import asyncio
import psutil
import json

async def package(metric_function):
    measurements = []
    for _ in range(10):
        measurement = metric_function()
        measurements.append(measurement)
        await asyncio.sleep(0.5)
    return measurements

async def cpu():
    return await package(lambda: psutil.cpu_percent(interval=1))


async def memory():
    return await package(lambda: psutil.virtual_memory().percent)


async def disk():
    return await package(lambda: psutil.disk_usage('/').percent)


async def swap():
    return await package(lambda: psutil.swap_memory().percent)


async def network():
    net_io = psutil.net_io_counters()
    return {
        "bytes_sent": net_io.bytes_sent,
        "bytes_recv": net_io.bytes_recv
    }


async def get_json_data():
    data = {
        "cpu-metric": await cpu(),
        "memory-metric": await memory(),
        "disk-metric": await disk(),
        "swap-metric": await swap(),
        "network-metric": await network()
    }
    return json.dumps(data, indent=2)
