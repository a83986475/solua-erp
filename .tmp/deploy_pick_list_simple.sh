#!/bin/bash
set -e
DIR=/home/frappe/frappe-bench/apps/solua_home/solua_home/print_format
sudo -u frappe mkdir -p "$DIR/pick_list_simple"
sudo -u frappe install -m 664 /tmp/pick_list_simple.json "$DIR/pick_list_simple/pick_list_simple.json"
sudo -u frappe install -m 664 /tmp/pick_list_color.json "$DIR/pick_list_color/pick_list_color.json"
sudo -u frappe ls -l "$DIR/pick_list_simple" "$DIR/pick_list_color"
PYTHONIOENCODING=utf-8 /home/frappe/frappe-bench/env/bin/python /tmp/deploy_pick_list_simple.py
