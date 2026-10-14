#!/bin/bash

LOG_FILE="$HOME/person2-lab/workload.log"
exec >> "$LOG_FILE" 2>&1

HEARTBEAT_PID=""

watchdog_heartbeat(){
    while true
    do
        sleep 10
        systemd-notify WATCHDOG=1
    done
}

STOPPING=0
CHILD_PID=""

cleanup() {
    if [ "$STOPPING" -eq 1 ]; then
        return
    fi

    STOPPING=1
    trap '' SIGINT SIGTERM

    if [ -n "$HEARTBEAT_PID" ]; then
        kill "$HEARTBEAT_PID" 2>/dev/null
        wait "$HEARTBEAT_PID" 2>/dev/null
    fi

    echo "[$(date)] Workload simulator stopping..."

    if [ -n "$CHILD_PID" ] && kill -0 "$CHILD_PID" 2>/dev/null; then
        kill -TERM "$CHILD_PID" 2>/dev/null
        wait "$CHILD_PID" 2>/dev/null
    fi

    exit 0
}

trap cleanup SIGINT SIGTERM

echo "==== Workload Test Starting ===="

watchdog_heartbeat &
HEARTBEAT_PID=$!

systemd-notify --ready --status="Workload simulator running"

while true
do
    echo "[$(date)] ===== Starting new workload cycle ====="
    echo "[$(date)] Starting CPU stress..."
    stress-ng --cpu 1 --timeout 5s --metrics-brief & 
    CHILD_PID=$!
    wait "$CHILD_PID"
    CHILD_PID=""

    echo "[$(date)] Starting memory stress..."
    stress-ng --vm 1 --vm-bytes 64M --timeout 5s --metrics-brief &
    CHILD_PID=$!
    wait "$CHILD_PID"
    CHILD_PID=""

    echo "[$(date)] Starting disk stress..."
    stress-ng --hdd 1 --hdd-bytes 32M --timeout 5s --metrics-brief &
    CHILD_PID=$!
    wait "$CHILD_PID"
    CHILD_PID=""
    
    echo "[$(date)] Starting filesystem stress on root filesystem..."
    stress-ng --dir 1 \
        --temp-path "$HOME/person2-lab/swapdirectory" \
        --timeout 5s --metrics-brief &
    CHILD_PID=$!
    wait "$CHILD_PID"
    CHILD_PID=""
 
    echo "[$(date)] Starting network stress..."

    for REQUEST in 1 2 3
    do
        if RESULT=$(curl --fail --silent --show-error \
            --max-time 5 \
            -o /dev/null \
            -w 'HTTP %{http_code} bytes=%{size_download} time=%{time_total}s' \
            "https://cloudflare.com/cdn-cgi/trace"); then

            echo "[$(date)] Network request $REQUEST/3 succeeded: $RESULT"
        else
            CURL_STATUS=$?
            echo "[$(date)] Network request $REQUEST/3 failed (curl exit code $CURL_STATUS)."
        fi

        if [ "$REQUEST" -lt 3 ]; then
            sleep 1
        fi
    done

    echo "[$(date)] Cycle complete. Resting for 5 seconds..."
    sleep 5
done
