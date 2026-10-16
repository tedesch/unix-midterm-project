import json
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VMConfig:
    name: str = "vm1"
    mode: str = "slave"
    master_url: str = "http://localhost:5000"
    command_token: str = ""
    ca_cert: str = ""


def load_config(path: Path) -> VMConfig:
    try:
        with path.open("rb") as config_file:
            values = tomllib.load(config_file)
    except FileNotFoundError:
        return VMConfig()

    vm_values = values.get("vm", {})
    master_values = values.get("master", {})
    security_values = values.get("security", {})
    if (
        not isinstance(vm_values, dict)
        or not isinstance(master_values, dict)
        or not isinstance(security_values, dict)
    ):
        raise ValueError("Config sections [vm], [master], and [security] must be tables")

    name = vm_values.get("name", VMConfig.name)
    mode = vm_values.get("mode", VMConfig.mode)
    master_url = master_values.get("url", VMConfig.master_url)
    command_token = security_values.get("command_token", VMConfig.command_token)
    ca_cert = master_values.get("ca_cert", VMConfig.ca_cert)
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Config value [vm].name must be a non-empty string")
    if mode not in ("master", "slave"):
        raise ValueError("Config value [vm].mode must be 'master' or 'slave'")
    if not isinstance(master_url, str) or not master_url.strip():
        raise ValueError("Config value [master].url must be a non-empty string")
    if not isinstance(command_token, str):
        raise ValueError("Config value [security].command_token must be a string")
    if not isinstance(ca_cert, str):
        raise ValueError("Config value [master].ca_cert must be a string")

    return VMConfig(
        name=name,
        mode=mode,
        master_url=master_url.rstrip("/"),
        command_token=command_token,
        ca_cert=ca_cert,
    )


def save_config(path: Path, config: VMConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    contents = (
        "[vm]\n"
        f"name = {json.dumps(config.name)}\n"
        f"mode = {json.dumps(config.mode)}\n\n"
        "[master]\n"
        f"url = {json.dumps(config.master_url)}\n"
        f"ca_cert = {json.dumps(config.ca_cert)}\n\n"
        "[security]\n"
        f"command_token = {json.dumps(config.command_token)}\n"
    )
    path.write_text(contents, encoding="utf-8")
