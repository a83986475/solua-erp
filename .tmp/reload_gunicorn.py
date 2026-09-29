"""以 frappe 身份对 gunicorn master 发 SIGHUP：graceful reload，让 worker 重新 import 应用代码。

用法：echo "exec(open('/tmp/reload_gunicorn.py').read())" | bench --site erp.solua.one console
"""
import glob
import os
import signal
import sys
import time

procs = {}
for path in glob.glob("/proc/[0-9]*/cmdline"):
    try:
        cmd = open(path, "rb").read().replace(b"\0", b" ").decode("utf8", "ignore")
    except OSError:
        continue
    if "gunicorn" not in cmd:
        continue
    procs[int(path.split("/")[2])] = cmd.strip()[:80]

ppids = {}
for pid in procs:
    try:
        for line in open(f"/proc/{pid}/status"):
            if line.startswith("PPid:"):
                ppids[pid] = int(line.split()[1])
    except OSError:
        pass

masters = [pid for pid in procs if ppids.get(pid) not in procs]
print("gunicorn pids:", sorted(procs))
print("master(s):", masters)
before = sorted(procs)

for pid in masters:
    os.kill(pid, signal.SIGHUP)
    print("SIGHUP ->", pid)

time.sleep(6)
after = set()
for path in glob.glob("/proc/[0-9]*/cmdline"):
    try:
        cmd = open(path, "rb").read().replace(b"\0", b" ").decode("utf8", "ignore")
    except OSError:
        continue
    if "gunicorn" in cmd:
        after.add(int(path.split("/")[2]))
print("alive after:", sorted(after))
print("old workers gone:", sorted(set(before) - after))
sys.stdout.flush()
