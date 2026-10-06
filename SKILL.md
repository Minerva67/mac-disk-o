---
name: mac-disk-cleanup
description: 给整台 Mac 腾磁盘空间的完整打法（不是整理某个文件夹，那是 folder-organizer）。按「纯缓存 → 已删App孤儿数据 → 开发工具大镜像 → 聊天App容器 → Downloads过程件 → 长期未用App」六层由安全到危险扫描，先测 TCC 挡住的 iPhone备份/照片/信息/邮件能否读（读不到就声明数字是下限），出一张「安全可删 / 需在App内清 / 系统挡住需授权 / 别碰」四档清单让用户一次确认，然后一律移废纸篓不硬删。另含「系统数据几百G但找不到文件」的小文件堆积专项（df -i 诊断 → 暂停 deleted_helper → 流式分片并行删），并自带「边清理边玩」实时游戏看板（进度小恐龙、喷火踩仙人掌、消消乐/飞行棋/俄罗斯方块/剧情模式）。凡用户说「系统数据几百G、删了文件空间不回来、电脑/磁盘/储存空间满了、清理一下 Mac、系统数据怎么这么大、腾点空间、C盘满了(Mac)、帮我清内存(实指磁盘)」时使用。查重放最后做，个人 Mac 上重复文件通常只有几十MB～1G。
---

# Mac Disk Cleanup · 给整台机子腾空间

## 先说清一件事：磁盘 ≠ 内存
用户说「清内存」十有八九指**储存空间/磁盘**。第一句就纠正口径，并用 `df -h /System/Volumes/Data` 报一个「已用/可用/占比」基线。

## 核心反常识（实战 82G 沉淀）
1. **别从查重开始。** 个人 Mac 的字节级重复通常 <1G；大头在「系统数据」里的 App 缓存、已删 App 孤儿数据、开发工具镜像。查重是最后一步。
2. **「系统数据 200G+」的本体终端读不到。** iPhone 备份 `~/Library/Application Support/MobileSync/Backup`、照片图库、`~/Library/Messages`、`~/Library/Mail` 被 TCC 挡住，`du` **静默漏算**（实战：家目录算 105G、实际 345G）。必须先测可读性，读不到就明说「以下数字是下限」，导向 系统设置→通用→储存空间 面板，或让用户开 完全磁盘访问→(本App)。
3. **「系统数据」几百G、却找不到大文件 → 先看文件总数 `df -i`。** 正常 Mac 两三百万个；几千万就是**小文件堆积**，见下方专项。⚠️ Chrome 的 `code_sign_clone` 堆积看着 du 几百G，其实是 APFS 克隆共享数据块，**删了零释放**，别当大头。
4. **安全护栏是用户敢放手的前提**（见下）。

## 流程

### 0 · 基线 + 可读性
```
python3 scripts/scan_disk.py            # 一次跑完 1-4 层，末尾给四档清单 + JSON
```
脚本会：df 基线；测 TCC 目录可读性；家目录/`~/Library` 大头；六层候选；输出四档。

### 1 · 六层候选（由安全到危险）
| 层 | 位置 | 判定 | 动作 |
|---|---|---|---|
| ① 纯缓存 | `~/Library/Caches/*`、`~/.npm/_cacache`、`~/.cache`、`~/Library/Application Support/Google/Chrome/<Profile>/Service Worker`、各 Electron App 的 `Cache`/`Code Cache`/`GPUCache` | 永远安全，App 自动重建；清 Chrome SW **不退登录**。例外：uv/npm/pip 包缓存对常写代码的用户别默认清，放「问一句」 | 安全可删 |
| ② 孤儿数据 | `~/Library/Application Support/<x>`、`~/.<x>` | `/Applications` 与 `~/Applications` 里**没有**对应 App | 安全可删（删前**重新核实**，用户会中途自己删 App） |
| ③ 大镜像 | Claude `Application Support/Claude/vm_bundles/claudevm.bundle`、Docker.raw、Xcode `DerivedData`/`CoreSimulator`、`~/.gemini`、ollama/lmstudio 模型 | 可重建但耗时/流量 | 问一句「用不用」再删 |
| ④ 聊天容器 | `~/Library/Containers/com.tencent.xinWeChat`、`com.bytedance.macos.feishu` | 手动 rm 会丢聊天记录 | **只在 App 内清**（微信→设置→通用→存储空间；飞书→设置→存储空间） |
| ⑤ Downloads 过程件 | `.dmg/.pkg` 安装包、`(1)/(2)/ 2` 重下、zip+解压目录并存、渲染/生成产物、屏幕录制 | 先按名字扫敏感件拎出 | 安全可删（走 folder-organizer 那套分桶） |
| ⑥ 长期未用 App | `mdls -raw -name kMDItemLastUsedDate` 为空或 >10 个月 | root 归属（iMovie/GarageBand/Pages）终端删不了 | 你的 App → Finder delete；root 的让用户访达拖 |

### 2 · 出四档清单（🚪 闸门）
每条标体积。四档：**安全可删 / 需在App内点 / 系统挡住需授权 / 别碰**。一次确认，别挤牙膏。

### 3 · 执行
```
bash scripts/trash.sh "<path1>" "<path2>" ...   # 逐条点名，走 Finder 移废纸篓，可恢复
```
- 一律移废纸篓，**不硬删**；空间在用户清倒废纸篓后才释放，要明说。
- 清浏览器前先退出它（`osascript -e 'tell application "Google Chrome" to quit'` 会超时也没关系，数据照样能移）。
- 自动模式会拦「通配扫描 + 批量 mv」，**逐条点名或走 Finder delete**。

### 4 · 收尾提醒
清倒废纸篓 · 重启浏览器 · 微信/飞书 App 内清 · 储存空间面板看 iPhone 备份/照片（访达→iPhone→管理备份 删旧备份）。

## 护栏（血泪）
- 批量前 `grep -iE '发票|简历|合同|薪|身份证|护照|银行|凭证'` 扫名字，敏感件**拎出不动**并主动告知。
- 删孤儿数据前重新 `ls /Applications` 核实——用户会中途删东西，别按旧扫描结果动手（实战一度误判「文件神秘消失」，其实是用户自己删的）。
- 名字相近的「版本残留」和 `(1)`/` 2` 后缀启发式**都会误报**（S02E03 vs E04、连拍照片）；只信字节 md5 与内容指纹。
- `du -s` 与 `-d1` 同用会**静默空输出**；`~/.Trash` 被 TCC 挡 `ls` 但 `mv` 进去可用。
- 用户自己的 App（stat 归属 = 本人）可 Finder delete；root 归属的需要密码，**不代输**，让用户拖。

## 专项：系统数据几百G、找不到大文件 = 小文件堆积（实战 10-06，5300 万个 / 240G）

**诊断**（全部只读、不用 sudo）
1. `df -i /System/Volumes/Data` 看 iused。远超 500 万 → 小文件堆积。`find -size +1G` 找不到它，因为每个只有几 KB。
2. 头号嫌疑 `/private/var/dirs_cleaner/*/`：重启时系统把 `/tmp` 挪进来等后台删，删不动就越积越多（实战是一个失控脚本往 /tmp 写了 5300 万张 PNG）。需要用户在终端 `sudo python3 -c` 用 `os.scandir` + `itertools.islice` **只取前 15 项**看一眼结构。
3. 看系统清理进程 `ps -axo pid,state,etime,%cpu,comm | grep deleted_helper`：跑了几小时、CPU 十几%就是它在独占这个目录。

**删除**（永久删除 → 只给命令，由用户本人执行，Claude 不代跑）
```bash
sudo bash ~/.claude/skills/mac-disk-cleanup/scripts/bulk_delete.sh <目录> 3
```
脚本做的事：停旧进程 → `kill -STOP` 暂停 deleted_helper → 3 个流式分片并行删 → caffeinate 防休眠 → 删完恢复 helper。中断后重跑接着删；重复启动会先停旧的。

**实测速度与血泪**
| 做法 | 速度 | 结论 |
|---|---|---|
| `rm -rf` / `find -delete` / `ls -l` | 0（卡死） | fts 先把几千万条读进内存，**别用** |
| 低优先级 `taskpolicy -b` | 900/分 | 被系统限流，40 天删不完 |
| 流式单进程，helper 没停 | 800/分 | helper 独占磁盘 |
| 流式单进程 + **暂停 helper** | 9.5 万/分 | 提速 100 倍的关键 |
| 3 分片并行 | 17.5 万/分 | 最优；再加进程边际收益很小（6 个 ≈19 万） |
- **同一时刻只许一套删除进程碰这个目录。** 5 个 rm/find/统计同时遍历，把电脑卡死过一次。自己开的统计命令用完必须确认停掉（sudo 起的要用户 kill）。
- 恢复模式不更快：里面只有 rm（fts），会撑爆内存。
- 空间随删随回；Finder 拖废纸篓不行（root 目录点不进，清倒时同样慢）。

## 边清理边玩：实时游戏看板
删除跑起来后开看板（只读采样 df/ps，每 2 秒刷新；启动时自动取文件数基线）：
```bash
python3 ~/.claude/skills/mac-disk-cleanup/dashboard/server.py   # 默认 :8765，PORT= 可改
```
在 Claude 桌面版里，用 `.claude/launch.json` 配一个 `python3 <skill>/dashboard/server.py` 的预览项，再用 preview_start 打开。
- 主卡片：已腾出多少 GB（换算成电影、照片）+ 跑道进度：小恐龙跟着真实进度跑；每 2 秒踩扁一棵仙人掌，弹出"+本轮删除数"金币。
- 曲线：可用空间、删除速度（悬停显示数值）；进程表：主进程、分片进程、防休眠、被暂停的 helper。
- 游戏标签：🦖 小恐龙（空格跳、F 喷火烧仙人掌带惨叫，速度跟随删除速度）· 🧩 消消乐 · 🎲 飞行棋 · 🟨 俄罗斯方块 ·（📖 剧情模式：章节按真实清理进度解锁，有就加）。
- 用户口味：Knock 配色；要可爱、要即时反馈；放置类（饼干）被评"不好玩"已撤。游戏要和清理数据挂钩，不然用户会问"和看板有啥关系"。

## 给小白的产品形态
一键扫描 → 四档清单（每条标体积）→ 一次确认 → 全进废纸篓 → 提醒清倒废纸篓 + 重启浏览器。不给终端、不给命令、开头说清磁盘≠内存。
