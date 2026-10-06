#!/usr/bin/env python3
"""scan_disk.py — 一次跑完 Mac 腾空间的候选扫描，末尾给四档清单。只读，不删任何东西。
用法: python3 scan_disk.py [--json out.json]
"""
import os, sys, json, subprocess, re, time
H = os.path.expanduser("~")
def sh(c):
    try: return subprocess.run(c, capture_output=True, text=True, timeout=600).stdout
    except Exception: return ""
def du(p):
    try: return int(sh(["du","-sk",p]).split()[0])*1024
    except Exception: return 0
def h(n):
    for u in ("B","K","M","G","T"):
        if n<1024: return f"{n:.0f}{u}" if u=="B" else f"{n:.1f}{u}"
        n/=1024
def readable(p): 
    try: os.listdir(p); return True
    except Exception: return False
out={"safe":[],"in_app":[],"blocked":[],"keep":[],"ask":[]}
def add(k,path,note=""): 
    b=du(path) if os.path.exists(path) else 0
    if b: out[k].append({"path":path,"bytes":b,"note":note})

print("=== 0 基线 ===")
print(sh(["df","-h","/System/Volumes/Data"]))
print("=== 0 TCC 可读性(读不到 → 下面所有数字都是下限) ===")
for p,n in [(H+"/Library/Application Support/MobileSync/Backup","iPhone 备份"),
            (H+"/Pictures/Photos Library.photoslibrary","照片图库"),
            (H+"/Library/Messages","信息附件"),(H+"/Library/Mail","邮件"),(H+"/.Trash","废纸篓")]:
    if not os.path.exists(p): continue
    if readable(p): print(f"  可读 {h(du(p)):>7}  {n}")
    else: print(f"  🔒挡住        {n}  → {p}"); out["blocked"].append({"path":p,"note":n})

print("\n=== ① 纯缓存 ===")
for p in [H+"/Library/Caches"]:
    if os.path.isdir(p): add("safe",p,"纯缓存,自动重建"); print(f"  {h(du(p)):>7}  {p}")
chrome=H+"/Library/Application Support/Google/Chrome"
if os.path.isdir(chrome):
    for prof in os.listdir(chrome):
        for sub in ("Service Worker","Code Cache","GPUCache"):
            p=os.path.join(chrome,prof,sub)
            if os.path.isdir(p) and du(p)>50*1024*1024:
                add("safe",p,"Chrome 缓存,不退登录"); print(f"  {h(du(p)):>7}  Chrome/{prof}/{sub}")

print("\n=== ①b 代码签名克隆堆积(Chrome bug,常是系统数据本体) ===")
X=subprocess.run(["getconf","DARWIN_USER_TEMP_DIR"],capture_output=True,text=True).stdout.strip().rstrip("/")[:-1]+"X"
if os.path.isdir(X):
    for e in os.listdir(X):
        if e.endswith(".code_sign_clone"):
            p=os.path.join(X,e); b=du(p)
            if b>500*1024*1024: add("safe",p,"code_sign_clone 堆积,App 退出后可删(APFS 克隆,实释放<du)"); print(f"  {h(b):>7}  {e}  ({len(os.listdir(p))} 份)")

print("\n=== ② 已删 App 的孤儿数据 ===")
apps=set()
for d in ("/Applications", H+"/Applications"):
    if os.path.isdir(d):
        for a in os.listdir(d):
            if a.endswith(".app"): apps.add(a[:-4].lower())
AS=H+"/Library/Application Support"
if os.path.isdir(AS):
    for e in sorted(os.listdir(AS)):
        p=os.path.join(AS,e); b=du(p)
        if b<100*1024*1024: continue
        key=e.lower().replace("com.","").split(".")[-1]
        if e.lower() in apps or key in apps or any(key in a or a in key for a in apps if len(a)>3):
            continue
        if e.startswith("com.apple") or e in ("MobileSync","Caches","Knowledge","Google","Claude","Apple","com.apple.TCC","CrashReporter","Mozilla","Microsoft","AddressBook","CloudDocs"): continue
        add("ask",p,"App 似乎已不在,请核实后再删"); print(f"  {h(b):>7}  {e}   (未找到同名 App)")

print("\n=== ③ 大镜像(可重建,问一句) ===")
for p,n in [(H+"/Library/Application Support/Claude/vm_bundles","Claude 沙箱 VM"),
            (H+"/Library/Containers/com.docker.docker","Docker"),(H+"/Library/Developer/Xcode/DerivedData","Xcode DerivedData"),
            (H+"/Library/Developer/CoreSimulator","iOS 模拟器"),(H+"/.gemini","Gemini/Antigravity"),(H+"/.ollama","ollama 模型"),(H+"/.lmstudio","LM Studio 模型")]:
    if os.path.exists(p) and du(p)>200*1024*1024: add("ask",p,n); print(f"  {h(du(p)):>7}  {n}  {p}")

print("\n=== ④ 聊天容器(只能 App 内清) ===")
for p,n in [(H+"/Library/Containers/com.tencent.xinWeChat","微信"),(H+"/Library/Containers/com.bytedance.macos.feishu","飞书")]:
    if os.path.exists(p): add("in_app",p,n); print(f"  {h(du(p)):>7}  {n}")

print("\n=== ⑥ 长期未用 App(>300天 或 从未) ===")
now=time.time()
for d in ("/Applications", H+"/Applications"):
    if not os.path.isdir(d): continue
    for a in sorted(os.listdir(d)):
        if not a.endswith(".app"): continue
        p=os.path.join(d,a)
        last=sh(["mdls","-raw","-name","kMDItemLastUsedDate",p]).strip()
        owner=sh(["stat","-f","%Su",p]).strip()
        never = last in ("(null)","")
        old=False
        if not never:
            try: old = (now-time.mktime(time.strptime(last[:19],"%Y-%m-%d %H:%M:%S")))>300*86400
            except Exception: pass
        if never or old:
            tag="从未" if never else last[:10]
            note=f"上次 {tag}, 归属 {owner}" + ("(root,需用户访达拖)" if owner=="root" else "")
            add("ask",p,note); print(f"  {h(du(p)):>7}  {a:30} {note}")

print("\n=== 家目录/Library 大头(参考) ===")
print(sh(["sh","-c",f"du -h -d1 '{H}/Library' 2>/dev/null | sort -rh | head -8"]))

print("\n================ 四档清单 ================")
for k,t in [("safe","🟢 安全可删(移废纸篓)"),("ask","🟡 需你确认(孤儿/镜像/未用App)"),("in_app","🔵 只能在 App 内清"),("blocked","🔒 系统挡住,需授权或用储存空间面板")]:
    items=out[k]; tot=sum(i.get("bytes",0) for i in items)
    print(f"\n{t}  共 {h(tot)}")
    for i in sorted(items,key=lambda x:-x.get("bytes",0)):
        print(f"  {h(i.get('bytes',0)):>7}  {i['path']}   {i.get('note','')}")
if "--json" in sys.argv:
    json.dump(out,open(sys.argv[sys.argv.index("--json")+1],"w"),ensure_ascii=False,indent=1)
