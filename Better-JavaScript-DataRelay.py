# BJS 数据接力 6.0.4.γ
# HXZXS

import sys, os, json, time, shutil, subprocess, urllib.parse, urllib.request
import threading, tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime
import traceback, pystray, ctypes
from PIL import Image, ImageDraw, ImageTk
from flask import Flask, request, jsonify, send_from_directory, abort, render_template_string
from flask_cors import CORS
import webbrowser, re, hashlib, zipfile, platform, uuid as uuid_lib, secrets
from collections import deque
import logging
from logging.handlers import RotatingFileHandler
import tempfile
import importlib.util
import socket
import io

# ---------- 目录和日志 ----------
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
if os.name == 'nt':
    USER_DATA = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'BJS')
else:
    USER_DATA = os.path.join(os.path.expanduser('~'), '.config', 'bjs')
os.makedirs(USER_DATA, exist_ok=True)
LOG_PATH = os.path.join(USER_DATA, "bjs.log")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('BJS')
logger.setLevel(logging.INFO)
fmt = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
console = logging.StreamHandler(); console.setFormatter(fmt); logger.addHandler(console)
try:
    fh = RotatingFileHandler(LOG_PATH, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
    fh.setFormatter(fmt); logger.addHandler(fh)
except Exception:
    pass

def log(msg, level="INFO", extra=None):
    if extra:
        msg += f" | {json.dumps(extra, ensure_ascii=False)}"
    getattr(logger, level.lower() if level.lower() in ('error','warning','info') else 'info')(msg)

DOWNLOAD_DIR = os.path.join(USER_DATA, "downloads")
ICON_PATH = os.path.join(BASE_DIR, "logo.ico")
if not os.path.exists(ICON_PATH):
    ICON_PATH = os.path.join(BASE_DIR, "logo.png")
DATA_DIR = os.path.join(USER_DATA, "data")
TASKS_FILE = os.path.join(DATA_DIR, "tasks.json")
VERSIONS_ROOT = os.path.join(DATA_DIR, "versions")
WATCH_CONFIG_FILE = os.path.join(DATA_DIR, "watches.json")
CACHE_FILE = os.path.join(DATA_DIR, "license_cache.json")
PLUGIN_DIR = os.path.join(DATA_DIR, "plugins")
SHARE_SESSIONS_FILE = os.path.join(DATA_DIR, "share_sessions.json")
DEVICES_FILE = os.path.join(DATA_DIR, "devices.json")

for d in [DOWNLOAD_DIR, DATA_DIR, VERSIONS_ROOT, PLUGIN_DIR]:
    os.makedirs(d, exist_ok=True)

HTTP_PORT = 8765
MAIN_ROOT = None
LICENSE_STATUS = {"valid": False, "key": None, "expire_time": None, "msg": None}
CLIPBOARD_HISTORY = deque(maxlen=100)
VERSION = "6.0.4.γ"

OFFLINE_BLOCK = True
NOTICE_URL = "https://bjs.rth1.xyz/notice.json"
UPDATE_URL = "https://bjs.rth1.xyz/up.json"
GITHUB_RELEASES = "https://github.com/HXZXS/Better-JavaScript/releases"
RECALL_URL = "https://bjs.rth1.xyz/Recall.json"
LICENSE_SERVER = "https://lckey.rth1.xyz/"
KEY_EXE = "BJS developer key.exe"
UNINS_EXE = "unins000.exe"

# 全局 UA —— 所有联网行为统一使用
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"

pending_notice = None
tray_icon = None


# ---------- 联网工具 ----------
def http_open(url, timeout=15, headers=None, method='GET', data=None):
    """统一的联网入口：强制带 UA"""
    h = {'User-Agent': UA, 'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'}
    if headers:
        h.update(headers)
    body = None
    if data is not None:
        if isinstance(data, (dict, list)):
            body = json.dumps(data).encode('utf-8')
            h.setdefault('Content-Type', 'application/json')
        elif isinstance(data, str):
            body = data.encode('utf-8')
        else:
            body = data
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    return urllib.request.urlopen(req, timeout=timeout)


def http_get_json(url, timeout=15, headers=None):
    """GET + 解析 JSON，带 UA"""
    with http_open(url, timeout=timeout, headers=headers) as r:
        return json.loads(r.read().decode('utf-8'))


def http_download(url, save_path, progress_cb=None, timeout=60):
    """带 UA 的流式下载。progress_cb(downloaded, total)"""
    with http_open(url, timeout=timeout) as resp:
        try:
            total = int(resp.headers.get('Content-Length', 0))
        except Exception:
            total = 0
        downloaded = 0
        chunk = 64 * 1024
        with open(save_path, 'wb') as f:
            while True:
                data = resp.read(chunk)
                if not data:
                    break
                f.write(data)
                downloaded += len(data)
                if progress_cb:
                    try: progress_cb(downloaded, total)
                    except Exception: pass
        return downloaded


# ---------- 权限 ----------
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def run_as_admin():
    try:
        if getattr(sys, 'frozen', False):
            exe = sys.executable
            params = ''
        else:
            exe = sys.executable
            params = ' '.join(f'"{a}"' for a in sys.argv)
        ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
        return True
    except Exception as e:
        log(f"提权失败: {e}", "ERROR")
        return False


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


# ---------- 共享会话 ----------
share_sessions = {}
share_sessions_lock = threading.Lock()

def load_share_sessions():
    global share_sessions
    if os.path.exists(SHARE_SESSIONS_FILE):
        try:
            with open(SHARE_SESSIONS_FILE, 'r', encoding='utf-8') as f:
                share_sessions = json.load(f)
        except Exception:
            pass

def save_share_sessions():
    try:
        with open(SHARE_SESSIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(share_sessions, f, indent=2)
    except Exception:
        pass

def clean_expired_sessions():
    now = time.time()
    with share_sessions_lock:
        dead = [t for t, s in share_sessions.items() if s.get('expires', 0) < now]
        for t in dead:
            del share_sessions[t]
        if dead:
            save_share_sessions()


# ---------- 设备 ----------
devices = {}
def load_devices():
    global devices
    if os.path.exists(DEVICES_FILE):
        try:
            with open(DEVICES_FILE, 'r', encoding='utf-8') as f:
                devices = json.load(f)
        except Exception:
            pass

def save_devices():
    try:
        with open(DEVICES_FILE, 'w', encoding='utf-8') as f:
            json.dump(devices, f, indent=2)
    except Exception:
        pass


# ---------- 开机自启 ----------
def setup_autostart():
    if getattr(sys, 'frozen', False):
        exe_cmd = f'"{sys.executable}"'
    else:
        pythonw = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
        if os.path.exists(pythonw):
            exe_cmd = f'"{pythonw}" "{os.path.abspath(sys.argv[0])}"'
        else:
            exe_cmd = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'

    if os.name == 'nt':
        import winreg
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_READ | winreg.KEY_SET_VALUE)
            try:
                cur, _ = winreg.QueryValueEx(key, "BJSDataRelay")
                if cur != exe_cmd:
                    winreg.SetValueEx(key, "BJSDataRelay", 0, winreg.REG_SZ, exe_cmd)
                    log("开机自启已更新", "INFO", {"cmd": exe_cmd})
            except FileNotFoundError:
                winreg.SetValueEx(key, "BJSDataRelay", 0, winreg.REG_SZ, exe_cmd)
                log("开机自启已设置", "INFO", {"cmd": exe_cmd})
            winreg.CloseKey(key)
        except Exception as e:
            log("设置开机自启失败", "ERROR", {"err": str(e)})
    else:
        auto_dir = os.path.expanduser("~/.config/autostart")
        os.makedirs(auto_dir, exist_ok=True)
        desktop = os.path.join(auto_dir, "bjs.desktop")
        content = f"""[Desktop Entry]
Type=Application
Name=BJS 数据接力
Exec={exe_cmd}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
"""
        try:
            with open(desktop, 'w') as f:
                f.write(content)
        except Exception as e:
            log("设置开机自启失败", "ERROR", {"err": str(e)})


def ensure_firewall_rule():
    if os.name != 'nt' or not is_admin():
        return
    rule = f"BJS DataRelay {HTTP_PORT}"
    try:
        kw = {'creationflags': subprocess.CREATE_NO_WINDOW}
        q = subprocess.run(['netsh', 'advfirewall', 'firewall', 'show', 'rule', f'name={rule}'],
                           capture_output=True, text=True, timeout=8, **kw)
        if q.returncode == 0 and 'No rules match' not in q.stdout:
            return
        a = subprocess.run(['netsh', 'advfirewall', 'firewall', 'add', 'rule',
                            f'name={rule}', 'dir=in', 'action=allow',
                            'protocol=TCP', f'localport={HTTP_PORT}'],
                           capture_output=True, text=True, timeout=8, **kw)
        if a.returncode == 0:
            log("防火墙规则已添加", "INFO", {"port": HTTP_PORT})
    except Exception as e:
        log("防火墙规则设置失败", "WARN", {"err": str(e)})


# ---------- 召回 ----------
def recall_check():
    try:
        data = http_get_json(RECALL_URL, timeout=10)
        return data.get('code', -1), data.get('recall', ''), data.get('msg', '')
    except Exception as e:
        log("召回检查失败", "WARN", {"err": str(e)})
        return -1, '', str(e)

def handle_recall():
    code, recall, msg = recall_check()
    if code != 1:
        return
    try:
        if os.name == 'nt':
            ctypes.windll.user32.MessageBoxW(0, f"{msg}\n\n程序即将执行召回操作。",
                                              "召回通告", 0x30 | 0x40000)
        else:
            tmp = tk.Tk(); tmp.withdraw()
            messagebox.showwarning("召回通告", f"{msg}\n\n程序即将执行召回操作。", parent=tmp)
            tmp.destroy()
    except Exception:
        pass

    if recall == "main":
        unins = os.path.join(BASE_DIR, UNINS_EXE)
        if os.path.exists(unins):
            try:
                if os.name == 'nt':
                    subprocess.Popen([unins], shell=True)
                else:
                    subprocess.Popen([unins])
            except Exception as e:
                log("执行卸载失败", "ERROR", {"err": str(e)})
        sys.exit(0)
    elif recall == "key":
        kp = os.path.join(BASE_DIR, KEY_EXE)
        if os.path.exists(kp):
            try:
                os.remove(kp)
            except Exception as e:
                log("删除卡密服务失败", "ERROR", {"err": str(e)})


# ---------- 公告 ----------
def fetch_notice():
    try:
        data = http_get_json(NOTICE_URL, timeout=5)
        code = data.get('code', -1)
        if code == 0:
            return True, None
        if code == 1:
            level = data.get('level', 'C')
            msg = data.get('msg', '')
            if msg:
                return True, {'level': level, 'msg': msg.replace('|', '\n')}
            return True, None
        return True, None
    except Exception as e:
        log("获取公告失败", "ERROR", {"err": str(e)})
        return False, None


def show_force_notice(level, msg, seconds, blink=False):
    try:
        win = tk.Toplevel(MAIN_ROOT)
        win.title("⚠ 公告")
        win.geometry("500x300")
        win.attributes('-topmost', True)
        if level == 'O':
            bg, fg, blink_color = '#B05923', 'white', '#900021'
        elif level == 'A':
            bg, fg = '#ff6600', 'white'
        else:
            bg, fg = '#3399ff', 'white'
        win.configure(bg=bg)

        label = tk.Label(win, text=msg, font=("微软雅黑", 14), wraplength=450, bg=bg, fg=fg)
        label.pack(pady=20, padx=20, fill=tk.BOTH, expand=True)

        btn_var = tk.StringVar(value=f"确定 ({seconds}s)")
        btn = ttk.Button(win, textvariable=btn_var, state='disabled', command=win.destroy)
        btn.pack(pady=10)

        if blink:
            def do_blink():
                try:
                    cur = win.cget('bg')
                    new = blink_color if cur == bg else bg
                    win.configure(bg=new); label.configure(bg=new)
                    if btn['state'] == 'disabled':
                        win.after(500, do_blink)
                except Exception:
                    pass
            win.after(500, do_blink)

        def countdown(c):
            if c > 0:
                btn_var.set(f"确定 ({c}s)")
                win.after(1000, countdown, c-1)
            else:
                btn_var.set("确定"); btn.config(state='normal')
        countdown(seconds)

        win.update_idletasks()
        w, h = win.winfo_width(), win.winfo_height()
        x = (win.winfo_screenwidth() - w)//2
        y = (win.winfo_screenheight() - h)//2
        win.geometry(f"+{x}+{y}")
        win.grab_set()
        win.wait_window()
    except Exception as e:
        log("强制公告窗口异常", "ERROR", {"err": str(e)})


def show_notice_detail(msg, level='D'):
    if not msg:
        return
    try:
        win = tk.Toplevel(MAIN_ROOT)
        win.title("📢 BJS 公告")
        win.geometry("520x400")
        win.attributes('-topmost', True)
        win.update_idletasks()
        w, h = win.winfo_width(), win.winfo_height()
        x = (win.winfo_screenwidth() - w) // 2
        y = (win.winfo_screenheight() - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")

        colors = {'O': '#B05923', 'A': '#ff6600', 'B': '#3399ff', 'C': '#2b6f9e', 'D': '#2b6f9e'}
        bar_color = colors.get(level, '#2b6f9e')

        head = tk.Frame(win, bg=bar_color, height=52)
        head.pack(fill=tk.X); head.pack_propagate(False)
        tk.Label(head, text=f"📢  公告  ·  {level} 级",
                 bg=bar_color, fg='white',
                 font=("微软雅黑", 14, "bold")).pack(side=tk.LEFT, padx=18)

        body = tk.Frame(win, bg='#fafcff')
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=14)

        txt = tk.Text(body, wrap=tk.WORD, font=("微软雅黑", 11),
                      bg='#fafcff', fg='#1a2a3e', relief=tk.FLAT,
                      padx=6, pady=6, cursor='arrow')
        sb = ttk.Scrollbar(body, orient=tk.VERTICAL, command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        txt.insert('1.0', msg)
        txt.config(state=tk.DISABLED)

        bf = ttk.Frame(win); bf.pack(fill=tk.X, pady=(0, 14))

        def copy_text():
            try:
                win.clipboard_clear(); win.clipboard_append(msg)
                messagebox.showinfo("提示", "已复制到剪贴板", parent=win)
            except Exception:
                pass

        ttk.Button(bf, text="📋 复制", command=copy_text, width=10).pack(side=tk.LEFT, padx=(20, 6))
        ttk.Button(bf, text="关闭", command=win.destroy, width=12).pack(side=tk.RIGHT, padx=(6, 20))

        win.grab_set(); win.focus_force()
    except Exception as e:
        log("公告详情窗口异常", "ERROR", {"err": str(e)})
        messagebox.showinfo("公告", msg, parent=MAIN_ROOT)


def show_pending_notice():
    if pending_notice:
        show_notice_detail(pending_notice, level='D')
    else:
        messagebox.showinfo("提示", "暂无公告", parent=MAIN_ROOT)


# ---------- 更新 ----------
def get_updates():
    try:
        data = http_get_json(UPDATE_URL, timeout=10)
        ver = data.get('version', '')
        if ver and ver != VERSION:
            url = data.get('url', ''); msg = data.get('msg', '')
            if MAIN_ROOT:
                MAIN_ROOT.after(0, lambda: show_update_win(ver, url, msg))
    except Exception as e:
        log("检查更新失败", "WARN", {"err": str(e)})


def show_update_win(version, url, msg):
    try:
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

        main = ttk.Frame(win, padding=20); main.pack(fill=tk.BOTH, expand=True)
        ttk.Label(main, text="📦 发现新版本", font=("微软雅黑", 16, "bold"), foreground="#2b6f9e").pack(pady=(0,5))
        ttk.Label(main, text=f"最新版本: {version}", font=("微软雅黑", 11)).pack(pady=(0,10))

        lf = ttk.LabelFrame(main, text="更新日志", padding=8)
        lf.pack(fill=tk.BOTH, expand=True, pady=5)
        lt = tk.Text(lf, height=6, wrap=tk.WORD, font=("微软雅黑", 10))
        lt.pack(fill=tk.BOTH, expand=True)
        lt.insert('1.0', '\n'.join(msg.split('|')) if msg else "暂无更新日志")
        lt.config(state=tk.DISABLED)

        pv = tk.DoubleVar()
        prog = ttk.Progressbar(main, variable=pv, maximum=100, length=350)
        prog.pack(pady=8); prog.pack_forget()

        sl = ttk.Label(main, text="", font=("微软雅黑", 9)); sl.pack(pady=(0,5))
        bf = ttk.Frame(main); bf.pack(pady=10)

        def open_gh():
            webbrowser.open(GITHUB_RELEASES)

        def do_dl():
            if not url:
                messagebox.showerror("错误", "下载地址无效", parent=win); return
            github_btn.config(state=tk.DISABLED); update_btn.config(state=tk.DISABLED)
            prog.pack(pady=8); sl.config(text="正在下载...")

            def worker():
                try:
                    tmp_dir = tempfile.gettempdir()
                    fn = os.path.basename(url) or "bjs_setup.exe"
                    sp = os.path.join(tmp_dir, fn)

                    def _cb(downloaded, total):
                        if total > 0:
                            pv.set(min(100, int(downloaded * 100 / total)))
                            win.update_idletasks()

                    # 带 UA 的流式下载
                    http_download(url, sp, progress_cb=_cb, timeout=60)

                    sl.config(text="下载完成，正在启动安装...")
                    if os.name == 'nt':
                        subprocess.Popen([sp], shell=True)
                    else:
                        subprocess.Popen([sp])
                    win.after(500, lambda: sys.exit(0))
                except Exception as e:
                    win.after(0, lambda: messagebox.showerror("下载失败", str(e), parent=win))
                    win.after(0, lambda: github_btn.config(state=tk.NORMAL))
                    win.after(0, lambda: update_btn.config(state=tk.NORMAL))
                    win.after(0, lambda: prog.pack_forget())
            threading.Thread(target=worker, daemon=True).start()

        github_btn = ttk.Button(bf, text="GitHub Releases", command=open_gh)
        github_btn.pack(side=tk.LEFT, padx=5)
        update_btn = ttk.Button(bf, text="立即更新", command=do_dl)
        update_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(bf, text="稍后", command=win.destroy).pack(side=tk.LEFT, padx=5)
    except Exception as e:
        log("更新窗口异常", "ERROR", {"err": str(e)})


# ---------- 卡密 ----------
def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_cache(data):
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _apply_license(key, expire, msg):
    """统一更新全局授权状态"""
    LICENSE_STATUS.update({
        "valid": True,
        "key": key,
        "expire_time": expire,
        "msg": msg or "验证通过"
    })


def _clear_license():
    """清除授权状态并删除本地缓存"""
    LICENSE_STATUS.update({"valid": False, "key": None,
                           "expire_time": None, "msg": None})
    if os.path.exists(CACHE_FILE):
        try: os.remove(CACHE_FILE)
        except Exception: pass


def online_check(key, device_id):
    """联网校验卡密。返回 (ok, expire, msg, is_network_error)"""
    url = f"{LICENSE_SERVER}?key={urllib.parse.quote(key)}&uuid={urllib.parse.quote(device_id)}"
    try:
        data = http_get_json(url, timeout=15,
                             headers={'Accept': 'application/json'})
        if data.get("code") == 200:
            return True, data.get("data", {}).get("expireTime"), data.get("msg"), False
        return False, None, data.get("msg"), False
    except Exception as e:
        log("联网验证异常", "ERROR", {"err": str(e)})
        return False, None, f"网络异常：{e}", True


def get_hardware_id():
    parts = []
    if os.name == 'nt':
        try:
            import wmi
            c = wmi.WMI()
            for cpu in c.Win32_Processor():
                if cpu.ProcessorId:
                    parts.append(f"cpu:{cpu.ProcessorId}"); break
            for b in c.Win32_BaseBoard():
                if b.SerialNumber and b.SerialNumber.strip():
                    parts.append(f"board:{b.SerialNumber.strip()}"); break
            for d in c.Win32_DiskDrive():
                if d.SerialNumber and d.SerialNumber.strip():
                    parts.append(f"disk:{d.SerialNumber.strip()}"); break
            for b in c.Win32_BIOS():
                if b.SerialNumber and b.SerialNumber.strip():
                    parts.append(f"bios:{b.SerialNumber.strip()}"); break
        except Exception:
            try:
                import winreg
                k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                   r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
                pid = winreg.QueryValueEx(k, "ProductId")[0]
                if pid: parts.append(f"pid:{pid}")
                winreg.CloseKey(k)
            except Exception:
                pass
    else:
        for p in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
            if os.path.exists(p):
                try:
                    with open(p, 'r') as f:
                        mid = f.read().strip()
                    if mid:
                        parts.append(f"machineid:{mid}"); break
                except Exception:
                    pass
    try:
        parts.append(f"cpu:{platform.processor() or platform.machine()}")
        parts.append(f"sys:{platform.system()}{platform.release()}")
    except Exception:
        pass
    if not parts:
        try:
            mac = uuid_lib.getnode()
            if mac != 0xffffffffffff:
                parts.append(f"mac:{mac}")
        except Exception:
            pass
    if not parts:
        parts.append(f"fallback:{uuid_lib.uuid4()}")
    h = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def verify_license(key):
    """验证卡密。必须联网成功才算通过，网络异常直接失败。"""
    if not key or not key.strip():
        return False, {"msg": "卡密为空"}
    key = key.strip()
    device_id = get_hardware_id()

    ok, expire, msg, net_err = online_check(key, device_id)

    if ok and expire and expire > int(time.time() * 1000):
        save_cache({"key": key, "uuid": device_id,
                    "expire_time": expire, "verified_at": int(time.time())})
        _apply_license(key, expire, msg)
        return True, {"key": key, "uuid": device_id, "expire_time": expire, "msg": msg}

    # 失败：清缓存 + 降级
    _clear_license()
    if net_err:
        return False, {"msg": "网络异常，请检查网络后重试"}
    if ok and (not expire or expire <= int(time.time() * 1000)):
        return False, {"msg": "卡密已过期"}
    return False, {"msg": msg or "验证失败"}


def is_advanced_allowed():
    return LICENSE_STATUS.get("valid", False)


def auth_on_start():
    """启动时校验授权。不比较本地设备指纹，一律拿去服务端验证。
    必须联网成功，网络异常直接降级普通版。"""
    cache = load_cache()
    if not cache.get("key"):
        _clear_license()
        return

    key = cache["key"]
    device_id = get_hardware_id()

    # 不管 uuid 有没有变，都拿 key 去服务端验证
    ok, expire, msg, net_err = online_check(key, device_id)

    if ok and expire and expire > int(time.time() * 1000):
        _apply_license(key, expire, msg or "验证通过")
        # 服务端认可就更新本地 uuid 为当前设备
        save_cache({"key": key, "uuid": device_id,
                    "expire_time": expire, "verified_at": int(time.time())})
        log("启动卡密验证通过", "INFO", {"key": key, "uuid": device_id})
        return

    _clear_license()
    if net_err:
        log("启动卡密验证失败：网络异常，降级普通版", "WARN", {"key": key})
    else:
        log("启动卡密验证失败，降级普通版", "WARN", {"key": key, "msg": msg})


def run_key_exe():
    kp = os.path.join(BASE_DIR, KEY_EXE)
    if not os.path.exists(kp):
        return
    try:
        if os.name == 'nt':
            res = subprocess.run(['tasklist', '/FI', f'IMAGENAME eq {KEY_EXE}'],
                                 capture_output=True, text=True, timeout=5)
            if KEY_EXE.lower() in res.stdout.lower():
                return
        else:
            res = subprocess.run(['pgrep', '-f', KEY_EXE], capture_output=True, text=True)
            if res.returncode == 0:
                return
    except Exception:
        pass
    try:
        if os.name == 'nt':
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.Popen([kp], startupinfo=si)
        else:
            subprocess.Popen([kp])
    except Exception as e:
        log("启动卡密服务失败", "ERROR", {"err": str(e)})


def kill_key_exe():
    try:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/f', '/im', KEY_EXE], capture_output=True, timeout=5)
        else:
            subprocess.run(['pkill', '-f', KEY_EXE], capture_output=True, timeout=5)
    except Exception:
        pass


# ---------- 路径 ----------
def safe_path(p, allow_system=False):
    if not p or not isinstance(p, str):
        return False
    try:
        expanded = os.path.expanduser(p)
        norm = os.path.normpath(os.path.abspath(expanded))
        if not os.path.isabs(norm):
            return False
        if not os.path.isabs(p) and '..' in p.split(os.sep):
            return False
        if not allow_system:
            forbidden = [
                os.environ.get('SystemRoot', r'C:\Windows'),
                r'C:\Windows\System32',
                r'C:\Windows\SysWOW64',
            ]
            low = norm.lower()
            for f in forbidden:
                if not f: continue
                fl = f.lower()
                if low == fl or low.startswith(fl + os.sep):
                    return False
        return True
    except Exception:
        return False


def _path_under_base(full_path, base_path):
    try:
        full = os.path.realpath(full_path)
        base = os.path.realpath(base_path)
        return os.path.commonpath([full, base]) == base
    except Exception:
        return False


def _human_size(n):
    for unit in ('B','KB','MB','GB','TB'):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"


# ---------- 对话框 ----------
class DialogBox:
    def __init__(self, master, cfg):
        self.master = master; self.cfg = cfg
        self.result = {}; self.vars = {}
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
            ct = ctrl.get('type', 'label')
            label = ctrl.get('label', '')
            default = ctrl.get('default', '')
            options = ctrl.get('options', [])
            cid = ctrl.get('id', f'ctrl_{row}')
            if ct == 'label':
                ttk.Label(main, text=label, wraplength=400).grid(row=row, column=0, columnspan=2, sticky='w', pady=2)
                row += 1
            elif ct == 'image':
                src = ctrl.get('src', '')
                if src:
                    try:
                        if src.startswith(('http://', 'https://')):
                            # 带 UA 拉取远程图片
                            with http_open(src, timeout=10) as r:
                                img = Image.open(io.BytesIO(r.read()))
                        else:
                            img = Image.open(src)
                        img.thumbnail((800, 600), Image.Resampling.LANCZOS)
                        photo = ImageTk.PhotoImage(img)
                        lbl = ttk.Label(main, image=photo); lbl.image = photo
                        lbl.grid(row=row, column=0, columnspan=2, pady=5)
                    except Exception:
                        ttk.Label(main, text=f"图片加载失败: {src}").grid(row=row, column=0, columnspan=2, pady=2)
                row += 1
            elif ct == 'entry':
                if label:
                    ttk.Label(main, text=label).grid(row=row, column=0, sticky='e', padx=5)
                var = tk.StringVar(value=default)
                ttk.Entry(main, textvariable=var, width=30).grid(row=row, column=1, sticky='w', pady=2)
                self.vars[cid] = var; row += 1
            elif ct == 'text':
                if label:
                    ttk.Label(main, text=label).grid(row=row, column=0, sticky='ne', padx=5)
                tw = scrolledtext.ScrolledText(main, height=ctrl.get('rows', 5), width=40)
                tw.insert('1.0', default)
                tw.grid(row=row, column=1, sticky='w', pady=2)
                self.vars[cid] = tw; row += 1
            elif ct == 'password':
                if label:
                    ttk.Label(main, text=label).grid(row=row, column=0, sticky='e', padx=5)
                var = tk.StringVar(value=default)
                ttk.Entry(main, textvariable=var, show='*', width=30).grid(row=row, column=1, sticky='w', pady=2)
                self.vars[cid] = var; row += 1
            elif ct == 'combobox':
                if label:
                    ttk.Label(main, text=label).grid(row=row, column=0, sticky='e', padx=5)
                var = tk.StringVar(value=default if default in options else (options[0] if options else ''))
                ttk.Combobox(main, textvariable=var, values=options, state='readonly', width=28)\
                    .grid(row=row, column=1, sticky='w', pady=2)
                self.vars[cid] = var; row += 1
            elif ct == 'checkbox':
                if label:
                    ttk.Label(main, text=label).grid(row=row, column=0, sticky='ne', padx=5)
                frm = ttk.Frame(main); frm.grid(row=row, column=1, sticky='w', pady=2)
                vars_list = []
                for opt in options:
                    var = tk.BooleanVar(value=(opt in default if default else False))
                    ttk.Checkbutton(frm, text=opt, variable=var).pack(anchor='w')
                    vars_list.append((opt, var))
                self.vars[cid] = vars_list; row += 1
            elif ct == 'radio':
                if label:
                    ttk.Label(main, text=label).grid(row=row, column=0, sticky='ne', padx=5)
                frm = ttk.Frame(main); frm.grid(row=row, column=1, sticky='w', pady=2)
                var = tk.StringVar(value=default if default in options else (options[0] if options else ''))
                for opt in options:
                    ttk.Radiobutton(frm, text=opt, variable=var, value=opt).pack(anchor='w')
                self.vars[cid] = var; row += 1
            elif ct == 'progress':
                if label:
                    ttk.Label(main, text=label).grid(row=row, column=0, sticky='e', padx=5)
                var = tk.IntVar(value=ctrl.get('value', 0))
                ttk.Progressbar(main, variable=var, maximum=ctrl.get('maximum', 100), length=250)\
                    .grid(row=row, column=1, sticky='w', pady=2)
                self.vars[cid] = var; row += 1
            else:
                ttk.Label(main, text=f"未知控件: {ct}").grid(row=row, column=0, columnspan=2, pady=2)
                row += 1
        bf = ttk.Frame(self.window); bf.pack(pady=10)
        for bt in buttons:
            ttk.Button(bf, text=bt, command=lambda b=bt: self.on_button(b)).pack(side=tk.LEFT, padx=5)

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
        return dlg.result
    except Exception as e:
        log("对话框异常", "ERROR", {"err": str(e)})
        return None


# ---------- 卡密窗口 ----------
class LicenseWindow:
    def __init__(self, master):
        self.master = master; self.result = None
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

        main = ttk.Frame(self.window, padding=30); main.pack(fill=tk.BOTH, expand=True)
        ttk.Label(main, text="🔑 输入卡密", font=("微软雅黑", 16, "bold"), foreground="#2b6f9e").pack(pady=(0,5))
        ttk.Label(main, text="粘贴或输入您的卡密，验证通过后解锁高级功能",
                  font=("微软雅黑", 10), foreground="#6a8aa8").pack(pady=(0,20))

        self.key_var = tk.StringVar()
        e = ttk.Entry(main, textvariable=self.key_var, font=("Consolas", 13), width=32)
        e.pack(fill=tk.X, pady=5, ipady=4); e.focus_set()
        e.bind('<Return>', lambda ev: self.do_verify())

        self.msg_var = tk.StringVar()
        self.msg_label = ttk.Label(main, textvariable=self.msg_var,
                                   font=("微软雅黑", 9), foreground="#cc0000")
        self.msg_label.pack(pady=(6, 12))

        bf = ttk.Frame(main); bf.pack(pady=5)
        self.verify_btn = ttk.Button(bf, text="✓ 验证卡密", command=self.do_verify, width=14)
        self.verify_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(bf, text="✕ 取消", command=self.cancel, width=10).pack(side=tk.LEFT, padx=5)
        self.processing = False
        self.window.protocol("WM_DELETE_WINDOW", self.cancel)

    def do_verify(self):
        if self.processing: return
        key = self.key_var.get().strip()
        if not key:
            self.msg_var.set("请输入卡密"); return
        self.processing = True
        self.verify_btn.config(state='disabled', text='验证中…')
        self.msg_var.set("")
        def worker():
            ok, info = verify_license(key)
            self.window.after(0, lambda: self.finish(ok, info))
        threading.Thread(target=worker, daemon=True).start()

    def finish(self, ok, info):
        self.processing = False
        self.verify_btn.config(state='normal', text='✓ 验证卡密')
        if ok:
            self.msg_var.set("✅ 验证通过！")
            self.msg_label.config(foreground="#00aa00")
            self.result = {"key": info.get("key"), "expire": info.get("expire_time")}
            self.window.after(700, self.close)
        else:
            self.msg_var.set(f"✗ {info.get('msg', '验证失败')}")
            self.msg_label.config(foreground="#cc0000")

    def cancel(self):
        self.result = None; self.close()
    def close(self):
        self.window.destroy()
    def run(self):
        self.window.grab_set(); self.window.wait_window()
        return self.result


# ---------- 基础 API ----------
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
        subprocess.Popen(cmd)
        return {"code": 0, "msg": "已启动"}
    except Exception as e:
        return {"code": -1, "msg": str(e)}


def show_msg(text, typ="info", title="来自网页", image=None, w=0, h=0):
    if image:
        cfg = {'title': title, 'width': w or 500, 'height': h or 400,
               'controls': [{'type': 'image', 'src': image}, {'type': 'label', 'text': text}],
               'buttons': ['确定']}
        return {"code": 0, "data": show_dialog(cfg)}
    top = tk.Toplevel(MAIN_ROOT); top.attributes('-topmost', True); top.withdraw()
    funcs = {'info': messagebox.showinfo, 'warning': messagebox.showwarning, 'error': messagebox.showerror,
             'question': messagebox.askquestion, 'yesno': messagebox.askyesno,
             'okcancel': messagebox.askokcancel, 'yesnocancel': messagebox.askyesnocancel}
    if typ in funcs:
        res = funcs[typ](title, text, parent=top)
        top.destroy(); return {"code": 0, "data": res}
    messagebox.showinfo(title, text, parent=top); top.destroy()
    return {"code": 0}


# ---------- 文件操作 ----------
def list_dir(path):
    if not path or not safe_path(path) or not os.path.isdir(path):
        return {"code": -1, "msg": "无效目录"}
    try:
        items = []
        for name in os.listdir(path):
            full = os.path.join(path, name)
            try:
                st = os.stat(full)
            except OSError:
                continue
            items.append({
                "name": name,
                "is_dir": os.path.isdir(full),
                "size": st.st_size if not os.path.isdir(full) else 0,
                "size_str": '' if os.path.isdir(full) else _human_size(st.st_size),
                "mtime": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })
        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        return {"code": 0, "data": items}
    except Exception as e:
        return {"code": -1, "msg": str(e)}


MAX_READ_BYTES = 8 * 1024 * 1024

def read_file(path, start_line=None, end_line=None, max_bytes=MAX_READ_BYTES):
    if not path or not safe_path(path) or not os.path.isfile(path):
        return {"code": -1, "msg": "文件不存在"}
    try:
        size = os.path.getsize(path)
    except Exception:
        size = 0
    for enc in ['utf-8', 'utf-8-sig', 'gbk', 'latin-1']:
        try:
            with open(path, 'r', encoding=enc, errors='replace') as f:
                if start_line is not None or end_line is not None:
                    s = (start_line or 1) - 1
                    e = end_line if end_line is not None else s + 2000
                    lines = []
                    for i, ln in enumerate(f):
                        if i < s: continue
                        if i >= e: break
                        lines.append(ln)
                    return {"code": 0, "data": ''.join(lines), "encoding": enc,
                            "lines": len(lines), "total_size": size}
                truncated = False
                if size > max_bytes:
                    data = f.read(max_bytes); truncated = True
                else:
                    data = f.read()
            return {"code": 0, "data": data, "encoding": enc, "total_size": size,
                    "truncated": truncated, "read_bytes": len(data)}
        except UnicodeDecodeError:
            continue
        except Exception as e:
            return {"code": -1, "msg": str(e)}
    return {"code": -1, "msg": "无法解码"}


def write_file(path, content, encoding='utf-8', append=False):
    if not path or not safe_path(path):
        return {"code": -1, "msg": "路径无效"}
    mode = 'a' if append else 'w'
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)) or '.', exist_ok=True)
        with open(path, mode, encoding=encoding, newline='') as f:
            f.write(content or '')
        return {"code": 0, "msg": "ok", "data": {"path": path, "size": os.path.getsize(path)}}
    except Exception as e:
        return {"code": -1, "msg": str(e)}


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


def rename_path(path, new_name):
    if not path or not safe_path(path):
        return {"code": -1, "msg": "路径无效"}
    if not os.path.exists(path):
        return {"code": -1, "msg": "路径不存在"}
    if os.sep in new_name or '/' in new_name or '\\' in new_name:
        return {"code": -1, "msg": "新名称不能包含路径分隔符"}
    parent = os.path.dirname(os.path.abspath(path))
    target = os.path.join(parent, new_name)
    if os.path.exists(target):
        return {"code": -1, "msg": "目标名称已存在"}
    try:
        os.rename(path, target)
        return {"code": 0, "data": {"old": path, "new": target}}
    except Exception as e:
        return {"code": -1, "msg": str(e)}


def get_file_info(path):
    if not path or not safe_path(path) or not os.path.exists(path):
        return {"code": -1, "msg": "路径不存在"}
    try:
        st = os.stat(path)
        info = {
            "path": os.path.abspath(path),
            "name": os.path.basename(path),
            "is_dir": os.path.isdir(path),
            "size": st.st_size if os.path.isfile(path) else 0,
            "ctime": datetime.fromtimestamp(st.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
            "mtime": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "atime": datetime.fromtimestamp(st.st_atime).strftime("%Y-%m-%d %H:%M:%S"),
        }
        if os.path.isfile(path):
            ext = os.path.splitext(path)[1].lower()
            info["ext"] = ext
            info["is_text"] = ext in {'.txt','.log','.json','.py','.js','.html','.css',
                                      '.md','.xml','.yml','.yaml','.ini','.cfg','.csv',
                                      '.tsv','.bat','.cmd','.ps1','.sh'}
        if os.name == 'nt':
            try:
                attrs = os.stat(path).st_file_attributes
                info["hidden"] = bool(attrs & 0x2)
                info["readonly"] = bool(attrs & 0x1)
                info["system"] = bool(attrs & 0x4)
                info["archive"] = bool(attrs & 0x20)
            except Exception:
                pass
        return {"code": 0, "data": info}
    except Exception as e:
        return {"code": -1, "msg": str(e)}


def dir_size(path):
    if not path or not safe_path(path) or not os.path.isdir(path):
        return {"code": -1, "msg": "无效目录"}
    total = 0; fc = 0; dc = 0
    try:
        for root, dirs, files in os.walk(path):
            dc += len(dirs)
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f)); fc += 1
                except OSError:
                    pass
        return {"code": 0, "data": {"bytes": total, "human": _human_size(total),
                                     "files": fc, "dirs": dc}}
    except Exception as e:
        return {"code": -1, "msg": str(e)}


def replace_in_file(path, find, replace, use_regex=False, count=0, encoding='utf-8'):
    if not path or not safe_path(path) or not os.path.isfile(path):
        return {"code": -1, "msg": "文件不存在"}
    if not find:
        return {"code": -1, "msg": "查找内容为空"}
    try:
        with open(path, 'r', encoding=encoding, errors='replace') as f:
            content = f.read()
        if use_regex:
            new_content, n = re.subn(find, replace, content, count=count)
        else:
            n = content.count(find) if count == 0 else min(count, content.count(find))
            new_content = content.replace(find, replace, count if count > 0 else -1)
        if n > 0:
            if ADVANCED_AVAILABLE:
                try: save_version(path)
                except Exception: pass
            with open(path, 'w', encoding=encoding, newline='') as f:
                f.write(new_content)
        return {"code": 0, "data": {"replacements": n, "path": path}}
    except Exception as e:
        return {"code": -1, "msg": str(e)}


def get_log(lines=100):
    try:
        if not os.path.exists(LOG_PATH):
            return {"code": 0, "data": "日志文件尚未生成。"}
        with open(LOG_PATH, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        return {"code": 0, "data": ''.join(all_lines[-lines:])}
    except Exception:
        return {"code": -1, "msg": "读取日志失败"}


def lanzou_dl(url, pwd='', save_path=''):
    try:
        api = f"https://api.bugpk.com/api/lanzou?url={urllib.parse.quote(url)}"
        if pwd:
            api += f"&pwd={urllib.parse.quote(pwd)}"
        # 带 UA
        data = http_get_json(api, timeout=30)
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
        # 带 UA 下载
        http_download(real_url, save_path, timeout=60)
        return True, filename, save_path, None
    except Exception as e:
        return False, None, None, str(e)


# ---------- Windows 专属 ----------
def set_file_attr(path, hidden=None, readonly=None, system=None, archive=None):
    if os.name != 'nt':
        return {"code": -1, "msg": "仅支持 Windows"}
    if not path or not safe_path(path) or not os.path.exists(path):
        return {"code": -1, "msg": "路径不存在"}
    try:
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
        if attrs == -1:
            return {"code": -1, "msg": "读取属性失败"}
        FILE_ATTRIBUTE_HIDDEN    = 0x02
        FILE_ATTRIBUTE_READONLY  = 0x01
        FILE_ATTRIBUTE_SYSTEM    = 0x04
        FILE_ATTRIBUTE_ARCHIVE   = 0x20
        def apply(cur, flag, val):
            if val is None: return cur
            return (cur | flag) if val else (cur & ~flag)
        attrs = apply(attrs, FILE_ATTRIBUTE_HIDDEN, hidden)
        attrs = apply(attrs, FILE_ATTRIBUTE_READONLY, readonly)
        attrs = apply(attrs, FILE_ATTRIBUTE_SYSTEM, system)
        attrs = apply(attrs, FILE_ATTRIBUTE_ARCHIVE, archive)
        ok = ctypes.windll.kernel32.SetFileAttributesW(str(path), attrs)
        if ok:
            return {"code": 0, "msg": "属性已更新", "attrs": attrs}
        return {"code": -1, "msg": "设置失败"}
    except Exception as e:
        return {"code": -1, "msg": str(e)}


def delete_to_recyclebin(path):
    if os.name != 'nt':
        return delete_path(path, recursive=True)
    if not path or not safe_path(path) or not os.path.exists(path):
        return {"code": -1, "msg": "路径不存在"}
    try:
        class SHFILEOPSTRUCTW(ctypes.Structure):
            _fields_ = [
                ("hwnd", ctypes.c_void_p),
                ("wFunc", ctypes.c_uint),
                ("pFrom", ctypes.c_wchar_p),
                ("pTo", ctypes.c_wchar_p),
                ("fFlags", ctypes.c_ushort),
                ("fAnyOperationsAborted", ctypes.c_int),
                ("hNameMappings", ctypes.c_void_p),
                ("lpszProgressTitle", ctypes.c_wchar_p),
            ]
        FO_DELETE = 3
        FOF_ALLOWUNDO = 0x0040
        FOF_NOCONFIRMATION = 0x0010
        FOF_SILENT = 0x0004
        FOF_NOERRORUI = 0x0400
        op = SHFILEOPSTRUCTW()
        op.wFunc = FO_DELETE
        op.pFrom = os.path.abspath(path) + '\x00\x00'
        op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
        res = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
        if res == 0:
            return {"code": 0, "msg": "已移入回收站"}
        return {"code": -1, "msg": f"SHFileOperation 失败 code={res}"}
    except Exception as e:
        return {"code": -1, "msg": str(e)}


def reveal_in_explorer(path):
    if os.name != 'nt':
        return {"code": -1, "msg": "仅支持 Windows"}
    if not path or not safe_path(path) or not os.path.exists(path):
        return {"code": -1, "msg": "路径不存在"}
    try:
        subprocess.Popen(['explorer', '/select,', os.path.abspath(path)])
        return {"code": 0, "msg": "已在资源管理器中显示"}
    except Exception as e:
        return {"code": -1, "msg": str(e)}


def notify(title, message):
    try:
        if tray_icon:
            tray_icon.notify(message, title)
            return True
    except Exception:
        pass
    return False


# ---------- 依赖 ----------
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


# ---------- 剪贴板 ----------
_clip_last = None
def _clipboard_worker():
    global _clip_last
    if os.name != 'nt':
        return
    try:
        import win32clipboard
    except ImportError:
        log("未安装 pywin32，剪贴板历史功能禁用", "WARN")
        return
    while True:
        try:
            win32clipboard.OpenClipboard()
            try:
                text = None
                if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                    text = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                elif win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_TEXT):
                    t = win32clipboard.GetClipboardData(win32clipboard.CF_TEXT)
                    if isinstance(t, bytes):
                        t = t.decode('gbk', errors='ignore')
                    text = t
                if text and text != _clip_last:
                    _clip_last = text
                    CLIPBOARD_HISTORY.append({
                        "content": text,
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
            finally:
                win32clipboard.CloseClipboard()
        except Exception:
            pass
        time.sleep(1.2)


def start_clipboard_monitor():
    if os.name == 'nt':
        threading.Thread(target=_clipboard_worker, daemon=True).start()


# ---------- 定时 / 监听 ----------
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
            except Exception:
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
            except Exception:
                pass
        return {}

    def save_watches(watches):
        with open(WATCH_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(watches, f, indent=2)

    def _sync_dirs_internal(src, dest, mode="mirror", exclude=None):
        if not safe_path(src) or not safe_path(dest) or not os.path.isdir(src):
            return {"code": -1, "msg": "路径无效"}
        os.makedirs(dest, exist_ok=True)
        exclude = exclude or []
        try:
            for root, _, files in os.walk(src):
                rel = os.path.relpath(root, src)
                tr = os.path.join(dest, rel)
                os.makedirs(tr, exist_ok=True)
                for f in files:
                    if any(f.endswith(ext) for ext in exclude):
                        continue
                    shutil.copy2(os.path.join(root, f), os.path.join(tr, f))
            return {"code": 0, "msg": "同步完成"}
        except Exception as e:
            return {"code": -1, "msg": str(e)}

    def execute_task(name):
        tasks = load_tasks()
        if name not in tasks or not tasks[name].get("active", True):
            return
        task = tasks[name]
        action = task.get("action")
        params = task.get("params", {})
        if action == "sync":
            src = params.get("src"); dest = params.get("dest")
            if src and dest:
                _sync_dirs_internal(src, dest, params.get("mode", "mirror"), params.get("exclude", []))

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
        vd = os.path.join(VERSIONS_ROOT, hashlib.md5(rel.encode()).hexdigest()[:16])
        os.makedirs(vd, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        vf = os.path.join(vd, f"{ts}_{os.path.basename(path)}")
        try:
            shutil.copy2(path, vf)
        except Exception as e:
            log("保存版本失败", "ERROR", {"err": str(e)})


# ---------- 高级函数 ----------
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
            tr = os.path.join(dest, rel)
            os.makedirs(tr, exist_ok=True)
            for f in files:
                if any(f.endswith(ext) for ext in exclude):
                    continue
                shutil.copy2(os.path.join(root, f), os.path.join(tr, f))
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
    except Exception:
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
                except Exception:
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
                try:
                    if os.path.getsize(full) < min_size:
                        continue
                    with open(full, 'rb') as fp:
                        h = hashlib.md5(fp.read()).hexdigest() if algorithm == "md5" else hashlib.sha1(fp.read()).hexdigest()
                    hashes.setdefault(h, []).append(full)
                except OSError:
                    pass
        dups = [{"hash": h, "paths": p} for h, p in hashes.items() if len(p) > 1]
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


# ---------- 共享 ----------
def create_share_session(path, expires_in=3600, password='', readonly=True,
                         upload=False, note='', max_access=0):
    if not safe_path(path) or not os.path.exists(path):
        return None
    token = secrets.token_hex(8)
    expiry = time.time() + expires_in
    with share_sessions_lock:
        share_sessions[token] = {
            'path': os.path.abspath(path),
            'expires': expiry,
            'readonly': readonly and not upload,
            'password': password,
            'created': time.time(),
            'note': note,
            'access_count': 0,
            'max_access': max_access,
        }
        save_share_sessions()
    log("创建共享会话", "INFO", {"token": token, "path": path, "expires": expires_in})
    return token


def validate_share_token(token, password=None):
    """
    校验共享会话。
    返回 (path, reason)：
      ok / not_found / expired / password / access_limit
    """
    clean_expired_sessions()
    with share_sessions_lock:
        session = share_sessions.get(token)
        if not session:
            return None, 'not_found'
        if session.get('expires', 0) < time.time():
            del share_sessions[token]; save_share_sessions()
            return None, 'expired'
        if session.get('password') and session['password'] != password:
            return None, 'password'
        max_access = session.get('max_access', 0)
        if max_access and session.get('access_count', 0) >= max_access:
            return None, 'access_limit'
        session['access_count'] = session.get('access_count', 0) + 1
        return session['path'], 'ok'


_ICON_MAP = {
    '.png':'🖼️','.jpg':'🖼️','.jpeg':'🖼️','.gif':'🖼️','.bmp':'🖼️','.webp':'🖼️','.svg':'🖼️',
    '.mp4':'🎬','.avi':'🎬','.mkv':'🎬','.mov':'🎬','.wmv':'🎬','.flv':'🎬',
    '.mp3':'🎵','.wav':'🎵','.flac':'🎵','.aac':'🎵','.ogg':'🎵',
    '.zip':'📦','.rar':'📦','.7z':'📦','.tar':'📦','.gz':'📦',
    '.pdf':'📕','.doc':'📘','.docx':'📘','.xls':'📗','.xlsx':'📗','.ppt':'📙','.pptx':'📙',
    '.txt':'📝','.md':'📝','.log':'📝',
    '.py':'🐍','.js':'📜','.html':'🌐','.css':'🎨','.json':'⚙️','.xml':'⚙️',
    '.exe':'⚡','.msi':'⚡','.bat':'⚡','.cmd':'⚡','.ps1':'⚡',
    '.iso':'💿','.apk':'📱','.dmg':'💿',
}

PASSWORD_PAGE_TEMPLATE = r'''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>输入密码 · BJS 文件共享</title>
<style>
  :root{--primary:#2b6f9e;--primary-dark:#1a3a5c;--bg:#f0f4f8;--card:#fff;
        --border:#dce2ea;--text:#1e2d3d;--muted:#6f8ba0;--accent:#e8f4ff;}
  *{box-sizing:border-box;}
  body{margin:0;font-family:-apple-system,"Segoe UI","Microsoft YaHei",Arial,sans-serif;
       background:var(--bg);color:var(--text);min-height:100vh;
       display:flex;align-items:center;justify-content:center;padding:20px;}
  .box{background:var(--card);border-radius:14px;padding:36px 32px;max-width:400px;width:100%;
       box-shadow:0 8px 32px rgba(0,0,0,.08);border:1px solid var(--border);text-align:center;}
  .icon{font-size:52px;margin-bottom:12px;}
  h1{font-size:20px;margin:0 0 6px;color:var(--primary-dark);}
  .sub{color:var(--muted);font-size:13px;margin-bottom:22px;line-height:1.5;}
  input[type=password]{width:100%;padding:12px 14px;border:1px solid var(--border);
    border-radius:8px;font-size:15px;outline:none;transition:.15s;margin-bottom:14px;
    font-family:inherit;}
  input[type=password]:focus{border-color:var(--primary);box-shadow:0 0 0 3px var(--accent);}
  button{width:100%;padding:12px;border:none;border-radius:8px;background:var(--primary);
    color:#fff;font-size:15px;font-weight:600;cursor:pointer;transition:.15s;
    font-family:inherit;}
  button:hover{background:var(--primary-dark);}
  .err{color:#c0392b;font-size:13px;margin-top:12px;min-height:18px;}
</style>
</head>
<body>
<div class="box">
  <div class="icon">🔒</div>
  <h1>此分享需要密码</h1>
  <div class="sub">请输入访问密码以查看共享内容</div>
  <form method="get" autocomplete="off">
    <input type="password" name="pwd" placeholder="访问密码" autofocus required>
    <button type="submit">进入</button>
  </form>
  <div class="err">{% if show_error %}密码错误，请重试{% endif %}</div>
</div>
</body>
</html>
'''

INVALID_PAGE_TEMPLATE = r'''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>访问失败 · BJS 文件共享</title>
<style>
  body{margin:0;font-family:-apple-system,"Segoe UI","Microsoft YaHei",Arial,sans-serif;
       background:#f0f4f8;color:#333;display:flex;align-items:center;justify-content:center;
       min-height:100vh;padding:20px;}
  .box{background:#fff;padding:40px;border-radius:12px;display:inline-block;
       box-shadow:0 8px 32px rgba(0,0,0,.1);text-align:center;max-width:400px;}
  h1{color:#c0392b;margin:0 0 12px;font-size:22px;}
  p{color:#666;line-height:1.6;margin:8px 0;}
</style>
</head>
<body>
<div class="box">
  <h1>🔒 访问失败</h1>
  <p>{{ message }}</p>
</div>
</body>
</html>
'''


SHARE_PAGE_TEMPLATE = r'''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ name }} - BJS 文件共享</title>
<style>
  :root{--primary:#2b6f9e;--primary-dark:#1a3a5c;--bg:#f0f4f8;--card:#fff;
        --border:#dce2ea;--text:#1e2d3d;--muted:#6f8ba0;--hover:#eaf3fb;--accent:#e8f4ff;}
  *{box-sizing:border-box;}
  body{margin:0;font-family:-apple-system,"Segoe UI","Microsoft YaHei",Arial,sans-serif;
       background:var(--bg);color:var(--text);min-height:100vh;}
  header{background:linear-gradient(135deg,var(--primary),var(--primary-dark));
         color:#fff;padding:22px 28px;box-shadow:0 2px 12px rgba(0,0,0,.12);}
  header h1{margin:0;font-size:22px;font-weight:600;display:flex;align-items:center;gap:10px;flex-wrap:wrap;}
  header .sub{opacity:.85;font-size:12px;margin-top:6px;word-break:break-all;}
  .toolbar{display:flex;flex-wrap:wrap;gap:10px;padding:14px 28px;background:#fff;
           border-bottom:1px solid var(--border);align-items:center;}
  .toolbar .path{font-size:13px;color:var(--muted);flex:1;min-width:200px;
                 word-break:break-all;font-family:Consolas,monospace;}
  .toolbar .path a{color:var(--primary);text-decoration:none;}
  .toolbar input[type=search]{padding:8px 12px;border:1px solid var(--border);border-radius:6px;
      font-size:13px;min-width:180px;outline:none;transition:.15s;}
  .toolbar input[type=search]:focus{border-color:var(--primary);box-shadow:0 0 0 3px var(--accent);}
  .btn{padding:8px 14px;border:none;border-radius:6px;background:var(--primary);color:#fff;
       cursor:pointer;font-size:13px;text-decoration:none;display:inline-flex;
       align-items:center;gap:6px;transition:.15s;}
  .btn:hover{background:var(--primary-dark);}
  .btn.ghost{background:transparent;color:var(--primary);border:1px solid var(--border);}
  .btn.ghost:hover{background:var(--hover);}
  main{padding:18px 28px 40px;}
  .breadcrumb{margin-bottom:14px;font-size:13px;color:var(--muted);}
  .breadcrumb a{color:var(--primary);text-decoration:none;}
  .list{background:var(--card);border:1px solid var(--border);border-radius:10px;
        overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.04);}
  .item{display:flex;align-items:center;padding:12px 16px;border-bottom:1px solid var(--border);
        transition:background .12s;}
  .item:last-child{border-bottom:none;}
  .item:hover{background:var(--hover);}
  .item .icon{font-size:22px;width:34px;text-align:center;flex-shrink:0;}
  .item .name{flex:1;color:var(--text);text-decoration:none;font-size:14px;
               word-break:break-all;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
  .item .name:hover{color:var(--primary);}
  .item .size{color:var(--muted);font-size:12px;margin-left:12px;
               font-family:Consolas,monospace;flex-shrink:0;}
  .item .actions{display:flex;gap:6px;margin-left:8px;flex-shrink:0;}
  .item .actions a{font-size:12px;color:var(--primary);text-decoration:none;
                    padding:3px 8px;border-radius:4px;transition:.15s;}
  .item .actions a:hover{background:var(--accent);}
  .empty{padding:48px;text-align:center;color:var(--muted);}
  .footer{text-align:center;color:var(--muted);font-size:12px;padding:20px;}
  .badge{display:inline-block;padding:2px 8px;border-radius:10px;background:rgba(255,255,255,.25);
         font-size:11px;margin-left:6px;}
  .upload-zone{margin-top:16px;padding:20px;border:2px dashed var(--border);
               border-radius:10px;text-align:center;color:var(--muted);
               transition:.15s;cursor:pointer;background:#fff;}
  .upload-zone.drag{border-color:var(--primary);background:var(--accent);}
  .upload-zone input{display:none;}
  .progress{margin-top:10px;height:6px;background:var(--border);border-radius:3px;overflow:hidden;display:none;}
  .progress .bar{height:100%;width:0;background:var(--primary);transition:width .2s;}
  @media(max-width:600px){header{padding:16px;} main{padding:12px;} .item .size{display:none;}}
</style>
</head>
<body>
<header>
  <h1>📁 BJS 文件共享<span class="badge">{{ mode_badge }}</span></h1>
  <div class="sub">当前目录：{{ display_path }}</div>
</header>

<div class="toolbar">
  <div class="path">
    {% for crumb in breadcrumbs %}{% if not loop.last %}<a href="{{ crumb.url }}">{{ crumb.name }}</a> / {% else %}{{ crumb.name }}{% endif %}{% endfor %}
  </div>
  <input type="search" id="filterBox" placeholder="筛选当前目录…" autocomplete="off">
  <button class="btn ghost" onclick="sortItems('name')">名称</button>
  <button class="btn ghost" onclick="sortItems('size')">大小</button>
  <button class="btn ghost" onclick="sortItems('time')">时间</button>
  {% if not readonly and items %}
  <a class="btn ghost" href="?zip=1{% if pwd %}&pwd={{ pwd|urlencode }}{% endif %}">⬇ 打包</a>
  {% endif %}
</div>

<main>
  {% if parent_url %}<div class="breadcrumb">⬅ <a href="{{ parent_url }}">返回上级目录</a></div>{% endif %}
  {% if items %}
  <div class="list" id="fileList">
    {% for item in items %}
    <div class="item" data-name="{{ item.name|lower }}" data-size="{{ item.size }}" data-time="{{ item.mtime_ts }}">
      <div class="icon">{% if item.is_dir %}📁{% else %}{{ item.icon }}{% endif %}</div>
      <a class="name" href="{{ item.url }}">{{ item.name }}</a>
      <div class="size">{% if not item.is_dir %}{{ item.size_str }}{% else %}文件夹{% endif %}</div>
      <div class="actions">
        {% if not item.is_dir %}
        <a href="{{ item.url }}" download>下载</a>
        {% if item.is_image %}<a href="{{ item.url }}" target="_blank">预览</a>{% endif %}
        {% endif %}
      </div>
    </div>
    {% endfor %}
  </div>
  {% else %}<div class="list"><div class="empty">此目录为空</div></div>{% endif %}

  {% if not readonly %}
  <div class="upload-zone" id="uploadZone">
    <input type="file" id="fileInput" multiple>
    <div>📤 点击或拖拽文件到此处上传</div>
    <div class="progress" id="progress"><div class="bar" id="progressBar"></div></div>
  </div>
  {% endif %}
</main>

<div class="footer">共享有效期至 {{ expires }} · 由 BJS 数据接力提供</div>

<script>
document.getElementById('filterBox')?.addEventListener('input', e=>{
  const kw = e.target.value.toLowerCase();
  document.querySelectorAll('#fileList .item').forEach(el=>{
    el.style.display = el.dataset.name.includes(kw) ? '' : 'none';
  });
});
let sortDir = {};
function sortItems(key){
  sortDir[key] = !sortDir[key];
  const list = document.getElementById('fileList'); if(!list) return;
  const items = Array.from(list.children);
  items.sort((a,b)=>{
    let av = a.dataset[key] || '', bv = b.dataset[key] || '';
    if(key==='size'||key==='time'){ av=parseFloat(av)||0; bv=parseFloat(bv)||0; }
    let r = av > bv ? 1 : av < bv ? -1 : 0;
    return sortDir[key] ? -r : r;
  });
  items.forEach(el=>list.appendChild(el));
}
const zone = document.getElementById('uploadZone');
const input = document.getElementById('fileInput');
if(zone && input){
  zone.addEventListener('click', ()=>input.click());
  ['dragenter','dragover'].forEach(ev=>zone.addEventListener(ev,e=>{
    e.preventDefault(); zone.classList.add('drag');
  }));
  ['dragleave','drop'].forEach(ev=>zone.addEventListener(ev,e=>{
    e.preventDefault(); zone.classList.remove('drag');
  }));
  zone.addEventListener('drop', e=>handleFiles(e.dataTransfer.files));
  input.addEventListener('change', ()=>handleFiles(input.files));
}
function handleFiles(files){
  if(!files || !files.length) return;
  const bar = document.getElementById('progressBar');
  const prog = document.getElementById('progress');
  prog.style.display='block';
  let done = 0;
  Array.from(files).forEach(file=>{
    const fd = new FormData();
    fd.append('file', file);
    fd.append('subpath', {{ subpath|tojson }});
    fd.append('pwd', {{ pwd|tojson }});
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/share/{{ token }}/upload', true);
    xhr.upload.onprogress = e=>{
      if(e.lengthComputable){
        bar.style.width = ((done + e.loaded/e.total) / files.length * 100) + '%';
      }
    };
    xhr.onload = ()=>{ done++; if(done===files.length){ bar.style.width='100%'; setTimeout(()=>location.reload(), 400); } };
    xhr.onerror = ()=>{ alert('上传失败：' + file.name); };
    xhr.send(fd);
  });
}
</script>
</body>
</html>
'''


# ---------- 插件 ----------
def load_plugin(name):
    pf = os.path.join(PLUGIN_DIR, f"{name}.py")
    if not os.path.exists(pf):
        return None
    spec = importlib.util.spec_from_file_location(name, pf)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def install_plugin(source, name):
    err = check_license()
    if err: return err
    try:
        if source.startswith(('http://', 'https://')):
            # 带 UA 下载插件
            with http_open(source, timeout=30) as r:
                content = r.read().decode('utf-8')
        else:
            with open(source, 'r', encoding='utf-8') as f:
                content = f.read()
        target = os.path.join(PLUGIN_DIR, f"{name}.py")
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
        return {"code": 0, "msg": f"插件 '{name}' 已安装"}
    except Exception as e:
        return {"code": -1, "msg": str(e)}


def exec_plugin(plugin, action):
    err = check_license()
    if err: return err
    mod = load_plugin(plugin)
    if not mod:
        return {"code": -1, "msg": f"插件 '{plugin}' 不存在"}
    if not hasattr(mod, action):
        return {"code": -1, "msg": f"插件 '{plugin}' 没有 '{action}' 方法"}
    try:
        result = getattr(mod, action)()
        return {"code": 0, "data": result}
    except Exception as e:
        return {"code": -1, "msg": str(e)}


# ---------- 多设备 / 远程 ----------
def sync_device(device_id, sync_path, auto_sync=False):
    err = check_license()
    if err: return err
    if not safe_path(sync_path) or not os.path.isdir(sync_path):
        return {"code": -1, "msg": "同步目录无效"}
    devices[device_id] = {
        'sync_path': os.path.abspath(sync_path),
        'auto_sync': auto_sync,
        'last_seen': time.time()
    }
    save_devices()
    return {"code": 0, "msg": f"设备 '{device_id}' 已配置"}


def generate_remote_token(expires_in=300, permissions=None):
    err = check_license()
    if err: return err
    token = secrets.token_hex(8)
    expiry = time.time() + expires_in
    path = os.path.expanduser("~")
    with share_sessions_lock:
        share_sessions[token] = {
            'path': path, 'expires': expiry, 'readonly': True,
            'password': '', 'created': time.time(), 'remote': True
        }
        save_share_sessions()
    ip = get_local_ip()
    return {"code": 0, "data": {"token": token, "url": f"http://{ip}:{HTTP_PORT}/share/{token}/"}}


def share_path(path, expires_in=3600, readonly=True, password='', upload=False, note=''):
    err = check_license()
    if err: return err
    if not safe_path(path) or not os.path.exists(path):
        return {"code": -1, "msg": "路径不存在或无效"}
    token = create_share_session(path, expires_in, password, readonly,
                                  upload=upload, note=note)
    if not token:
        return {"code": -1, "msg": "创建共享失败"}
    ip = get_local_ip()
    url = f"http://{ip}:{HTTP_PORT}/share/{token}/"
    if password:
        url += f"?pwd={urllib.parse.quote(password)}"
    return {"code": 0, "data": {"url": url, "token": token, "has_password": bool(password)}}


if ADVANCED_AVAILABLE:
    def schedule_task(name, trigger, expression, action, params):
        err = check_license()
        if err: return err
        tasks = load_tasks()
        if name in tasks:
            return {"code": -1, "msg": f"任务 '{name}' 已存在"}
        tasks[name] = {"trigger": trigger, "expression": expression,
                       "action": action, "params": params, "active": True}
        save_tasks(tasks)
        try:
            if trigger == "cron":
                scheduler.add_job(lambda: execute_task(name),
                                  CronTrigger.from_crontab(expression),
                                  id=f"task_{name}", replace_existing=True)
            else:
                scheduler.add_job(lambda: execute_task(name), 'interval',
                                  seconds=int(expression),
                                  id=f"task_{name}", replace_existing=True)
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
        config = {"path": path, "events": events, "filter": filter,
                  "action": action, "target": target, "active": True}
        watches[path] = config
        save_watches(watches)
        start_watch(path, config)
        return {"code": 0, "msg": f"已开始监听 {path}"}

    def get_file_versions(path):
        err = check_license()
        if err: return err
        if not os.path.exists(path):
            return {"code": -1, "msg": "文件不存在"}
        vd = os.path.join(VERSIONS_ROOT,
                          hashlib.md5(os.path.abspath(path).replace(":", "").replace("\\", "/").encode()).hexdigest()[:16])
        if not os.path.isdir(vd):
            return {"code": 0, "data": []}
        versions = []
        for f in os.listdir(vd):
            full = os.path.join(vd, f)
            if os.path.isfile(full):
                parts = f.split("_", 1)
                versions.append({
                    "version": parts[0] if len(parts) > 1 else "",
                    "file": f, "full_path": full,
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
        vd = os.path.join(VERSIONS_ROOT,
                          hashlib.md5(os.path.abspath(path).replace(":", "").replace("\\", "/").encode()).hexdigest()[:16])
        if not os.path.isdir(vd):
            return {"code": -1, "msg": "没有版本记录"}
        for f in os.listdir(vd):
            if f.startswith(version + "_"):
                try:
                    shutil.copy2(os.path.join(vd, f), path)
                    return {"code": 0, "msg": f"已恢复到版本 {version}"}
                except Exception as e:
                    return {"code": -1, "msg": str(e)}
        return {"code": -1, "msg": f"未找到版本 {version}"}


# ---------- Flask ----------
app = Flask(__name__)
CORS(app)


@app.before_request
def log_request():
    log(f"请求 {request.method} {request.path}", "INFO",
        {"remote_addr": request.remote_addr, "args": request.args.to_dict()})


@app.after_request
def log_response(response):
    log(f"响应 {request.method} {request.path} -> {response.status}", "INFO")
    return response


@app.route('/share/<token>/', defaults={'subpath': ''})
@app.route('/share/<token>/<path:subpath>')
def share_browse(token, subpath):
    password = request.args.get('pwd', '')
    base_path, reason = validate_share_token(token, password)

    if base_path is None:
        if reason == 'password':
            return render_template_string(
                PASSWORD_PAGE_TEMPLATE,
                show_error=bool(password)
            ), 401 if password else 200

        messages = {
            'not_found': '链接不存在或已被删除',
            'expired': '链接已过期',
            'access_limit': '链接访问次数已达上限',
        }
        return render_template_string(
            INVALID_PAGE_TEMPLATE,
            message=messages.get(reason, '访问失败')
        ), 403

    subpath = subpath.strip('/').replace('\\', '/')
    if subpath:
        full_path = os.path.join(base_path, *[p for p in subpath.split('/') if p and p != '.'])
    else:
        full_path = base_path
    if not _path_under_base(full_path, base_path):
        abort(403, description="越权访问")
    if not os.path.exists(full_path):
        abort(404, description="路径不存在")

    with share_sessions_lock:
        sess = share_sessions.get(token, {})
        readonly = sess.get('readonly', True)
        expires_time = sess.get('expires', 0)

    if os.path.isfile(full_path):
        return send_from_directory(os.path.dirname(full_path), os.path.basename(full_path))

    try:
        entries = os.listdir(full_path)
    except PermissionError:
        abort(403, description="无权限读取该目录")

    if request.args.get('zip') == '1' and not readonly:
        try:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
            with zipfile.ZipFile(tmp.name, 'w', zipfile.ZIP_DEFLATED) as z:
                for name in entries:
                    p = os.path.join(full_path, name)
                    if os.path.isfile(p):
                        z.write(p, name)
            return send_from_directory(os.path.dirname(tmp.name),
                                       os.path.basename(tmp.name),
                                       as_attachment=True,
                                       download_name=f"{os.path.basename(full_path) or 'share'}.zip")
        except Exception as e:
            abort(500, description=f"打包失败: {e}")

    items = []
    for name in entries:
        p = os.path.join(full_path, name)
        try:
            st = os.stat(p)
        except OSError:
            continue
        is_dir = os.path.isdir(p)
        ext = os.path.splitext(name)[1].lower()
        url = urllib.parse.quote(name) + ('/' if is_dir else '')
        items.append({
            'name': name, 'is_dir': is_dir,
            'size': 0 if is_dir else st.st_size,
            'size_str': '' if is_dir else _human_size(st.st_size),
            'mtime_ts': int(st.st_mtime),
            'icon': _ICON_MAP.get(ext, '📄'),
            'is_image': ext in {'.png','.jpg','.jpeg','.gif','.bmp','.webp','.svg'},
            'url': url,
        })
    items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))

    pwd_qs = f"?pwd={urllib.parse.quote(password)}" if password else ""
    breadcrumbs = [{'name': '🏠 根', 'url': f"/share/{token}/{pwd_qs}"}]
    if subpath:
        parts = subpath.split('/')
        acc = ''
        for part in parts:
            acc = (acc + '/' + part) if acc else part
            url = f"/share/{token}/{urllib.parse.quote(acc)}/{pwd_qs}"
            breadcrumbs.append({'name': part, 'url': url})

    parent_url = None
    if subpath:
        pp = subpath.split('/')[:-1]
        parent_url = f"/share/{token}/" + ('/'.join(urllib.parse.quote(p) for p in pp) + '/' if pp else '')
        if password:
            parent_url += f"?pwd={urllib.parse.quote(password)}"

    expires_str = datetime.fromtimestamp(expires_time).strftime('%Y-%m-%d %H:%M:%S') if expires_time else '已过期'

    return render_template_string(
        SHARE_PAGE_TEMPLATE,
        name=os.path.basename(full_path) or '共享根目录',
        display_path=full_path,
        breadcrumbs=breadcrumbs,
        parent_url=parent_url,
        items=items,
        expires=expires_str,
        token=token,
        subpath=subpath,
        pwd=password,
        readonly=readonly,
        mode_badge='只读' if readonly else '可上传',
    )


@app.route('/share/<token>/upload', methods=['POST'])
def share_upload(token):
    password = request.form.get('pwd', '') or request.args.get('pwd', '')
    base_path, reason = validate_share_token(token, password)
    if base_path is None:
        msg = '密码错误' if reason == 'password' else '无效或过期'
        return jsonify({"code": -1, "msg": msg}), 403
    with share_sessions_lock:
        sess = share_sessions.get(token, {})
    if sess.get('readonly', True):
        return jsonify({"code": -1, "msg": "只读共享，禁止上传"}), 403
    f = request.files.get('file')
    if not f or not f.filename:
        return jsonify({"code": -1, "msg": "未收到文件"}), 400
    target_sub = request.form.get('subpath', '').strip('/').replace('\\', '/')
    save_dir = os.path.join(base_path, *[p for p in target_sub.split('/') if p and p != '.']) if target_sub else base_path
    if not _path_under_base(save_dir, base_path):
        return jsonify({"code": -1, "msg": "越权"}), 403
    os.makedirs(save_dir, exist_ok=True)
    safe_name = os.path.basename(f.filename).replace('\x00', '')
    if not safe_name or safe_name in ('.', '..'):
        return jsonify({"code": -1, "msg": "文件名非法"}), 400
    save_path = os.path.join(save_dir, safe_name)
    base, ext = os.path.splitext(safe_name)
    i = 1
    while os.path.exists(save_path):
        save_path = os.path.join(save_dir, f"{base}_{i}{ext}")
        i += 1
    f.save(save_path)
    log("共享上传", "INFO", {"token": token, "file": save_path})
    return jsonify({"code": 0, "msg": "上传成功", "name": os.path.basename(save_path)})


# ---------- 基础路由 ----------
@app.route('/health')
def health():
    return jsonify({"code": 0, "status": "running", "port": HTTP_PORT, "version": VERSION})


@app.route('/api/open')
def api_open():
    return jsonify(open_path(request.args.get('path', '')))


@app.route('/api/msg', methods=['POST'])
def api_msg():
    d = request.json or {}
    return jsonify(show_msg(d.get('text',''), d.get('type','info'), d.get('title','来自网页'),
                            d.get('image'), d.get('width',0), d.get('height',0)))


@app.route('/api/run', methods=['POST'])
def api_run():
    d = request.json or {}
    return jsonify(run_prog(d.get('path',''), d.get('args'), d.get('wait', False)))


@app.route('/api/dialog', methods=['POST'])
def api_dialog():
    d = request.json or {}
    res = show_dialog(d.get('config', ''))
    return jsonify({"code": 0, "data": res} if res else {"code": -1, "msg": "对话框错误"})


@app.route('/api/listdir')
def api_listdir():
    return jsonify(list_dir(request.args.get('path', os.path.expanduser("~"))))


@app.route('/api/readfile')
def api_readfile():
    return jsonify(read_file(request.args.get('path', ''),
                             request.args.get('start_line', type=int),
                             request.args.get('end_line', type=int)))


@app.route('/api/writefile', methods=['POST'])
def api_writefile():
    d = request.json or {}
    return jsonify(write_file(d.get('path',''), d.get('content',''),
                              d.get('encoding','utf-8'), d.get('append', False)))


@app.route('/api/mkdir', methods=['POST'])
def api_mkdir():
    return jsonify(mkdir((request.json or {}).get('path', '')))


@app.route('/api/delete', methods=['POST'])
def api_delete():
    d = request.json or {}
    return jsonify(delete_path(d.get('path',''), d.get('recursive', False)))


@app.route('/api/copy', methods=['POST'])
def api_copy():
    d = request.json or {}
    return jsonify(copy_path(d.get('src',''), d.get('dest','')))


@app.route('/api/move', methods=['POST'])
def api_move():
    d = request.json or {}
    return jsonify(move_path(d.get('src',''), d.get('dest','')))


@app.route('/api/rename', methods=['POST'])
def api_rename():
    d = request.json or {}
    return jsonify(rename_path(d.get('path',''), d.get('new_name','')))


@app.route('/api/fileinfo')
def api_fileinfo():
    return jsonify(get_file_info(request.args.get('path','')))


@app.route('/api/dirsize')
def api_dirsize():
    return jsonify(dir_size(request.args.get('path','')))


@app.route('/api/replace', methods=['POST'])
def api_replace():
    d = request.json or {}
    return jsonify(replace_in_file(d.get('path',''), d.get('find',''), d.get('replace',''),
                                   d.get('regex', False), d.get('count', 0),
                                   d.get('encoding','utf-8')))


@app.route('/api/log')
def api_log():
    return jsonify(get_log(request.args.get('lines', 100, type=int)))


@app.route('/api/lanzou/download', methods=['POST'])
def api_lanzou():
    d = request.json or {}
    ok, name, path, err = lanzou_dl(d.get('url',''), d.get('pwd',''), d.get('save_path',''))
    if ok:
        return jsonify({"code": 0, "data": {"filename": name, "save_path": path}})
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
    except Exception:
        return jsonify({"code": 0, "data": {"system": platform.system(), "release": platform.release()}})


@app.route('/api/license/status')
def api_license_status():
    return jsonify({"code": 0, "data": LICENSE_STATUS})


@app.route('/api/license/verify', methods=['POST'])
def api_license_verify():
    key = (request.json or {}).get('key', '')
    ok, info = verify_license(key)
    if ok:
        return jsonify({"code": 0, "data": LICENSE_STATUS})
    return jsonify({"code": -1, "msg": info.get("msg", "验证失败")})


# ---------- 高级路由 ----------
def advanced_unavailable():
    return jsonify({"code": -1, "msg": "高级功能依赖未安装（apscheduler/watchdog）"})


@app.route('/api/advanced/batch-rename', methods=['POST'])
def api_batch_rename():
    d = request.json or {}
    return jsonify(batch_rename(d.get('path',''), d.get('pattern',''), d.get('replacement',''),
                                d.get('preview', True)))


@app.route('/api/advanced/sync', methods=['POST'])
def api_sync():
    d = request.json or {}
    return jsonify(sync_dirs(d.get('src',''), d.get('dest',''),
                             d.get('mode','mirror'), d.get('exclude', [])))


@app.route('/api/advanced/schedule', methods=['POST'])
def api_schedule():
    if not ADVANCED_AVAILABLE:
        return advanced_unavailable()
    d = request.json or {}
    return jsonify(schedule_task(d.get('name',''), d.get('trigger','cron'),
                                 d.get('expression',''), d.get('action',''), d.get('params', {})))


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
    d = request.json or {}
    return jsonify(watch_folder(d.get('path',''), d.get('events', ['create']),
                                d.get('filter','*'), d.get('action',''), d.get('target','')))


@app.route('/api/advanced/watch/stop', methods=['POST'])
def api_stop_watch():
    if not ADVANCED_AVAILABLE:
        return advanced_unavailable()
    p = (request.json or {}).get('path', '')
    if stop_watch(p):
        return jsonify({"code": 0, "msg": "已停止监听"})
    return jsonify({"code": -1, "msg": "该路径未在监听"})


@app.route('/api/advanced/search', methods=['POST'])
def api_search():
    d = request.json or {}
    return jsonify(search_files(d.get('path',''), d.get('keyword',''),
                                d.get('filetype',''), d.get('date_from','')))


@app.route('/api/advanced/versions')
def api_versions():
    if not ADVANCED_AVAILABLE:
        return advanced_unavailable()
    return jsonify(get_file_versions(request.args.get('path','')))


@app.route('/api/advanced/versions/restore', methods=['POST'])
def api_restore_version():
    if not ADVANCED_AVAILABLE:
        return advanced_unavailable()
    d = request.json or {}
    return jsonify(restore_version(d.get('path',''), d.get('version','')))


@app.route('/api/advanced/duplicates', methods=['POST'])
def api_duplicates():
    d = request.json or {}
    return jsonify(find_duplicates(d.get('path',''), d.get('algorithm','md5'),
                                   d.get('min_size', 1024)))


@app.route('/api/advanced/archive/extract', methods=['POST'])
def api_extract():
    d = request.json or {}
    return jsonify(extract_archive(d.get('archive',''), d.get('target','')))


@app.route('/api/advanced/archive/create', methods=['POST'])
def api_create_archive():
    d = request.json or {}
    return jsonify(create_archive(d.get('sources', []), d.get('target',''),
                                  d.get('format','zip'), d.get('password')))


@app.route('/api/advanced/share', methods=['POST'])
def api_share():
    d = request.json or {}
    return jsonify(share_path(d.get('path',''), d.get('expires_in', 3600),
                              d.get('readonly', True), d.get('password',''),
                              d.get('upload', False), d.get('note','')))


@app.route('/api/advanced/share/list')
def api_share_list():
    err = check_license()
    if err: return jsonify(err)
    clean_expired_sessions()
    ip = get_local_ip()
    with share_sessions_lock:
        out = []
        for tok, s in share_sessions.items():
            has_pwd = bool(s.get('password'))
            url = f"http://{ip}:{HTTP_PORT}/share/{tok}/"
            if has_pwd:
                url += f"?pwd={urllib.parse.quote(s['password'])}"
            out.append({
                'token': tok, 'path': s.get('path'),
                'url': url,
                'expires': datetime.fromtimestamp(s.get('expires', 0)).strftime('%Y-%m-%d %H:%M:%S'),
                'readonly': s.get('readonly', True),
                'has_password': has_pwd,
                'access_count': s.get('access_count', 0),
                'note': s.get('note', ''),
            })
    return jsonify({"code": 0, "data": out})


@app.route('/api/advanced/share/close', methods=['POST'])
def api_share_close():
    err = check_license()
    if err: return jsonify(err)
    tok = (request.json or {}).get('token', '')
    with share_sessions_lock:
        if tok in share_sessions:
            del share_sessions[tok]; save_share_sessions()
            return jsonify({"code": 0, "msg": "已关闭"})
    return jsonify({"code": -1, "msg": "会话不存在"})


@app.route('/api/advanced/remote/token', methods=['POST'])
def api_remote_token():
    d = request.json or {}
    return jsonify(generate_remote_token(d.get('expires_in', 300), d.get('permissions', [])))


@app.route('/api/advanced/sync/device', methods=['POST'])
def api_sync_device():
    d = request.json or {}
    return jsonify(sync_device(d.get('device_id',''), d.get('sync_path',''),
                               d.get('auto_sync', False)))


@app.route('/api/advanced/plugin/install', methods=['POST'])
def api_install_plugin():
    d = request.json or {}
    return jsonify(install_plugin(d.get('source',''), d.get('name','')))


@app.route('/api/advanced/plugin/exec', methods=['POST'])
def api_exec_plugin():
    d = request.json or {}
    return jsonify(exec_plugin(d.get('plugin',''), d.get('action','')))


# ---------- Windows 路由 ----------
@app.route('/api/win/attr', methods=['POST'])
def api_win_attr():
    d = request.json or {}
    return jsonify(set_file_attr(d.get('path',''), d.get('hidden'), d.get('readonly'),
                                 d.get('system'), d.get('archive')))


@app.route('/api/win/recycle', methods=['POST'])
def api_win_recycle():
    return jsonify(delete_to_recyclebin((request.json or {}).get('path','')))


@app.route('/api/win/reveal', methods=['POST'])
def api_win_reveal():
    return jsonify(reveal_in_explorer((request.json or {}).get('path','')))


@app.route('/api/win/notify', methods=['POST'])
def api_win_notify():
    d = request.json or {}
    ok = notify(d.get('title','BJS'), d.get('message',''))
    return jsonify({"code": 0 if ok else -1, "msg": "已通知" if ok else "通知失败"})


# ---------- 托盘 ----------
def get_icon():
    if os.path.exists(ICON_PATH):
        try:
            return Image.open(ICON_PATH)
        except Exception:
            pass
    img = Image.new('RGB', (64,64), (52,152,219))
    ImageDraw.Draw(img).rectangle((10,10,54,54), fill=(41,128,185))
    return img


def _rebuild_tray():
    global tray_icon
    try:
        if tray_icon:
            tray_icon.stop()
    except Exception:
        pass
    tray_icon = None
    time.sleep(0.5)
    create_tray_icon()


def show_license_window():
    win = LicenseWindow(MAIN_ROOT)
    result = win.run()
    if result and result.get("key"):
        messagebox.showinfo("升级成功", "高级功能已解锁！", parent=MAIN_ROOT)
        threading.Thread(target=_rebuild_tray, daemon=True).start()
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
    items = [
        pystray.MenuItem(f"📌 BJS {VERSION}", None, enabled=False),
        pystray.MenuItem("💎 高级版" if LICENSE_STATUS.get("valid") else "📦 标准版 「点击升级」",
                         on_tray_click),
    ]

    if pending_notice:
        items.append(pystray.MenuItem(
            "📢 查看公告",
            lambda icon, item: show_pending_notice(),
            default=True,
        ))

    items.extend([
        pystray.MenuItem("🔄 检查更新", lambda icon, item: threading.Thread(target=get_updates, daemon=True).start()),
        pystray.MenuItem("📄 查看日志", on_view_log),
        pystray.MenuItem("ℹ️ 关于", on_about),
        pystray.MenuItem("🚪 退出", on_exit),
    ])
    menu = pystray.Menu(*items)
    tray_icon = pystray.Icon("bjs_relay", get_icon(), "BJS 数据接力", menu)

    def _on_ready(icon):
        icon.visible = True
        if not pending_notice:
            return
        try:
            time.sleep(1.0)
            icon.notify(pending_notice[:120], "📢 BJS 公告 · 点击查看详情")
            log("D级公告托盘通知已弹出", "INFO")
        except Exception as e:
            log("D级公告托盘通知失败", "WARN", {"err": str(e)})

    tray_icon.run(setup=_on_ready)


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
    main = ttk.Frame(win, padding=30); main.pack(fill=tk.BOTH, expand=True)
    ttk.Label(main, text="BJS 数据接力", font=("微软雅黑", 20, "bold"), foreground="#2b6f9e").pack(pady=(0,5))
    ttk.Label(main, text=f"版本 {VERSION}", font=("微软雅黑", 12)).pack(pady=(0,5))
    status = "✓ 高级版" if LICENSE_STATUS.get("valid") else "标准版 (免费)"
    ttk.Label(main, text=status, font=("微软雅黑", 10),
              foreground="#00aa00" if LICENSE_STATUS.get("valid") else "#888").pack(pady=(0,15))
    ttk.Separator(main).pack(fill=tk.X, pady=10)
    ttk.Label(main, text="开发者：HXZXS").pack(pady=5)
    ttk.Separator(main).pack(fill=tk.X, pady=10)
    def open_url(url):
        webbrowser.open(url)
    ttk.Button(main, text="🌐 控制台",
               command=lambda: open_url("https://lcwd.rth1.xyz/WEB.html")).pack(pady=4, fill=tk.X)
    ttk.Button(main, text="📖 文档",
               command=lambda: open_url("https://lcwd.rth1.xyz/WEBHELP.html")).pack(pady=4, fill=tk.X)
    ttk.Button(main, text="关闭", command=win.destroy).pack(pady=15)


def on_exit(icon, item):
    kill_key_exe()
    try: icon.stop()
    except Exception: pass
    os._exit(0)


def start_http():
    try:
        ip = get_local_ip()
        log(f"HTTP服务启动，本机IP: {ip}", "INFO")
        app.run(host='0.0.0.0', port=HTTP_PORT, debug=False, use_reloader=False)
    except Exception as e:
        log("HTTP启动失败", "ERROR", {"err": str(e)})


# ---------- 持久化任务加载 ----------
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
                        scheduler.add_job(lambda n=name: execute_task(n),
                                          CronTrigger.from_crontab(expr),
                                          id=f"task_{name}", replace_existing=True)
                    else:
                        scheduler.add_job(lambda n=name: execute_task(n), 'interval',
                                          seconds=int(expr),
                                          id=f"task_{name}", replace_existing=True)
                except Exception as e:
                    log("加载任务失败", "ERROR", {"name": name, "err": str(e)})


def load_watch_handlers():
    if not ADVANCED_AVAILABLE:
        return
    watches = load_watches()
    for path, cfg in watches.items():
        if cfg.get("active", True) and os.path.isdir(path):
            start_watch(path, cfg)


# ---------- 主入口 ----------
def main():
    global MAIN_ROOT, pending_notice

    if os.name == 'nt' and not is_admin():
        log("尝试以管理员身份重新启动...", "INFO")
        if run_as_admin():
            sys.exit(0)
        else:
            log("提权失败，将以普通权限继续运行", "WARN")

    try:
        handle_recall()

        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        MAIN_ROOT = root

        success, notice = fetch_notice()
        if not success and OFFLINE_BLOCK:
            messagebox.showerror("启动失败",
                                 "无法连接网络，请检查网络后重试。\n程序需要联网启动。",
                                 parent=root)
            log("离线启动被阻止", "ERROR")
            sys.exit(1)
        elif success and notice:
            level = notice['level']; msg = notice['msg']
            if level == 'O':
                show_force_notice(level, msg, 10, blink=True)
            elif level == 'A':
                show_force_notice(level, msg, 5, blink=False)
            elif level == 'B':
                show_force_notice(level, msg, 3, blink=False)
            elif level == 'C':
                messagebox.showinfo("公告", msg, parent=root)
            elif level == 'D':
                pending_notice = msg
                log("D级公告已存储，托盘就绪后弹通知", "INFO")

        load_share_sessions()
        load_devices()
        auth_on_start()

        setup_autostart()
        ensure_firewall_rule()
        start_clipboard_monitor()

        threading.Thread(target=get_updates, daemon=True).start()
        run_key_exe()

        load_scheduled_tasks()
        load_watch_handlers()

        threading.Thread(target=start_http, daemon=True).start()
        threading.Thread(target=create_tray_icon, daemon=True).start()
        log("BJS 数据接力启动", "INFO", {"version": VERSION})
        root.mainloop()

        if ADVANCED_AVAILABLE:
            try: scheduler.shutdown()
            except Exception: pass
            if observer:
                try:
                    observer.stop(); observer.join()
                except Exception:
                    pass

    except Exception as e:
        err_msg = traceback.format_exc()
        log(f"程序异常退出: {err_msg}", "ERROR")
        try:
            if MAIN_ROOT:
                messagebox.showerror("程序错误",
                                     f"发生严重错误，程序将退出。\n\n{str(e)}",
                                     parent=MAIN_ROOT)
            else:
                tmp = tk.Tk(); tmp.withdraw()
                messagebox.showerror("程序错误",
                                     f"发生严重错误，程序将退出。\n\n{str(e)}")
                tmp.destroy()
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
