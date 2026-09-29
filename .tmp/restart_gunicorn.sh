#!/bin/bash
set -e
MASTER=$(ps -eo pid,cmd | grep -i gunicorn | grep -v grep | awk '{print $1}' | sort -n | head -1)
echo "master before: $MASTER"
ps -o pid,lstart,cmd -p "$MASTER" | tail -1
sudo -u frappe kill -TERM "$MASTER"
sleep 8
echo "--- after restart"
ps -eo pid,ppid,user,lstart,cmd | grep -i gunicorn | grep -v grep | head -3
echo "--- health"
curl -s -o /dev/null -w "ping=%{http_code}\n" -H "Host: erp.solua.one" http://127.0.0.1:8000/api/method/frappe.ping
