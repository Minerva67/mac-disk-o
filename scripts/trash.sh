#!/usr/bin/env bash
# trash.sh — 把点名的路径逐条移进废纸篓(走 Finder,可"放回原处")。绝不硬删。
# 用法: bash trash.sh "<path1>" "<path2>" ...
set -u
[ $# -eq 0 ] && { echo "用法: trash.sh <path>..."; exit 1; }
tot=0
for p in "$@"; do
  [ -e "$p" ] || { echo "跳过(不存在): $p"; continue; }
  kb=$(du -sk "$p" 2>/dev/null | cut -f1)
  osascript -e "tell application \"Finder\" to delete POSIX file \"$p\"" >/dev/null 2>&1
  if [ -e "$p" ]; then echo "✗ 未能移走(可能是 root 归属,请在访达里拖): $p"
  else tot=$((tot+kb)); printf "✓ %7.2fG  %s\n" "$(echo "$kb/1048576" | bc -l)" "$p"; fi
done
printf -- "---- 已移入废纸篓合计 %.1fG;清倒废纸篓后才真正释放。\n" "$(echo "$tot/1048576" | bc -l)"
