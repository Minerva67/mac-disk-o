#!/usr/bin/env python3
"""ln_png 清理看板后端：每 2 秒采一次 df/ps，提供 /stats JSON，并托管 index.html。只读，不碰删除进程。"""
import json, os, re, subprocess, threading, time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(os.environ.get("TMPDIR", "/tmp"), "disk-cleanup-history.json")
# 启动时自动取基线；也可用环境变量覆盖：START_TOTAL / FLOOR / PORT
def _iused():
    return int(subprocess.run(["df", "-i", "/System/Volumes/Data"], capture_output=True, text=True).stdout.splitlines()[1].split()[5])
START_TOTAL = int(os.environ.get("START_TOTAL") or _iused())
FLOOR = int(os.environ.get("FLOOR", 2_500_000))   # 一台正常 Mac 的文件数估计（用来估剩余）
START_TS = int(time.time())
PORT = int(os.environ.get("PORT", 8765))

hist = []                     # [ts, iused, avail_kb]
lock = threading.Lock()

def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout

def sample():
    out = sh(["df", "-k", "-i", "/System/Volumes/Data"]).splitlines()
    p = out[1].split()
    return int(time.time()), int(p[5]), int(p[3])

STATE_MAP = {"R": "运行", "S": "睡眠", "U": "等磁盘", "T": "已暂停", "I": "空闲", "Z": "僵尸"}
def procs():
    # sudo 起的子进程对普通用户隐藏参数，所以用 sudo 父进程认名字、用子进程(ppid 匹配)取 CPU/状态
    all_ = []
    for line in sh(["ps", "-axo", "pid,ppid,etime,%cpu,rss,state,command"]).splitlines()[1:]:
        p = line.split(None, 6)
        if len(p) < 7: continue
        all_.append({"pid": int(p[0]), "ppid": int(p[1]), "etime": p[2], "cpu": float(p[3]),
                     "rss": int(p[4]), "st": p[5], "cmd": p[6]})
    by_pid = {a["pid"]: a for a in all_}
    rows = []
    for a in all_:
        c = a["cmd"]
        par = by_pid.get(a["ppid"], {"cmd": ""})["cmd"]
        is_py = "Python.app/Contents/MacOS/Python" in c or c.startswith("python3")
        if is_py and "stream_delete" in par:            # sudo python3 stream_delete.py 直接起的
            m = re.search(r"stream_delete\.py \S+ (\d+) (\d+)", par)
            name, src = (f"分工进程 {m.group(2)}/{m.group(1)}" if m else "主删除进程"), a
        elif is_py and "caffeinate" in par and "stream_delete" in par:   # 脚本里 caffeinate 包着的主进程
            name, src = "主删除进程", a
        elif is_py and "bulk_delete" in par:     # 脚本起的：带 caffeinate 子进程的是主进程，其余是分工
            main = any(k["ppid"] == a["pid"] and k["cmd"].startswith("caffeinate") for k in all_)
            name, src = ("主删除进程" if main else "分工进程"), a
        elif c.startswith("caffeinate -i"): name, src = "防休眠", a
        elif c.endswith("/deleted_helper"): name, src = "系统自带清理", a
        else: continue
        rows.append({"name": name, "pid": src["pid"], "etime": src["etime"], "cpu": src["cpu"],
                     "rss_mb": round(src["rss"] / 1024, 1), "state": STATE_MAP.get(src["st"][0], src["st"])})
    order = {"主删除进程": 0, "分工进程 1/2": 1, "分工进程 2/3": 2, "防休眠": 3, "系统自带清理": 4}
    return sorted(rows, key=lambda r: order.get(r["name"], 9))

def rate(seconds):
    now = hist[-1]
    for h in reversed(hist):
        if now[0] - h[0] >= seconds:
            dt = now[0] - h[0]
            return (h[1] - now[1]) / dt * 60 if dt else 0
    return 0

def collector():
    while True:
        try:
            s = sample()
            with lock:
                hist.append(list(s))
                if len(hist) % 15 == 0:
                    json.dump(hist, open(STATE, "w"))
        except Exception as e:
            print("sample error", e)
        time.sleep(2)

class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k): super().__init__(*a, directory=HERE, **k)
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith("/stats"):
            with lock:
                h = list(hist)
            if not h:
                body = b"{}"
            else:
                step = max(1, len(h) // 600)
                ds = h[::step] + ([h[-1]] if (len(h) - 1) % step else [])
                r1, r10 = rate(60), rate(600)
                remain = max(0, h[-1][1] - FLOOR)
                eta = remain / (r10 / 60) if r10 > 0 else None
                body = json.dumps({
                    "ts": h[-1][0], "iused": h[-1][1], "avail_kb": h[-1][2],
                    "start_total": START_TOTAL, "floor": FLOOR, "start_ts": START_TS,
                    "deleted": START_TOTAL - h[-1][1], "remain": remain,
                    "rate_1m": r1, "rate_10m": r10, "eta_s": eta,
                    "load": os.getloadavg(), "procs": procs(), "history": ds,
                }).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(body)
            return
        if self.path == "/": self.path = "/index.html"
        super().do_GET()

if __name__ == "__main__":
    if os.path.exists(STATE):
        try: hist = json.load(open(STATE))
        except Exception: hist = []
    threading.Thread(target=collector, daemon=True).start()
    print(f"看板: http://localhost:{PORT}  基线文件数 {START_TOTAL:,}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
