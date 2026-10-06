#!/usr/bin/env bash
# 删除"几千万小文件"目录的完整一键版：停旧进程 → 暂停系统 deleted_helper → N 个流式分片并行 → 防休眠 → 恢复 helper。
# 用法（用户本人执行）: sudo bash bulk_delete.sh <目录> [并行数=3]
# 可反复执行：中断了再跑会从剩下的接着删；重复启动会先把旧的停掉，保证只有一套在跑。
set -u
P="${1:?用法: sudo bash bulk_delete.sh <目录> [并行数]}"; W="${2:-3}"
HERE="$(cd "$(dirname "$0")" && pwd)"
[ "$(id -u)" = 0 ] || { echo "需要 sudo"; exit 1; }
[ -d "$P" ] || { echo "目录不存在，无需再删: $P"; exit 0; }
pkill -f stream_delete.py 2>/dev/null && { echo "已停掉旧的删除进程"; sleep 3; }
H=$(pgrep -x deleted_helper || true)
[ -n "$H" ] && kill -STOP $H && echo "已暂停系统清理进程 deleted_helper($H)，否则它独占磁盘、速度掉 100 倍"
trap '[ -n "$H" ] && kill -CONT $H 2>/dev/null; pkill -f stream_delete.py' INT TERM
for ((k=1; k<W; k++)); do python3 "$HERE/stream_delete.py" "$P" "$W" "$k" & done
caffeinate -i -s python3 "$HERE/stream_delete.py" "$P" "$W" 0
wait
[ -n "$H" ] && kill -CONT $H 2>/dev/null && echo "已恢复系统清理进程"
df -h /System/Volumes/Data | tail -1
