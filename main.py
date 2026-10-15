import argparse
import asyncio
import json
import logging
from pathlib import Path
from collections.abc import Sequence
from threading import Thread
from time import monotonic, sleep

import global_variables as globals
import psutil
from utilities.config import VMConfig, load_config, save_config
from utilities.dataExtraction import get_json_data


HOST_TELEMETRY_INTERVAL_SECONDS = 2
logger = logging.getLogger(__name__)


def main(argv: Sequence[str] | None = None) -> None:
    default_config_path = Path(__file__).resolve().parent / "config" / "vm1.toml"
    parser = argparse.ArgumentParser(description="Run a project VM.")
    parser.add_argument(
        "--config",
        type=Path,
        default=default_config_path,
        help="Path to this VM's TOML config file.",
    )
    parser.add_argument("--name", help="Set and save this VM's name.")
    parser.add_argument(
        "--mode",
        choices=("master", "slave"),
        help="Set and save this VM's mode.",
    )
    parser.add_argument(
        "--master-url",
        help="Set and save the master server URL (for example, http://10.0.0.5:5000).",
    )
    args = parser.parse_args(argv)

    config = load_config(args.config)
    config = VMConfig(
        name=args.name if args.name is not None else config.name,
        mode=args.mode if args.mode is not None else config.mode,
        master_url=(
            args.master_url.rstrip("/")
            if args.master_url is not None
            else config.master_url
        ),
        command_token=config.command_token,
    )
    save_config(args.config, config)

    globals.name = config.name
    globals.mode = config.mode
    globals.Url = config.master_url
    globals.command_token = config.command_token
    print(f"Starting VM {globals.name} in {globals.mode} mode")

    from api import apiDef as apdef
    from api import apiRequest as req
    from api import dashboard as dash

    if globals.mode == "master":
        app = apdef.create_app()
        record_telemetry = app.extensions["record_telemetry"]

        def collect_host_telemetry() -> None:
            next_collection = monotonic()
            while True:
                try:
                    packet = json.loads(asyncio.run(get_json_data()))
                    packet["name"] = f"{globals.name} (host)"
                    packet["is_host"] = True
                    record_telemetry(packet)
                except (OSError, psutil.Error, RuntimeError, ValueError):
                    logger.exception("Unable to collect host telemetry")

                next_collection += HOST_TELEMETRY_INTERVAL_SECONDS
                sleep(max(0, next_collection - monotonic()))

        Thread(target=collect_host_telemetry, name="host-telemetry", daemon=True).start()
        app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
        dash.sendDataLoopToDashboard()
    else:
        req.sendDataLoop()


if __name__ == "__main__":
    main()
