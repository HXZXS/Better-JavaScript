# BJS 数据接力 6.0.3.γ
# 开发者 HXZXS

import sys, os, json, time, shutil, subprocess, urllib.parse, urllib.request
import threading, tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime
import traceback, pystray
from PIL import Image, ImageDraw, ImageTk
from flask import Flask, request, jsonify
from flask_cors import CORS
import webbrowser, re, hashlib, zipfile, platform, uuid as uuid_lib, secrets
from collections import deque
import logging
from logging.handlers import RotatingFileHandler
import tempfile

#  路径 
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
if os.name == 'nt':
    USER_DATA = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'BJS')
else:
    USER_DATA = os.path.join(os.path.expanduser('~'), '.config', 'bjs')
os.makedirs(USER_DATA, exist_ok=True)

LOG_PATH = os.path.join(USER_DATA, "bjs.log")
DOWNLOAD_DIR = os.path.join(USER_DATA, "downloads")
ICON_PATH = os.path.join(BASE_DIR, "logo.ico") or os.path.join(BASE_DIR, "logo.png")
DATA_DIR = os.path.join(USER_DATA, "data")
TASKS_FILE = os.path.join(DATA_DIR, "tasks.json")
VERSIONS_ROOT = os.path.join(DATA_DIR, "versions")
WATCH_CONFIG_FILE = os.path.join(DATA_DIR, "watches.json")
CACHE_FILE = os.path.join(DATA_DIR, "license_cache.json")
FIRST_RUN_FLAG = os.path.join(USER_DATA, "first_run.flag")
for d in [DOWNLOAD_DIR, DATA_DIR, VERSIONS_ROOT]:
    os.makedirs(d, exist_ok=True)

HTTP_PORT = 8765
MAIN_ROOT = None
LICENSE_STATUS = {"valid": False, "key": None, "expire_time": None, "msg": None}
CLIPBOARD_HISTORY = deque(maxlen=100)
VERSION = "6.0.3.γ"

#  更新 
UPDATE_URL = "https://bjs.rth1.xyz/up.json"
GITHUB_RELEASES = "https://github.com/HXZXS/Better-JavaScript/releases"

#  日志 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('BJS')
logger.setLevel(logging.INFO)
fmt = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
console = logging.StreamHandler()
console.setFormatter(fmt)
logger.addHandler(console)
try:
    fh = RotatingFileHandler(LOG_PATH, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
    fh.setFormatter(fmt)
    logger.addHandler(fh)
except:
    pass

def log(msg, level="INFO", extra=None):
    if extra:
        msg += f" | {json.dumps(extra, ensure_ascii=False)}"
    getattr(logger, level.lower() if level.lower() in ('error','warning','info') else 'info')(msg)

#  开机自启 
def setup_autostart():
    if os.path.exists(FIRST_RUN_FLAG):
        return
    try:
        if os.name == 'nt':
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE)
            exe_path = sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]
            if getattr(sys, 'frozen', False):
                cmd = f'"{exe_path}"'
            else:
                cmd = f'"{sys.executable}" "{exe_path}"'
            winreg.SetValueEx(key, "BJSDataRelay", 0, winreg.REG_SZ, cmd)
            winreg.CloseKey(key)
            log("开机自启已设置", "INFO")
        else:
            autostart_dir = os.path.expanduser("~/.config/autostart")
            os.makedirs(autostart_dir, exist_ok=True)
            desktop = os.path.join(autostart_dir, "bjs.desktop")
            exe_path = sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]
            if getattr(sys, 'frozen', False):
                exec_cmd = f'"{exe_path}"'
            else:
                exec_cmd = f'"{sys.executable}" "{exe_path}"'
            content = f"""[Desktop Entry]
Type=Application
Name=BJS 数据接力
Exec={exec_cmd}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
"""
            with open(desktop, 'w') as f:
                f.write(content)
            log("开机自启已设置 (Linux)", "INFO")
        with open(FIRST_RUN_FLAG, 'w') as f:
            f.write('1')
    except Exception as e:
        log("设置开机自启失败", "ERROR", {"err": str(e)})

#  召回 
RECALL_URL = "https://bjs.rth1.xyz/Recall.json"
KEY_EXE = "BJS developer key.exe"
UNINS_EXE = "unins000.exe"
ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"

def recall_check():
    try:
        req = urllib.request.Request(RECALL_URL, headers={'User-Agent': ua})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
            return data.get('code', -1), data.get('recall', ''), data.get('msg', '')
    except Exception as e:
        log("召回检查失败", "WARN", {"err": str(e)})
        return -1, '', str(e)

def handle_recall():
    code, recall, msg = recall_check()
    if code != 1:
        log("无需召回", "INFO")
        return
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    messagebox.showwarning("召回通告", f"{msg}\n\n程序即将执行召回操作。", parent=root)
    root.destroy()

    if recall == "main":
        unins = os.path.join(BASE_DIR, UNINS_EXE)
        if os.path.exists(unins):
            log("执行卸载", "INFO", {"path": unins})
            try:
                if os.name == 'nt':
                    subprocess.Popen([unins], shell=True)
                else:
                    subprocess.Popen([unins])
            except Exception as e:
                log("执行卸载失败", "ERROR", {"err": str(e)})
        else:
            log("卸载程序不存在", "WARN", {"path": unins})
        sys.exit(0)
    elif recall == "key":
        key_path = os.path.join(BASE_DIR, KEY_EXE)
        if os.path.exists(key_path):
            log("删除卡密服务", "INFO", {"path": key_path})
            try:
                os.remove(key_path)
            except Exception as e:
                log("删除卡密服务失败", "ERROR", {"err": str(e)})
        else:
            log("卡密服务不存在", "WARN", {"path": key_path})

#  更新检查 
def get_updates():
    try:
        req = urllib.request.Request(UPDATE_URL, headers={'User-Agent': ua})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
        ver = data.get('version', '')
        if ver and ver != VERSION:
            url = data.get('url', '')
            msg = data.get('msg', '')
            if MAIN_ROOT:
                MAIN_ROOT.after(0, lambda: show_update_win(ver, url, msg))
        else:
            log("已是最新版本", "INFO")
    except Exception as e:
        log("检查更新失败", "WARN", {"err": str(e)})

def show_update_win(version, url, msg):
    win = tk.Toplevel(MAIN_ROOT)
    win.title("发现新版本")
    win.geometry("460x360")
    win.resizable(False, False)
    win.attributes('-topmost', True)
    win.update_idletasks()
    w, h = win.winfo_width(), win.winfo_height()
    x = (win.winfo_screenwidth() - w)//2
    y = (win.winfo_screenheight() - h)//2
    win.geometry(f"{w}x{h}+{x}+{y}")

    main = ttk.Frame(win, padding=20)
    main.pack(fill=tk.BOTH, expand=True)

    ttk.Label(main, text="📦 发现新版本", font=("微软雅黑", 16, "bold"), foreground="#2b6f9e").pack(pady=(0,5))
    ttk.Label(main, text=f"最新版本: {version}", font=("微软雅黑", 11)).pack(pady=(0,10))

    log_frame = ttk.LabelFrame(main, text="更新日志", padding=8)
    log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
    log_text = tk.Text(log_frame, height=6, wrap=tk.WORD, font=("微软雅黑", 10))
    log_text.pack(fill=tk.BOTH, expand=True)
    if msg:
        lines = msg.split('|')
        display = '\n'.join(lines)
    else:
        display = "暂无更新日志"
    log_text.insert('1.0', display)
    log_text.config(state=tk.DISABLED)

    progress_var = tk.DoubleVar()
    progress = ttk.Progressbar(main, variable=progress_var, maximum=100, length=350)
    progress.pack(pady=8)
    progress.pack_forget()

    status_label = ttk.Label(main, text="", font=("微软雅黑", 9))
    status_label.pack(pady=(0,5))

    btn_frame = ttk.Frame(main)
    btn_frame.pack(pady=10)

    def open_github():
        webbrowser.open(GITHUB_RELEASES)

    def start_download():
        if not url:
            messagebox.showerror("错误", "下载地址无效", parent=win)
            return
        github_btn.config(state=tk.DISABLED)
        update_btn.config(state=tk.DISABLED)
        progress.pack(pady=8)
        status_label.config(text="正在下载...")

        def download_thread():
            try:
                tmp_dir = tempfile.gettempdir()
                filename = os.path.basename(url) or "bjs_setup.exe"
                save_path = os.path.join(tmp_dir, filename)
                def report_hook(block_num, block_size, total_size):
                    if total_size > 0:
                        percent = min(100, int(block_num * block_size * 100 / total_size))
                        progress_var.set(percent)
                        win.update_idletasks()
                urllib.request.urlretrieve(url, save_path, reporthook=report_hook)
                status_label.config(text="下载完成，正在启动安装...")
                if os.name == 'nt':
                    subprocess.Popen([save_path], shell=True)
                else:
                    subprocess.Popen([save_path])
                win.after(500, lambda: sys.exit(0))
            except Exception as e:
                win.after(0, lambda: messagebox.showerror("下载失败", str(e), parent=win))
                win.after(0, lambda: status_label.config(text="下载失败"))
                win.after(0, lambda: github_btn.config(state=tk.NORMAL))
                win.after(0, lambda: update_btn.config(state=tk.NORMAL))
                win.after(0, lambda: progress.pack_forget())

        threading.Thread(target=download_thread, daemon=True).start()

    github_btn = ttk.Button(btn_frame, text="GitHub Releases", command=open_github)
    github_btn.pack(side=tk.LEFT, padx=5)
    update_btn = ttk.Button(btn_frame, text="立即更新", command=start_download)
    update_btn.pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="稍后", command=win.destroy).pack(side=tk.LEFT, padx=5)

#  卡密验证 
LICENSE_SERVER = "https://lckey.rth1.xyz/"

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_cache(data):
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except:
        pass

def online_check(key, device_id):
    url = f"{LICENSE_SERVER}?key={urllib.parse.quote(key)}&uuid={urllib.parse.quote(device_id)}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': ua, 'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
            if data.get("code") == 200:
                expire = data.get("data", {}).get("expireTime")
                return True, expire, data.get("msg")
            else:
                return False, None, data.get("msg")
    except Exception as e:
        log("联网验证异常", "ERROR", {"err": str(e)})
        return False, None, str(e)

def verify_license(key):
    if not key or not key.strip():
        return False, {"msg": "卡密为空"}
    key = key.strip()
    device_id = get_hardware_id()
    cache = load_cache()
    if cache.get("key") == key and cache.get("uuid") == device_id:
        expire = cache.get("expire_time")
        if expire and expire > int(time.time() * 1000):
            log("使用缓存授权", "INFO", {"key": key})
            return True, {"key": key, "uuid": device_id, "expire_time": expire, "msg": "缓存有效"}
    ok, expire, msg = online_check(key, device_id)
    if ok and expire and expire > int(time.time() * 1000):
        save_cache({"key": key, "uuid": device_id, "expire_time": expire, "verified_at": int(time.time())})
        return True, {"key": key, "uuid": device_id, "expire_time": expire, "msg": msg}
    else:
        return False, {"msg": msg or "验证失败"}

def get_hardware_id():
    parts = []
    if os.name == 'nt':
        try:
            import wmi
            c = wmi.WMI()
            for cpu in c.Win32_Processor():
                if cpu.ProcessorId:
                    parts.append(f"cpu:{cpu.ProcessorId}"); break
            for board in c.Win32_BaseBoard():
                if board.SerialNumber and board.SerialNumber.strip():
                    parts.append(f"board:{board.SerialNumber.strip()}"); break
            for disk in c.Win32_DiskDrive():
                if disk.SerialNumber and disk.SerialNumber.strip():
                    parts.append(f"disk:{disk.SerialNumber.strip()}"); break
            for bios in c.Win32_BIOS():
                if bios.SerialNumber and bios.SerialNumber.strip():
                    parts.append(f"bios:{bios.SerialNumber.strip()}"); break
        except:
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
                pid = winreg.QueryValueEx(key, "ProductId")[0]
                if pid: parts.append(f"pid:{pid}")
                winreg.CloseKey(key)
            except:
                pass
    else:
        for p in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
            if os.path.exists(p):
                try:
                    with open(p, 'r') as f:
                        mid = f.read().strip()
                        if mid:
                            parts.append(f"machineid:{mid}"); break
                except:
                    pass
    try:
        import platform
        parts.append(f"cpu:{platform.processor() or platform.machine()}")
        parts.append(f"sys:{platform.system()}{platform.release()}")
    except:
        pass
    if not parts:
        try:
            mac = uuid_lib.getnode()
            if mac != 0xffffffffffff:
                parts.append(f"mac:{mac}")
        except:
            pass
    if not parts:
        parts.append(f"fallback:{uuid_lib.uuid4()}")
    raw = "|".join(parts)
    h = hashlib.sha256(raw.encode()).hexdigest()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"

def is_advanced_allowed():
    return LICENSE_STATUS.get("valid", False)

def auth_on_start():
    cache = load_cache()
    if not cache.get("key"):
        log("无缓存卡密", "INFO")
        return
    key = cache["key"]
    device_id = get_hardware_id()
    ok, expire, msg = online_check(key, device_id)
    if ok and expire and expire > int(time.time() * 1000):
        LICENSE_STATUS.update({"valid": True, "key": key, "expire_time": expire, "msg": "验证通过"})
        save_cache({"key": key, "uuid": device_id, "expire_time": expire, "verified_at": int(time.time())})
        log("启动时卡密验证通过", "INFO", {"key": key})
    else:
        LICENSE_STATUS.update({"valid": False, "key": None, "expire_time": None, "msg": "验证失败"})
        if os.path.exists(CACHE_FILE):
            try: os.remove(CACHE_FILE)
            except: pass
        log("启动时卡密验证失败", "WARN", {"key": key, "msg": msg})

#  卡密服务进程 
def run_key_exe():
    key_path = os.path.join(BASE_DIR, KEY_EXE)
    if not os.path.exists(key_path):
        log("卡密服务不存在", "WARN", {"path": key_path})
        return
    try:
        if os.name == 'nt':
            res = subprocess.run(['tasklist', '/FI', f'IMAGENAME eq {KEY_EXE}'], capture_output=True, text=True, timeout=5)
            if KEY_EXE.lower() in res.stdout.lower():
                log("卡密服务已在运行", "INFO")
                return
        else:
            res = subprocess.run(['pgrep', '-f', KEY_EXE], capture_output=True, text=True)
            if res.returncode == 0:
                log("卡密服务已在运行", "INFO")
                return
    except Exception as e:
        log("检查卡密服务状态失败", "WARN", {"err": str(e)})
    try:
        if os.name == 'nt':
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.Popen([key_path], startupinfo=si)
        else:
            subprocess.Popen([key_path])
        log("启动卡密服务", "INFO", {"path": key_path})
    except Exception as e:
        log("启动卡密服务失败", "ERROR", {"err": str(e)})

def kill_key_exe():
    """退出时终止卡密进程"""
    try:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/f', '/im', KEY_EXE], capture_output=True, timeout=5)
        else:
            subprocess.run(['pkill', '-f', KEY_EXE], capture_output=True, timeout=5)
        log("已终止卡密服务", "INFO")
    except Exception as e:
        log("终止卡密服务失败", "WARN", {"err": str(e)})

#  安全路径 
def safe_path(p):
    if not p:
        return False
    p = os.path.normpath(p)
    if '..' in p or '~' in p:
        return False
    forbidden = ['C:\\Windows', 'C:\\System32', 'C:\\Program Files', 'C:\\ProgramData']
    if os.path.isabs(p):
        for f in forbidden:
            if p.lower().startswith(f.lower()):
                return False
        return True
    return '..' not in os.path.abspath(p)

#  对话框 
class DialogBox:
    def __init__(self, master, cfg):
        self.master = master
        self.cfg = cfg
        self.result = {}
        self.vars = {}
        self.build()
        self.window.grab_set()

    def build(self):
        title = self.cfg.get('title', '对话框')
        w, h = self.cfg.get('width', 0), self.cfg.get('height', 0)
        controls = self.cfg.get('controls', [])
        buttons = self.cfg.get('buttons', ['确定'])
        self.window = tk.Toplevel(self.master)
        self.window.title(title)
        if w > 0 and h > 0:
            self.window.geometry(f"{w}x{h}")
        self.window.attributes('-topmost', True)
        main = ttk.Frame(self.window, padding=10)
        main.pack(fill=tk.BOTH, expand=True)
        row = 0
        for ctrl in controls:
            ctype = ctrl.get('type', 'label')
            label = ctrl.get('label', '')
            default = ctrl.get('default', '')
            options = ctrl.get('options', [])
            cid = ctrl.get('id', f'ctrl_{row}')
            if ctype == 'label':
                ttk.Label(main, text=label, wraplength=400).grid(row=row, column=0, columnspan=2, sticky='w', pady=2)
                row += 1
            elif ctype == 'image':
                src = ctrl.get('src', '')
                if src:
                    try:
                        if src.startswith(('http://', 'https://')):
                            with urllib.request.urlopen(src, timeout=10) as r:
                                img = Image.open(io.BytesIO(r.read()))
                        else:
                            img = Image.open(src)
                        img.thumbnail((800, 600), Image.Resampling.LANCZOS)
                        photo = ImageTk.PhotoImage(img)
                        lbl = ttk.Label(main, image=photo)
                        lbl.image = photo
                        lbl.grid(row=row, column=0, columnspan=2, pady=5)
                    except:
                        ttk.Label(main, text=f"图片加载失败: {src}").grid(row=row, column=0, columnspan=2, pady=2)
                else:
                    ttk.Label(main, text="未指定图片").grid(row=row, column=0, columnspan=2, pady=2)
                row += 1
            elif ctype == 'entry':
                if label:
                    ttk.Label(main, text=label).grid(row=row, column=0, sticky='e', padx=5)
                var = tk.StringVar(value=default)
                ttk.Entry(main, textvariable=var, width=30).grid(row=row, column=1, sticky='w', pady=2)
                self.vars[cid] = var
                row += 1
            elif ctype == 'text':
                if label:
                    ttk.Label(main, text=label).grid(row=row, column=0, sticky='ne', padx=5)
                tw = scrolledtext.ScrolledText(main, height=ctrl.get('rows', 5), width=40)
                tw.insert('1.0', default)
                tw.grid(row=row, column=1, sticky='w', pady=2)
                self.vars[cid] = tw
                row += 1
            elif ctype == 'password':
                if label:
                    ttk.Label(main, text=label).grid(row=row, column=0, sticky='e', padx=5)
                var = tk.StringVar(value=default)
                ttk.Entry(main, textvariable=var, show='*', width=30).grid(row=row, column=1, sticky='w', pady=2)
                self.vars[cid] = var
                row += 1
            elif ctype == 'combobox':
                if label:
                    ttk.Label(main, text=label).grid(row=row, column=0, sticky='e', padx=5)
                var = tk.StringVar(value=default if default in options else (options[0] if options else ''))
                ttk.Combobox(main, textvariable=var, values=options, state='readonly', width=28).grid(row=row, column=1, sticky='w', pady=2)
                self.vars[cid] = var
                row += 1
            elif ctype == 'checkbox':
                if label:
                    ttk.Label(main, text=label).grid(row=row, column=0, sticky='ne', padx=5)
                frm = ttk.Frame(main)
                frm.grid(row=row, column=1, sticky='w', pady=2)
                vars_list = []
                for opt in options:
                    var = tk.BooleanVar(value=(opt in default if default else False))
                    ttk.Checkbutton(frm, text=opt, variable=var).pack(anchor='w')
                    vars_list.append((opt, var))
                self.vars[cid] = vars_list
                row += 1
            elif ctype == 'radio':
                if label:
                    ttk.Label(main, text=label).grid(row=row, column=0, sticky='ne', padx=5)
                frm = ttk.Frame(main)
                frm.grid(row=row, column=1, sticky='w', pady=2)
                var = tk.StringVar(value=default if default in options else (options[0] if options else ''))
                for opt in options:
                    ttk.Radiobutton(frm, text=opt, variable=var, value=opt).pack(anchor='w')
                self.vars[cid] = var
                row += 1
            elif ctype == 'progress':
                if label:
                    ttk.Label(main, text=label).grid(row=row, column=0, sticky='e', padx=5)
                var = tk.IntVar(value=ctrl.get('value', 0))
                ttk.Progressbar(main, variable=var, maximum=ctrl.get('maximum', 100), length=250).grid(row=row, column=1, sticky='w', pady=2)
                self.vars[cid] = var
                row += 1
            else:
                ttk.Label(main, text=f"未知控件: {ctype}").grid(row=row, column=0, columnspan=2, pady=2)
                row += 1
        btn_frame = ttk.Frame(self.window)
        btn_frame.pack(pady=10)
        for bt in buttons:
            ttk.Button(btn_frame, text=bt, command=lambda b=bt: self.on_button(b)).pack(side=tk.LEFT, padx=5)

    def on_button(self, bt):
        data = {}
        for cid, val in self.vars.items():
            if isinstance(val, (tk.StringVar, tk.IntVar, tk.BooleanVar)):
                data[cid] = val.get()
            elif isinstance(val, list):
                data[cid] = [opt for opt, var in val if var.get()]
            elif isinstance(val, tk.Text):
                data[cid] = val.get('1.0', 'end-1c')
            else:
                data[cid] = str(val)
        self.result = {'button': bt, 'values': data}
        self.window.destroy()

def show_dialog(cfg):
    try:
        if isinstance(cfg, str):
            cfg = json.loads(cfg)
        dlg = DialogBox(MAIN_ROOT, cfg)
        return dlg.run()
    except Exception as e:
        log("对话框异常", "ERROR", {"err": str(e)})
        return None

#  卡密输入窗口 
class LicenseWindow:
    def __init__(self, master):
        self.master = master
        self.result = None
        self.window = tk.Toplevel(master)
        self.window.title("BJS 数据接力 · 升级高级版")
        self.window.geometry("420x260")
        self.window.resizable(False, False)
        self.window.attributes('-topmost', True)
        self.window.update_idletasks()
        w, h = self.window.winfo_width(), self.window.winfo_height()
        x = (self.window.winfo_screenwidth() - w)//2
        y = (self.window.winfo_screenheight() - h)//2
        self.window.geometry(f"{w}x{h}+{x}+{y}")

        main = ttk.Frame(self.window, padding=30)
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text="🔑 输入卡密", font=("微软雅黑", 16, "bold"), foreground="#2b6f9e").pack(pady=(0,5))
        ttk.Label(main, text="粘贴或输入您的卡密，验证通过后解锁高级功能", font=("微软雅黑", 10), foreground="#6a8aa8").pack(pady=(0,20))

        self.key_var = tk.StringVar()
        entry = ttk.Entry(main, textvariable=self.key_var, font=("Consolas", 13), width=32)
        entry.pack(fill=tk.X, pady=5, ipady=4)
        entry.focus_set()
        entry.bind('<Return>', lambda e: self.do_verify())

        self.msg_var = tk.StringVar()
        self.msg_label = ttk.Label(main, textvariable=self.msg_var, font=("微软雅黑", 9), foreground="#cc0000")
        self.msg_label.pack(pady=(6, 12))

        btn_frame = ttk.Frame(main)
        btn_frame.pack(pady=5)
        self.verify_btn = ttk.Button(btn_frame, text="✓ 验证卡密", command=self.do_verify, width=14)
        self.verify_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="✕ 取消", command=self.cancel, width=10).pack(side=tk.LEFT, padx=5)

        self.processing = False
        self.window.protocol("WM_DELETE_WINDOW", self.cancel)

    def do_verify(self):
        if self.processing:
            return
        key = self.key_var.get().strip()
        if not key:
            self.msg_var.set("请输入卡密")
            return
        self.processing = True
        self.verify_btn.config(state='disabled', text='验证中…')
        self.msg_var.set("")
        def thread_verify():
            ok, info = verify_license(key)
            self.window.after(0, lambda: self.finish(ok, info))
        threading.Thread(target=thread_verify, daemon=True).start()

    def finish(self, ok, info):
        self.processing = False
        self.verify_btn.config(state='normal', text='✓ 验证卡密')
        if ok:
            self.msg_var.set("✅ 验证通过！")
            self.msg_label.config(foreground="#00aa00")
            self.result = {"key": info.get("key"), "expire": info.get("expire_time")}
            self.window.after(500, self.close)
        else:
            code = info.get("code")
            status = info.get("status")
            msg = info.get("msg", "验证失败")
            if code == 403 and status == "black":
                self.msg_var.set("✗ 卡密已拉黑")
            elif code == 410 or status == "expired":
                self.msg_var.set("✗ 卡密已过期")
            elif code == 403 and status == "bind":
                self.msg_var.set("✗ 已绑定其他设备")
            elif code == 404 or status == "invalid":
                self.msg_var.set("✗ 卡密无效")
            else:
                self.msg_var.set(f"✗ {msg}")
            self.msg_label.config(foreground="#cc0000")

    def cancel(self):
        self.result = None
        self.close()
    def close(self):
        self.window.destroy()
    def run(self):
        self.window.grab_set()
        self.window.wait_window()
        return self.result

#  基础API函数 
def open_path(path):
    if not path or not safe_path(path):
        return {"code": -1, "msg": "路径无效"}
    if not os.path.exists(path):
        return {"code": -1, "msg": f"路径不存在: {path}"}
    try:
        os.startfile(path) if os.name == 'nt' else subprocess.Popen(['open', path])
        return {"code": 0, "msg": "ok", "data": {"path": path}}
    except Exception as e:
        return {"code": -1, "msg": str(e)}

def run_prog(path, args=None, wait=False):
    if not path or not safe_path(path) or not os.path.exists(path):
        return {"code": -1, "msg": "程序路径无效"}
    cmd = [path] + (args.split() if args else [])
    try:
        if wait:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return {"code": 0, "data": {"returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}}
        else:
            subprocess.Popen(cmd)
            return {"code": 0, "msg": "已启动"}
    except Exception as e:
        return {"code": -1, "msg": str(e)}

def show_msg(text, typ="info", title="来自网页", image=None, w=0, h=0):
    if image:
        cfg = {'title': title, 'width': w or 500, 'height': h or 400,
               'controls': [{'type': 'image', 'src': image}, {'type': 'label', 'text': text}], 'buttons': ['确定']}
        return {"code": 0, "data": show_dialog(cfg)}
    top = tk.Toplevel(MAIN_ROOT)
    top.attributes('-topmost', True)
    top.withdraw()
    funcs = {'info': messagebox.showinfo, 'warning': messagebox.showwarning, 'error': messagebox.showerror,
             'question': messagebox.askquestion, 'yesno': messagebox.askyesno,
             'okcancel': messagebox.askokcancel, 'yesnocancel': messagebox.askyesnocancel}
    if typ in funcs:
        res = funcs[typ](title, text, parent=top)
        top.destroy()
        return {"code": 0, "data": res}
    else:
        messagebox.showinfo(title, text, parent=top)
        top.destroy()
        return {"code": 0}

#  文件操作 
def list_dir(path):
    if not path or not safe_path(path) or not os.path.isdir(path):
        return {"code": -1, "msg": "无效目录"}
    try:
        items = []
        for name in os.listdir(path):
            full = os.path.join(path, name)
            st = os.stat(full)
            items.append({
                "name": name,
                "is_dir": os.path.isdir(full),
                "size": st.st_size if not os.path.isdir(full) else 0,
                "mtime": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })
        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        return {"code": 0, "data": items}
    except Exception as e:
        return {"code": -1, "msg": str(e)}

def read_file(path):
    if not path or not safe_path(path) or not os.path.isfile(path):
        return {"code": -1, "msg": "文件不存在"}
    for enc in ['utf-8', 'gbk']:
        try:
            with open(path, 'r', encoding=enc) as f:
                return {"code": 0, "data": f.read()}
        except:
            continue
    return {"code": -1, "msg": "无法解码"}

def mkdir(path):
    if not path or not safe_path(path):
        return {"code": -1, "msg": "路径无效"}
    if os.path.exists(path):
        return {"code": -1, "msg": "已存在"}
    try:
        os.makedirs(path)
        return {"code": 0}
    except Exception as e:
        return {"code": -1, "msg": str(e)}

def delete_path(path, recursive=False):
    if not path or not safe_path(path) or not os.path.exists(path):
        return {"code": -1, "msg": "路径无效"}
    try:
        if os.path.isdir(path):
            shutil.rmtree(path) if recursive else os.rmdir(path)
        else:
            os.remove(path)
        return {"code": 0}
    except Exception as e:
        return {"code": -1, "msg": str(e)}

def copy_path(src, dst):
    if not src or not dst or not safe_path(src) or not safe_path(dst):
        return {"code": -1, "msg": "路径无效"}
    try:
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
        return {"code": 0}
    except Exception as e:
        return {"code": -1, "msg": str(e)}

def move_path(src, dst):
    if not src or not dst or not safe_path(src) or not safe_path(dst):
        return {"code": -1, "msg": "路径无效"}
    try:
        shutil.move(src, dst)
        return {"code": 0}
    except Exception as e:
        return {"code": -1, "msg": str(e)}

def get_log(lines=100):
    try:
        if not os.path.exists(LOG_PATH):
            return {"code": 0, "data": "日志文件尚未生成。"}
        with open(LOG_PATH, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        return {"code": 0, "data": ''.join(all_lines[-lines:])}
    except:
        return {"code": -1, "msg": "读取日志失败"}

def lanzou_dl(url, pwd='', save_path=''):
    try:
        api = f"https://api.bugpk.com/api/lanzou?url={urllib.parse.quote(url)}"
        if pwd:
            api += f"&pwd={urllib.parse.quote(pwd)}"
        req = urllib.request.Request(api, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
        if data.get('code') != 200:
            return False, None, None, data.get('msg', '解析失败')
        real_url = data['data'].get('url')
        name = data['data'].get('name', '')
        if not real_url:
            return False, None, None, "无下载链接"
        parsed = urllib.parse.urlparse(real_url)
        qs = urllib.parse.parse_qs(parsed.query)
        filename = qs.get('fileName', [qs.get('filename', [name])[0]])[0] or 'downloaded_file'
        if not save_path:
            save_path = os.path.join(DOWNLOAD_DIR, filename)
        elif os.path.isdir(save_path):
            save_path = os.path.join(save_path, filename)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        req = urllib.request.Request(real_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=60) as r:
            with open(save_path, 'wb') as f:
                f.write(r.read())
        return True, filename, save_path, None
    except Exception as e:
        return False, None, None, str(e)

#  高级功能（依赖检查） 
ADVANCED_AVAILABLE = True
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
except ImportError:
    ADVANCED_AVAILABLE = False
    log("APScheduler未安装，定时任务功能禁用", "WARN")

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    ADVANCED_AVAILABLE = False
    log("Watchdog未安装，文件监听功能禁用", "WARN")

def check_license():
    if not is_advanced_allowed():
        return {"code": 403, "msg": "需要卡密激活", "status": "license_required"}
    return None

if ADVANCED_AVAILABLE:
    scheduler = BackgroundScheduler()
    scheduler.start()
    observer = None
    watch_handlers = {}

    def load_tasks():
        if os.path.exists(TASKS_FILE):
            try:
                with open(TASKS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def save_tasks(tasks):
        with open(TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(tasks, f, indent=2)

    def load_watches():
        if os.path.exists(WATCH_CONFIG_FILE):
            try:
                with open(WATCH_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def save_watches(watches):
        with open(WATCH_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(watches, f, indent=2)

    def execute_task(name):
        tasks = load_tasks()
        if name not in tasks or not tasks[name].get("active", True):
            return
        task = tasks[name]
        action = task.get("action")
        params = task.get("params", {})
        if action == "sync":
            src = params.get("src")
            dest = params.get("dest")
            if src and dest:
                sync_dirs(src, dest, params.get("mode", "mirror"), params.get("exclude", []))

    class WatchEventHandler(FileSystemEventHandler):
        def __init__(self, config):
            self.config = config
            self.filter_ext = config.get("filter", "*").strip()
            self.action = config.get("action")
            self.target = config.get("target")
        def on_created(self, event):
            if not event.is_directory:
                self.process(event.src_path)
        def on_modified(self, event):
            if not event.is_directory:
                self.process(event.src_path)
        def process(self, path):
            if self.filter_ext != "*" and not path.endswith(self.filter_ext):
                return
            if self.action == "move" and self.target:
                try:
                    os.makedirs(self.target, exist_ok=True)
                    shutil.move(path, os.path.join(self.target, os.path.basename(path)))
                except Exception as e:
                    log("移动失败", "ERROR", {"err": str(e)})
            elif self.action == "copy" and self.target:
                try:
                    os.makedirs(self.target, exist_ok=True)
                    shutil.copy2(path, os.path.join(self.target, os.path.basename(path)))
                except Exception as e:
                    log("复制失败", "ERROR", {"err": str(e)})

    def start_watch(path, config):
        global observer, watch_handlers
        if observer is None:
            observer = Observer()
            observer.start()
        handler = WatchEventHandler(config)
        watch_handlers[path] = handler
        observer.schedule(handler, path, recursive=False)
        log("监听已启动", "INFO", {"path": path})

    def stop_watch(path):
        global observer, watch_handlers
        if path in watch_handlers:
            observer.unschedule(watch_handlers[path])
            del watch_handlers[path]
            watches = load_watches()
            if path in watches:
                del watches[path]
                save_watches(watches)
            return True
        return False

    def save_version(path):
        if not os.path.exists(path) or os.path.isdir(path):
            return
        rel = os.path.abspath(path).replace(":", "").replace("\\", "/")
        ver_dir = os.path.join(VERSIONS_ROOT, hashlib.md5(rel.encode()).hexdigest()[:16])
        os.makedirs(ver_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        ver_file = os.path.join(ver_dir, f"{ts}_{os.path.basename(path)}")
        try:
            shutil.copy2(path, ver_file)
            log("版本已保存", "INFO", {"path": path})
        except Exception as e:
            log("保存版本失败", "ERROR", {"err": str(e)})

#  高级功能函数 
def batch_rename(path, pattern, replacement, preview=True):
    err = check_license()
    if err: return err
    if not safe_path(path) or not os.path.isdir(path):
        return {"code": -1, "msg": "无效目录"}
    try:
        results = []
        for name in os.listdir(path):
            full = os.path.join(path, name)
            if os.path.isdir(full):
                continue
            new_name = re.sub(pattern, replacement, name)
            if new_name != name:
                if preview:
                    results.append({"old": name, "new": new_name, "will_change": True})
                else:
                    os.rename(full, os.path.join(path, new_name))
                    results.append({"old": name, "new": new_name, "changed": True})
        return {"code": 0, "data": {"preview": preview, "results": results}}
    except Exception as e:
        return {"code": -1, "msg": str(e)}

def sync_dirs(src, dest, mode="mirror", exclude=None):
    err = check_license()
    if err: return err
    if not safe_path(src) or not safe_path(dest) or not os.path.isdir(src):
        return {"code": -1, "msg": "路径无效"}
    os.makedirs(dest, exist_ok=True)
    exclude = exclude or []
    try:
        for root, _, files in os.walk(src):
            rel = os.path.relpath(root, src)
            target_root = os.path.join(dest, rel)
            os.makedirs(target_root, exist_ok=True)
            for f in files:
                if any(f.endswith(ext) for ext in exclude):
                    continue
                shutil.copy2(os.path.join(root, f), os.path.join(target_root, f))
        return {"code": 0, "msg": "同步完成"}
    except Exception as e:
        return {"code": -1, "msg": str(e)}

def get_clipboard_history(limit=50):
    err = check_license()
    if err: return err
    history = list(CLIPBOARD_HISTORY)
    if limit:
        history = history[-limit:]
    return {"code": 0, "data": history}

def restore_clipboard(index):
    err = check_license()
    if err: return err
    try:
        idx = int(index)
        if 0 <= idx < len(CLIPBOARD_HISTORY):
            return {"code": 0, "data": CLIPBOARD_HISTORY[idx]}
        return {"code": -1, "msg": "索引无效"}
    except:
        return {"code": -1, "msg": "索引格式错误"}

def search_files(path, keyword, filetype=None, date_from=None):
    err = check_license()
    if err: return err
    if not safe_path(path) or not os.path.isdir(path):
        return {"code": -1, "msg": "无效目录"}
    results = []
    try:
        for root, _, files in os.walk(path):
            for f in files:
                if filetype:
                    ext = f.split('.')[-1].lower() if '.' in f else ''
                    if ext not in filetype.split(','):
                        continue
                full = os.path.join(root, f)
                if keyword.lower() in f.lower():
                    results.append({"path": full, "type": "filename"})
                    continue
                try:
                    with open(full, 'r', encoding='utf-8', errors='ignore') as fp:
                        if keyword in fp.read():
                            results.append({"path": full, "type": "content"})
                except:
                    pass
                if len(results) > 100:
                    break
        return {"code": 0, "data": results}
    except Exception as e:
        return {"code": -1, "msg": str(e)}

def find_duplicates(path, algorithm="md5", min_size=1024):
    err = check_license()
    if err: return err
    if not safe_path(path) or not os.path.isdir(path):
        return {"code": -1, "msg": "无效目录"}
    hashes = {}
    try:
        for root, _, files in os.walk(path):
            for f in files:
                full = os.path.join(root, f)
                if os.path.getsize(full) < min_size:
                    continue
                with open(full, 'rb') as fp:
                    h = hashlib.md5(fp.read()).hexdigest() if algorithm == "md5" else hashlib.sha1(fp.read()).hexdigest()
                hashes.setdefault(h, []).append(full)
        dups = [{"hash": h, "paths": paths} for h, paths in hashes.items() if len(paths) > 1]
        return {"code": 0, "data": dups}
    except Exception as e:
        return {"code": -1, "msg": str(e)}

def extract_archive(archive, target):
    err = check_license()
    if err: return err
    if not safe_path(archive) or not safe_path(target):
        return {"code": -1, "msg": "路径无效"}
    try:
        with zipfile.ZipFile(archive, 'r') as z:
            z.extractall(target)
        return {"code": 0, "msg": "解压完成"}
    except Exception as e:
        return {"code": -1, "msg": str(e)}

def create_archive(sources, target, format="zip", password=None):
    err = check_license()
    if err: return err
    try:
        with zipfile.ZipFile(target, 'w') as z:
            for src in sources:
                if os.path.isdir(src):
                    for root, _, files in os.walk(src):
                        for f in files:
                            full = os.path.join(root, f)
                            z.write(full, os.path.relpath(full, os.path.dirname(src)))
                else:
                    z.write(src, os.path.basename(src))
        return {"code": 0, "msg": "压缩完成"}
    except Exception as e:
        return {"code": -1, "msg": str(e)}

def share_path(path, expires_in=3600, readonly=True):
    err = check_license()
    if err: return err
    return {"code": 0, "data": {"url": f"http://127.0.0.1:{HTTP_PORT}/share/placeholder"}}

def generate_remote_token(expires_in=300, permissions=None):
    err = check_license()
    if err: return err
    token = secrets.token_hex(8)
    return {"code": 0, "data": {"token": token, "url": f"https://bjs.example.com/remote/{token}"}}

def sync_device(device_id, sync_path, auto_sync=False):
    err = check_license()
    if err: return err
    return {"code": 0, "msg": "设备同步已配置（占位）"}

def install_plugin(source, name):
    err = check_license()
    if err: return err
    return {"code": 0, "msg": "插件安装占位"}

def exec_plugin(plugin, action):
    err = check_license()
    if err: return err
    return {"code": 0, "msg": "插件执行占位"}

def exec_script(script, timeout=10):
    err = check_license()
    if err: return err
    try:
        exec_globals = {}
        exec(script, exec_globals)
        return {"code": 0, "msg": "脚本执行完成"}
    except Exception as e:
        return {"code": -1, "msg": str(e)}

if ADVANCED_AVAILABLE:
    def schedule_task(name, trigger, expression, action, params):
        err = check_license()
        if err: return err
        tasks = load_tasks()
        if name in tasks:
            return {"code": -1, "msg": f"任务 '{name}' 已存在"}
        tasks[name] = {"trigger": trigger, "expression": expression, "action": action, "params": params, "active": True}
        save_tasks(tasks)
        try:
            if trigger == "cron":
                scheduler.add_job(lambda: execute_task(name), CronTrigger.from_crontab(expression), id=f"task_{name}", replace_existing=True)
            else:
                scheduler.add_job(lambda: execute_task(name), 'interval', seconds=int(expression), id=f"task_{name}", replace_existing=True)
            return {"code": 0, "msg": f"任务 '{name}' 已添加"}
        except Exception as e:
            return {"code": -1, "msg": str(e)}

    def watch_folder(path, events, filter, action, target):
        err = check_license()
        if err: return err
        if not safe_path(path) or not os.path.isdir(path):
            return {"code": -1, "msg": "无效目录"}
        watches = load_watches()
        if path in watches:
            return {"code": -1, "msg": "该目录已被监听"}
        config = {"path": path, "events": events, "filter": filter, "action": action, "target": target, "active": True}
        watches[path] = config
        save_watches(watches)
        start_watch(path, config)
        return {"code": 0, "msg": f"已开始监听 {path}"}

    def get_file_versions(path):
        err = check_license()
        if err: return err
        if not os.path.exists(path):
            return {"code": -1, "msg": "文件不存在"}
        ver_dir = os.path.join(VERSIONS_ROOT, hashlib.md5(os.path.abspath(path).replace(":", "").replace("\\", "/").encode()).hexdigest()[:16])
        if not os.path.isdir(ver_dir):
            return {"code": 0, "data": []}
        versions = []
        for f in os.listdir(ver_dir):
            full = os.path.join(ver_dir, f)
            if os.path.isfile(full):
                parts = f.split("_", 1)
                versions.append({
                    "version": parts[0] if len(parts) > 1 else "",
                    "file": f,
                    "full_path": full,
                    "size": os.path.getsize(full),
                    "mtime": datetime.fromtimestamp(os.path.getmtime(full)).strftime("%Y-%m-%d %H:%M:%S")
                })
        versions.sort(key=lambda x: x["version"], reverse=True)
        return {"code": 0, "data": versions}

    def restore_version(path, version):
        err = check_license()
        if err: return err
        if not os.path.exists(path):
            return {"code": -1, "msg": "文件不存在"}
        ver_dir = os.path.join(VERSIONS_ROOT, hashlib.md5(os.path.abspath(path).replace(":", "").replace("\\", "/").encode()).hexdigest()[:16])
        if not os.path.isdir(ver_dir):
            return {"code": -1, "msg": "没有版本记录"}
        for f in os.listdir(ver_dir):
            if f.startswith(version + "_"):
                try:
                    shutil.copy2(os.path.join(ver_dir, f), path)
                    return {"code": 0, "msg": f"已恢复到版本 {version}"}
                except Exception as e:
                    return {"code": -1, "msg": str(e)}
        return {"code": -1, "msg": f"未找到版本 {version}"}

#  Flask 应用 
app = Flask(__name__)
CORS(app)

@app.before_request
def log_request():
    log(f"请求 {request.method} {request.path}", "INFO", {"remote_addr": request.remote_addr, "args": request.args.to_dict(), "json": request.get_json(silent=True)})

@app.after_request
def log_response(response):
    log(f"响应 {request.method} {request.path} -> {response.status}", "INFO", {"status": response.status})
    return response

@app.route('/health')
def health():
    return jsonify({"code": 0, "status": "running", "port": HTTP_PORT})

@app.route('/api/open')
def api_open():
    return jsonify(open_path(request.args.get('path', '')))

@app.route('/api/msg', methods=['POST'])
def api_msg():
    data = request.json or {}
    return jsonify(show_msg(data.get('text', ''), data.get('type', 'info'), data.get('title', '来自网页'),
                            data.get('image'), data.get('width', 0), data.get('height', 0)))

@app.route('/api/run', methods=['POST'])
def api_run():
    data = request.json or {}
    return jsonify(run_prog(data.get('path', ''), data.get('args'), data.get('wait', False)))

@app.route('/api/dialog', methods=['POST'])
def api_dialog():
    data = request.json or {}
    res = show_dialog(data.get('config', ''))
    return jsonify({"code": 0, "data": res} if res else {"code": -1, "msg": "对话框错误"})

@app.route('/api/listdir')
def api_listdir():
    return jsonify(list_dir(request.args.get('path', os.path.expanduser("~"))))

@app.route('/api/readfile')
def api_readfile():
    return jsonify(read_file(request.args.get('path', '')))

@app.route('/api/mkdir', methods=['POST'])
def api_mkdir():
    return jsonify(mkdir(request.json.get('path', '')))

@app.route('/api/delete', methods=['POST'])
def api_delete():
    data = request.json or {}
    return jsonify(delete_path(data.get('path', ''), data.get('recursive', False)))

@app.route('/api/copy', methods=['POST'])
def api_copy():
    data = request.json or {}
    return jsonify(copy_path(data.get('src', ''), data.get('dest', '')))

@app.route('/api/move', methods=['POST'])
def api_move():
    data = request.json or {}
    return jsonify(move_path(data.get('src', ''), data.get('dest', '')))

@app.route('/api/log')
def api_log():
    return jsonify(get_log(request.args.get('lines', 100, type=int)))

@app.route('/api/lanzou/download', methods=['POST'])
def api_lanzou():
    data = request.json or {}
    ok, name, path, err = lanzou_dl(data.get('url', ''), data.get('pwd', ''), data.get('save_path', ''))
    if ok:
        return jsonify({"code": 0, "data": {"filename": name, "save_path": path}})
    else:
        return jsonify({"code": -1, "msg": err})

@app.route('/api/sysinfo')
def sysinfo():
    try:
        import psutil
        return jsonify({"code": 0, "data": {
            "system": platform.system(), "release": platform.release(),
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "disk_usage": psutil.disk_usage('/')._asdict()
        }})
    except:
        return jsonify({"code": 0, "data": {"system": platform.system(), "release": platform.release()}})

@app.route('/api/license/status')
def api_license_status():
    return jsonify({"code": 0, "data": LICENSE_STATUS})

@app.route('/api/license/verify', methods=['POST'])
def api_license_verify():
    key = (request.json or {}).get('key', '')
    ok, info = verify_license(key)
    if ok:
        LICENSE_STATUS.update({"valid": True, "key": key, "expire_time": info.get("expire_time"), "msg": info.get("msg")})
        return jsonify({"code": 0, "data": LICENSE_STATUS})
    else:
        return jsonify({"code": -1, "msg": info.get("msg", "验证失败")})

def advanced_unavailable():
    return jsonify({"code": -1, "msg": "高级功能依赖未安装（apscheduler/watchdog）"})

@app.route('/api/advanced/batch-rename', methods=['POST'])
def api_batch_rename():
    data = request.json or {}
    return jsonify(batch_rename(data.get('path', ''), data.get('pattern', ''), data.get('replacement', ''), data.get('preview', True)))

@app.route('/api/advanced/sync', methods=['POST'])
def api_sync():
    data = request.json or {}
    return jsonify(sync_dirs(data.get('src', ''), data.get('dest', ''), data.get('mode', 'mirror'), data.get('exclude', [])))

@app.route('/api/advanced/schedule', methods=['POST'])
def api_schedule():
    if not ADVANCED_AVAILABLE:
        return advanced_unavailable()
    data = request.json or {}
    return jsonify(schedule_task(data.get('name', ''), data.get('trigger', 'cron'), data.get('expression', ''),
                                 data.get('action', ''), data.get('params', {})))

@app.route('/api/advanced/clipboard/history')
def api_clipboard_history():
    return jsonify(get_clipboard_history(request.args.get('limit', 50, type=int)))

@app.route('/api/advanced/clipboard/restore', methods=['POST'])
def api_clipboard_restore():
    return jsonify(restore_clipboard((request.json or {}).get('index')))

@app.route('/api/advanced/watch', methods=['POST'])
def api_watch():
    if not ADVANCED_AVAILABLE:
        return advanced_unavailable()
    data = request.json or {}
    return jsonify(watch_folder(data.get('path', ''), data.get('events', ['create']), data.get('filter', '*'),
                                data.get('action', ''), data.get('target', '')))

@app.route('/api/advanced/search', methods=['POST'])
def api_search():
    data = request.json or {}
    return jsonify(search_files(data.get('path', ''), data.get('keyword', ''), data.get('filetype', ''), data.get('date_from', '')))

@app.route('/api/advanced/versions')
def api_versions():
    if not ADVANCED_AVAILABLE:
        return advanced_unavailable()
    return jsonify(get_file_versions(request.args.get('path', '')))

@app.route('/api/advanced/versions/restore', methods=['POST'])
def api_restore_version():
    if not ADVANCED_AVAILABLE:
        return advanced_unavailable()
    data = request.json or {}
    return jsonify(restore_version(data.get('path', ''), data.get('version', '')))

@app.route('/api/advanced/duplicates', methods=['POST'])
def api_duplicates():
    data = request.json or {}
    return jsonify(find_duplicates(data.get('path', ''), data.get('algorithm', 'md5'), data.get('min_size', 1024)))

@app.route('/api/advanced/archive/extract', methods=['POST'])
def api_extract():
    data = request.json or {}
    return jsonify(extract_archive(data.get('archive', ''), data.get('target', '')))

@app.route('/api/advanced/archive/create', methods=['POST'])
def api_create_archive():
    data = request.json or {}
    return jsonify(create_archive(data.get('sources', []), data.get('target', ''), data.get('format', 'zip'), data.get('password')))

@app.route('/api/advanced/share', methods=['POST'])
def api_share():
    data = request.json or {}
    return jsonify(share_path(data.get('path', ''), data.get('expires_in', 3600), data.get('readonly', True)))

@app.route('/api/advanced/remote/token', methods=['POST'])
def api_remote_token():
    data = request.json or {}
    return jsonify(generate_remote_token(data.get('expires_in', 300), data.get('permissions', [])))

@app.route('/api/advanced/sync/device', methods=['POST'])
def api_sync_device():
    data = request.json or {}
    return jsonify(sync_device(data.get('device_id', ''), data.get('sync_path', ''), data.get('auto_sync', False)))

@app.route('/api/advanced/plugin/install', methods=['POST'])
def api_install_plugin():
    data = request.json or {}
    return jsonify(install_plugin(data.get('source', ''), data.get('name', '')))

@app.route('/api/advanced/plugin/exec', methods=['POST'])
def api_exec_plugin():
    data = request.json or {}
    return jsonify(exec_plugin(data.get('plugin', ''), data.get('action', '')))

@app.route('/api/advanced/script/exec', methods=['POST'])
def api_exec_script():
    data = request.json or {}
    return jsonify(exec_script(data.get('script', ''), data.get('timeout', 10)))

@app.route('/api/advanced/watch/stop', methods=['POST'])
def api_stop_watch():
    if not ADVANCED_AVAILABLE:
        return advanced_unavailable()
    path = (request.json or {}).get('path', '')
    if stop_watch(path):
        return jsonify({"code": 0, "msg": "已停止监听"})
    return jsonify({"code": -1, "msg": "该路径未在监听"})

#  托盘 
def get_icon():
    if os.path.exists(ICON_PATH):
        try:
            return Image.open(ICON_PATH)
        except:
            pass
    img = Image.new('RGB', (64,64), (52,152,219))
    ImageDraw.Draw(img).rectangle((10,10,54,54), fill=(41,128,185))
    return img

def show_license_window():
    win = LicenseWindow(MAIN_ROOT)
    result = win.run()
    if result and result.get("key"):
        global tray_icon
        if 'tray_icon' in globals():
            tray_icon.stop()
            tray_icon = None
        create_tray_icon()
        messagebox.showinfo("升级成功", "高级功能已解锁！", parent=MAIN_ROOT)
        log("用户通过托盘升级高级版", "INFO", {"key": result["key"]})
    else:
        log("用户取消升级", "INFO")

def on_tray_click(icon, item):
    if LICENSE_STATUS.get("valid"):
        messagebox.showinfo("提示", "您已是高级版用户", parent=MAIN_ROOT)
    else:
        show_license_window()

def create_tray_icon():
    global tray_icon
    if LICENSE_STATUS.get("valid"):
        menu_text = "💎 高级版"
    else:
        menu_text = "📦 标准版 「点击升级」"
    menu = pystray.Menu(
        pystray.MenuItem(f"📌 BJS {VERSION}", None, enabled=False),
        pystray.MenuItem(menu_text, on_tray_click),
        pystray.MenuItem("🔄 检查更新", lambda icon, item: threading.Thread(target=get_updates, daemon=True).start()),
        pystray.MenuItem("📄 查看日志", on_view_log),
        pystray.MenuItem("ℹ️ 关于", on_about),
        pystray.MenuItem("🚪 退出", on_exit)
    )
    tray_icon = pystray.Icon("bjs_relay", get_icon(), "BJS 数据接力", menu)
    tray_icon.run()

def on_view_log(icon, item):
    if os.path.exists(LOG_PATH):
        os.startfile(LOG_PATH)

def on_about(icon, item):
    win = tk.Toplevel(MAIN_ROOT)
    win.title("关于")
    win.geometry("420x420")
    win.attributes('-topmost', True)
    win.update_idletasks()
    win.geometry(f"+{win.winfo_screenwidth()//2-210}+{win.winfo_screenheight()//2-210}")
    main = ttk.Frame(win, padding=30)
    main.pack(fill=tk.BOTH, expand=True)
    ttk.Label(main, text="BJS 数据接力", font=("微软雅黑", 20, "bold"), foreground="#2b6f9e").pack(pady=(0,5))
    ttk.Label(main, text=f"版本 {VERSION}", font=("微软雅黑", 12)).pack(pady=(0,5))
    status = "✓ 高级版" if LICENSE_STATUS.get("valid") else "标准版 (免费)"
    ttk.Label(main, text=status, font=("微软雅黑", 10), foreground="#00aa00" if LICENSE_STATUS.get("valid") else "#888").pack(pady=(0,15))
    ttk.Separator(main).pack(fill=tk.X, pady=10)
    ttk.Label(main, text="开发者：HXZXS").pack(pady=5)
    ttk.Separator(main).pack(fill=tk.X, pady=10)
    def open_url(url):
        webbrowser.open(url)
    ttk.Button(main, text="🌐 控制台", command=lambda: open_url("https://lcwd.rth1.xyz/WEB.html")).pack(pady=4, fill=tk.X)
    ttk.Button(main, text="📖 文档", command=lambda: open_url("https://lcwd.rth1.xyz/WEBHELP.html")).pack(pady=4, fill=tk.X)
    ttk.Button(main, text="关闭", command=win.destroy).pack(pady=15)

def on_exit(icon, item):
    # 终止卡密服务
    kill_key_exe()
    icon.stop()
    os._exit(0)

def start_http():
    try:
        app.run(host='127.0.0.1', port=HTTP_PORT, debug=False, use_reloader=False)
    except Exception as e:
        log("HTTP启动失败", "ERROR", {"err": str(e)})

#  启动加载持久化任务 
def load_scheduled_tasks():
    if not ADVANCED_AVAILABLE:
        return
    tasks = load_tasks()
    for name, cfg in tasks.items():
        if cfg.get("active", True):
            trigger, expr = cfg.get("trigger"), cfg.get("expression")
            if trigger and expr:
                try:
                    if trigger == "cron":
                        scheduler.add_job(lambda n=name: execute_task(n), CronTrigger.from_crontab(expr), id=f"task_{name}", replace_existing=True)
                    else:
                        scheduler.add_job(lambda n=name: execute_task(n), 'interval', seconds=int(expr), id=f"task_{name}", replace_existing=True)
                except Exception as e:
                    log("加载任务失败", "ERROR", {"name": name, "err": str(e)})

def load_watch_handlers():
    if not ADVANCED_AVAILABLE:
        return
    watches = load_watches()
    for path, cfg in watches.items():
        if cfg.get("active", True) and os.path.isdir(path):
            start_watch(path, cfg)

#  入口 
if __name__ == "__main__":
    # 召回
    handle_recall()

    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    MAIN_ROOT = root

    # 卡密验证（联网）
    auth_on_start()

    # 首次运行开机自启
    setup_autostart()

    # 检查更新（非阻塞）
    threading.Thread(target=get_updates, daemon=True).start()

    # 启动卡密服务
    run_key_exe()

    # 加载持久化任务
    load_scheduled_tasks()
    load_watch_handlers()

    # 启动服务
    threading.Thread(target=start_http, daemon=True).start()
    threading.Thread(target=create_tray_icon, daemon=True).start()
    log("BJS 数据接力启动", "INFO", {"version": VERSION})
    root.mainloop()

    # 清理
    if ADVANCED_AVAILABLE:
        scheduler.shutdown()
        if observer:
            observer.stop()
            observer.join()
