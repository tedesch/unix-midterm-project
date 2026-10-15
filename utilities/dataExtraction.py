import asyncio
import global_variables as globals
import psutil
import json

async def package(metric_function):
    measurements = []
    for _ in range(50):
        measurement = await asyncio.to_thread(metric_function)
        measurements.append(measurement)
    return measurements

async def cpu():
    return await package(lambda: psutil.cpu_percent(interval=0.1))


async def memory():
    return await asyncio.to_thread(lambda: psutil.virtual_memory().percent)


async def disk():
    return await asyncio.to_thread(lambda: psutil.disk_usage('/').percent)


async def swap():
    swap_stats = await asyncio.to_thread(psutil.swap_memory)
    return swap_stats.percent if swap_stats.total else None


async def network():
    net_io = await asyncio.to_thread(psutil.net_io_counters)
    return {
        "bytes_sent": net_io.bytes_sent,
        "bytes_recv": net_io.bytes_recv
    }


async def get_json_data():
    cpu_data = await cpu()
    memory_data, disk_data, swap_data, network_data = await asyncio.gather(
        memory(),
        disk(),
        swap(),
        network(),
    )
    data = {
        "name": globals.name,
        "cpu-metric": cpu_data,
        "memory-metric": memory_data,
        "disk-metric": disk_data,
        "swap-metric": swap_data,
        "network-metric": network_data,
    }
    return json.dumps(data, indent=2)
