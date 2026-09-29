#!/bin/bash
set -e
APP=/home/frappe/frappe-bench/apps/solua_home/solua_home
sudo -u frappe install -m 664 /tmp/wholesale_py.py "$APP/printing/wholesale.py"
sudo -u frappe install -m 664 /tmp/install_py.py "$APP/install.py"
sudo -u frappe install -m 664 /tmp/pick_list_simple.json "$APP/print_format/pick_list_simple/pick_list_simple.json"
sudo -u frappe ls -l "$APP/printing/wholesale.py" "$APP/install.py" "$APP/print_format/pick_list_simple/pick_list_simple.json"
PYTHONIOENCODING=utf-8 /home/frappe/frappe-bench/env/bin/python /tmp/deploy_pick_uom_v2.py
