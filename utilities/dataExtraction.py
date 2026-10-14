import asyncio
import psutil
import json

async def package(metric_function):
    measurements = []
    for _ in range(10):
        measurement = await asyncio.to_thread(metric_function)
        measurements.append(measurement)
        # await asyncio.sleep(0.1)
    return measurements

async def cpu():
    return await package(lambda: psutil.cpu_percent(interval=0.01))


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
    cpu_data, memory_data, disk_data, swap_data, network_data = await asyncio.gather(
        cpu(),
        memory(),
        disk(),
        swap(),
        network(),
    )
    data = {
        "cpu-metric": cpu_data,
        "memory-metric": memory_data,
        "disk-metric": disk_data,
        "swap-metric": swap_data,
        "network-metric": network_data,
    }
    return json.dumps(data, indent=2)
