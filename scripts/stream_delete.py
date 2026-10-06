#!/usr/bin/env python3
"""流式删除超大平铺目录（几百万～几千万文件）。读一个删一个，不预读整个目录，不会撑爆内存。
可多进程分工：按文件名哈希分片，每个进程只删自己那一份，互不抢同一个文件。

用法（必须由用户本人在终端以 sudo 运行；Claude 不代跑永久删除）:
  sudo python3 stream_delete.py <目录>                # 单进程，删全部
  sudo python3 stream_delete.py <目录> <总份数> <编号>  # 分片，例: 3 0 / 3 1 / 3 2
只删普通文件；子目录跳过（打印数量）。可随时 Ctrl+C，已删的不会回来，重跑即接着删。
"""
import os, sys, time, zlib

if len(sys.argv) not in (2, 4):
    sys.exit(__doc__)
P = os.path.abspath(sys.argv[1])
N, K = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) == 4 else (1, 0)
for bad in ("/", "/System", "/Users", "/Applications", "/Library", os.path.expanduser("~")):
    if P == bad:
        sys.exit(f"拒绝删除顶层目录: {P}")
os.chdir(P)
tag = f"[{K + 1}/{N}] " if N > 1 else ""
n = dirs = 0
t0 = time.time()
while True:
    got = 0
    for e in os.scandir("."):
        if N > 1 and zlib.crc32(e.name.encode()) % N != K:
            continue
        if e.is_dir(follow_symlinks=False):
            dirs += 1
            continue
        try:
            os.unlink(e.name)
            n += 1
            got += 1
            if n % 50000 == 0:
                dt = time.time() - t0
                print(f"{tag}已删 {n:,}  速度 {int(n / dt)}/s", flush=True)
        except OSError:
            pass
    if got == 0:
        break
    dirs = 0
print(f"{tag}done {n:,}" + (f"（跳过子目录 {dirs} 个）" if dirs else ""), flush=True)
if N == 1 or K == 0:
    try:
        os.chdir("/")
        os.rmdir(P)
        print("目录已移除")
    except OSError:
        pass
