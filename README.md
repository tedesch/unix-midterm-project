# unix-midterm-project

## Setup

Use Python 3.11 or newer, then install the project dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Run a VM

Each VM loads its settings from `config/vm1.toml` by default. Copy that file
for each VM, then specify the copy with `--config`:

```powershell
python main.py --config config/vm2.toml --name vm2 --mode slave --master-url http://10.0.0.5:5000
```

The command-line values are saved to the specified TOML file and loaded again
on the next start. Omit them to reuse the saved values:

```powershell
python main.py --config config/vm2.toml
```

Supported options:

- `--config`: TOML file for this VM (defaults to `config/vm1.toml` beside `main.py`).
- `--name`: VM name.
- `--mode`: `master` or `slave`.
- `--master-url`: base URL used by this VM to contact the master.

When running in master mode, the server listens on all network interfaces on
port `5000` with Flask debug mode disabled. Allow inbound TCP port `5000` in
the master VM's firewall if slave VMs need to connect. Set each slave's
`--master-url` to the master's reachable IP address, such as
`http://10.0.0.5:5000`.

### Remote workload button

The dashboard workload button queues a fixed start or stop command for the
selected slave. The slave polls the master and runs only
`sudo -n systemctl start workload-simulator.service` or
`sudo -n systemctl stop workload-simulator.service`; it does not accept
arbitrary shell commands. Install the `workload-simulator.service` unit on
each Linux slave and grant the account running this project passwordless
permission to run only those service actions.
The checked-in unit assumes the repository is at
`/home/conno/unix-midterm-project` and runs the script from its `scripts`
directory as `conno`; adjust `User`, `Group`, `WorkingDirectory`, and
`ExecStart` in the unit if a slave uses a different account or repository path.
After systemd accepts the start request, the dashboard shows `Workload active`
instead of re-enabling the start button. The supplied workload script loops
continuously; stop it on the slave with
`sudo systemctl stop workload-simulator.service`.
To let the dashboard stop it remotely, update the sudoers rule to permit both
exact actions:

```bash
SYSTEMCTL_PATH="$(command -v systemctl)"
printf '%s\n' "conno ALL=(root) NOPASSWD: $SYSTEMCTL_PATH start workload-simulator.service, $SYSTEMCTL_PATH stop workload-simulator.service" |
  sudo tee /etc/sudoers.d/workload-simulator >/dev/null
sudo chmod 0440 /etc/sudoers.d/workload-simulator
sudo visudo -cf /etc/sudoers.d/workload-simulator
```

Memory, disk, and swap are sampled after the CPU sampling window, so they
reflect the time the telemetry packet is sent. The dashboard displays one
decimal place so smaller percentage changes are visible.

Set the same non-empty `command_token` in the `[security]` section of the
master and every slave's TOML config. Keep it private and use a different
random token for each deployment. Generate one with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Without a matching token, the workload command endpoints reject requests.
The dashboard prompts for this token the first time a workload is requested
in a page session; it is kept in browser memory only. Use HTTPS or restrict
dashboard access to a trusted private network, since plain HTTP does not
protect the token in transit.

Open `http://<master-ip>:5000/` in a browser to view the btop-inspired VM
dashboard. It shows the latest CPU, memory, disk, swap, and network metrics
for each named VM and the master host itself, refreshes every two seconds,
and marks a VM offline when it has not reported for 30 seconds. The host is
shown with a `HOST` badge. The master keeps the latest packet per VM in
memory; restarting the master clears the displayed telemetry until VMs send
their next packets and host collection completes.

The TOML format is:

```toml
[vm]
name = "vm1"
mode = "slave"

[master]
url = "http://localhost:5000"

[security]
command_token = "replace-with-a-long-random-token"
```
### License
To create the certificate and key for HTTPS, run:

```bash
sudo apt install -y nginx certbot python3-certbot-nginx

sudo nano /etc/nginx/sites-available/flask-api

```
on the file type 
```nginx
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Then run the following command to create the certificate and key:

```bash
sudo ln -s /etc/nginx/sites-available/flask-api \
  /etc/nginx/sites-enabled/flask-api