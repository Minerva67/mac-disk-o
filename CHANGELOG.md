# 更新日志

## v2.0 · 2026-10-06

这一版起因是一次真实事故：系统数据 281G，可是能找到的大文件加起来只有 190G。查到最后，是一个失控脚本往 `/tmp` 里写了 5300 万张小 PNG。v1 的六层扫描专找大文件，碰上这种情况查不出来，所以补了专项诊断和删除方案。

### 新增
- **小文件堆积专项**：针对「系统数据几百 G 却找不到大文件」
  - 诊断：先用 `df -i` 看文件总数（正常两三百万，几千万就是堆积），再查 `/private/var/dirs_cleaner` 和后台清理进程 `deleted_helper`
  - `scripts/bulk_delete.sh` + `scripts/stream_delete.py`：暂停 deleted_helper，3 个分片并行流式删除，用 caffeinate 防休眠，删完恢复 helper。中断后重跑会接着删，重复启动会先停掉旧进程
  - 实测速度：每分钟 800 个 → 17.5 万个，快了 200 多倍
  - 永久删除的命令只交给用户自己执行，Claude 不代跑
- **边清理边玩看板** `dashboard/`：`python3 dashboard/server.py`，打开 http://localhost:8765
  - 已腾出空间、实时曲线、进程表，每 2 秒采样一次，只读
  - 进度小恐龙跟着真实删除进度跑，踩仙人掌时弹出本轮删除数
  - 小游戏：小恐龙跑酷（F 喷火）、消消乐、飞行棋、俄罗斯方块、剧情模式（5 章，按真实清理进度解锁）
- **README**：起因、安装方法、实测数据、注意事项
- 扫描新增 ①b 层：Chrome 的 `code_sign_clone` 堆积

### 调整
- 核心原则新增一条：系统数据异常时先看 `df -i`
- 提醒：`code_sign_clone` 用 du 看有几百 G，但它是 APFS 克隆，删了几乎不释放空间，别当成大头
- uv / npm / pip 包缓存改成「问一句」，不再默认清（常写代码的人清了要重新下载）
- 孤儿数据扫描跳过 `com.apple*`、MobileSync、Knowledge 等系统目录，减少误报
- 仓库开源：github.com/Minerva67/mac-disk-o

### 踩过的坑（已写进 SKILL.md）
- 几千万个文件时，`rm -rf`、`find -delete`、`ls -l` 都会卡死
- 同一个目录同一时间只能跑一套删除，5 个进程一起遍历会把电脑卡死
- 恢复模式不会更快

## v1.0 · 2026-09-23
- 六层扫描（纯缓存 → 孤儿数据 → 大镜像 → 聊天容器 → Downloads → 长期未用 App）
- 先测 TCC 可读性，读不到的数字标成下限
- 四档清单，确认一次；一律移进废纸篓
- `scripts/scan_disk.py`、`scripts/trash.sh`
