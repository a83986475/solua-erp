#!/bin/bash
set -e
APP=/home/frappe/frappe-bench/apps/solua_home/solua_home
sudo -u frappe install -m 664 /tmp/a4_provider.py "$APP/printing/a4_designer.py"
sudo -u frappe ls -l "$APP/printing/a4_designer.py"
PYTHONIOENCODING=utf-8 /home/frappe/frappe-bench/env/bin/python /tmp/verify_a4_logo_fix.py
