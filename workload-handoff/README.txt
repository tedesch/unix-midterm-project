PERSON 2 - WORKLOAD SIMULATOR

Contents:
- person2-lab/workload.sh: workload generator
- person2-lab/swapdirectory/: filesystem stress target
- person2-lab/workload.log: sample run evidence
- workload-simulator.service: systemd service configuration
- dependencies.txt: dependency commands and package versions

Requirements:
- Ubuntu Linux
- stress-ng
- curl
- systemd and systemd-notify
- A regular Linux account to run the workload

The service runs CPU, memory, disk I/O, filesystem, and network
stress tests in repeated cycles.

The systemd unit configures automatic startup, restart behavior,
readiness notifications, and a watchdog timeout.

Before installing on another VM, update the service's User,
Group, WorkingDirectory, and ExecStart paths to match the target
account and installation directory.

Install dependencies:
sudo apt update
sudo apt install stress-ng curl

Check the workload script:
bash -n ~/person2-lab/workload.sh

After installing the service unit:
sudo systemctl daemon-reload
sudo systemctl enable --now workload-simulator.service

Check status:
sudo systemctl status workload-simulator.service --no-pager

View workload logs:
tail -n 80 ~/person2-lab/workload.log
