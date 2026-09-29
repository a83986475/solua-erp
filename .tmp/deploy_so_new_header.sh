#!/bin/bash
set -e
APP=/home/frappe/frappe-bench/apps/solua_home/solua_home
sudo -u frappe install -m 664 /tmp/so_wholesale.py "$APP/printing/wholesale.py"
sudo -u frappe install -m 664 /tmp/so_api_a4_designer.py "$APP/api/a4_designer.py"
sudo -u frappe install -m 664 /tmp/so_printing_a4_designer.py "$APP/printing/a4_designer.py"
sudo -u frappe mkdir -p "$APP/print_format/so_new_header"
sudo -u frappe install -m 664 /tmp/so_new_header.json "$APP/print_format/so_new_header/so_new_header.json"
echo "--- installed"
sudo -u frappe ls -l "$APP/printing/wholesale.py" "$APP/api/a4_designer.py" "$APP/printing/a4_designer.py" "$APP/print_format/so_new_header/"
sudo -u frappe /home/frappe/frappe-bench/env/bin/python -m py_compile "$APP/printing/wholesale.py" "$APP/api/a4_designer.py" "$APP/printing/a4_designer.py"
echo "syntax OK"
