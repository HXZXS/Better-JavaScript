# BJS 数据接力
# 版本 6.0.α
# 开发者 HXZXS

import sys
import os
import json
import time
import shutil
import subprocess
import urllib.parse
import urllib.request
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime
import traceback
import pystray
from PIL import Image, ImageDraw, ImageTk
from flask import Flask, request, jsonify
from flask_cors import CORS
import webbrowser

# 基础路径 - 使用程序所在目录
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
LOG_PATH = os.path.join(BASE_DIR, "bjs.log")
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
ICON_PATH = os.path.join(BASE_DIR, "logo.ico")  # 优先ico，若不存在则尝试png
if not os.path.exists(ICON_PATH):
    ICON_PATH = os.path.join(BASE_DIR, "logo.png")

# 确保必要目录存在
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

HTTP_PORT = 8765
MAIN_ROOT = None   # tkinter根窗口，用于弹窗

# 日志函数
def log(msg, level="INFO", extra=None):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if extra:
        extra_str = json.dumps(extra, ensure_ascii=False)
        line = f"[{ts}] {level}: {msg} | {extra_str}"
    else:
        line = f"[{ts}] {level}: {msg}"
    print(line)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except:
        pass

# 安全路径检查（防穿越）
def safe_path(path):
    if not path:
        return False
    norm = os.path.normpath(path)
    if '..' in norm or '~' in norm:
        return False
    # 禁止访问系统核心目录
    forbidden = ['C:\\Windows', 'C:\\System32', 'C:\\Program Files', 'C:\\ProgramData']
    if os.path.isabs(path):
        for f in forbidden:
            if norm.lower().startswith(f.lower()):
                return False
        return True
    # 相对路径转为绝对路径后检查.. 
    abs_path = os.path.abspath(path)
    if '..' in abs_path:
        return False
    return True

# 加载图片（URL或本地）
def load_pic(src, max_size=(800,600)):
    try:
        if src.startswith(('http://','https://')):
            with urllib.request.urlopen(src, timeout=10) as r:
                data = r.read()
            import io
            img = Image.open(io.BytesIO(data))
        else:
            img = Image.open(src)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        return photo, img.size
    except Exception as e:
        log("图片加载失败", "ERROR", {"src": src, "err": str(e)})
        return None, (0,0)

# = 自定义对话框 =
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
        w = self.cfg.get('width', 0)
        h = self.cfg.get('height', 0)
        controls = self.cfg.get('controls', [])
        buttons = self.cfg.get('buttons', ['确定'])

        self.window = tk.Toplevel(self.master)
        self.window.title(title)
        if w>0 and h>0:
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
                    photo, size = load_pic(src)
                    if photo:
                        img_label = ttk.Label(main, image=photo)
                        img_label.image = photo
                        img_label.grid(row=row, column=0, columnspan=2, pady=5)
                        row += 1
                    else:
                        ttk.Label(main, text=f"图片加载失败: {src}").grid(row=row, column=0, columnspan=2, pady=2)
                        row += 1
                else:
                    ttk.Label(main, text="未指定图片").grid(row=row, column=0, columnspan=2, pady=2)
                    row += 1
            elif ctype == 'entry':
                if label:
                    ttk.Label(main, text=label).grid(row=row, column=0, sticky='e', padx=5)
                var = tk.StringVar(value=default)
                entry = ttk.Entry(main, textvariable=var, width=30)
                entry.grid(row=row, column=1, sticky='w', pady=2)
                self.vars[cid] = var
                row += 1
            elif ctype == 'text':
                if label:
                    ttk.Label(main, text=label).grid(row=row, column=0, sticky='ne', padx=5)
                text_w = scrolledtext.ScrolledText(main, height=ctrl.get('rows',5), width=40)
                text_w.insert('1.0', default)
                text_w.grid(row=row, column=1, sticky='w', pady=2)
                self.vars[cid] = text_w
                row += 1
            elif ctype == 'password':
                if label:
                    ttk.Label(main, text=label).grid(row=row, column=0, sticky='e', padx=5)
                var = tk.StringVar(value=default)
                entry = ttk.Entry(main, textvariable=var, show='*', width=30)
                entry.grid(row=row, column=1, sticky='w', pady=2)
                self.vars[cid] = var
                row += 1
            elif ctype == 'combobox':
                if label:
                    ttk.Label(main, text=label).grid(row=row, column=0, sticky='e', padx=5)
                var = tk.StringVar(value=default if default in options else (options[0] if options else ''))
                combo = ttk.Combobox(main, textvariable=var, values=options, state='readonly', width=28)
                combo.grid(row=row, column=1, sticky='w', pady=2)
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
                    cb = ttk.Checkbutton(frm, text=opt, variable=var)
                    cb.pack(anchor='w')
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
                    rb = ttk.Radiobutton(frm, text=opt, variable=var, value=opt)
                    rb.pack(anchor='w')
                self.vars[cid] = var
                row += 1
            elif ctype == 'progress':
                if label:
                    ttk.Label(main, text=label).grid(row=row, column=0, sticky='e', padx=5)
                var = tk.IntVar(value=ctrl.get('value',0))
                maxv = ctrl.get('maximum',100)
                prog = ttk.Progressbar(main, variable=var, maximum=maxv, length=250)
                prog.grid(row=row, column=1, sticky='w', pady=2)
                self.vars[cid] = var
                row += 1
            else:
                ttk.Label(main, text=f"未知控件: {ctype}").grid(row=row, column=0, columnspan=2, pady=2)
                row += 1

        # 按钮
        btn_frame = ttk.Frame(self.window)
        btn_frame.pack(pady=10)
        for bt in buttons:
            btn = ttk.Button(btn_frame, text=bt, command=lambda b=bt: self.on_button(b))
            btn.pack(side=tk.LEFT, padx=5)

    def on_button(self, bt):
        # 收集数据
        data = {}
        for cid, val in self.vars.items():
            if isinstance(val, tk.StringVar):
                data[cid] = val.get()
            elif isinstance(val, tk.IntVar):
                data[cid] = val.get()
            elif isinstance(val, tk.BooleanVar):
                data[cid] = val.get()
            elif isinstance(val, list):  # checkbox
                data[cid] = [opt for opt, var in val if var.get()]
            elif isinstance(val, tk.Text):
                data[cid] = val.get('1.0', 'end-1c')
            else:
                data[cid] = str(val)
        self.result = {'button': bt, 'values': data}
        self.window.destroy()

    def run(self):
        self.window.wait_window()
        return self.result

def show_dialog(cfg):
    try:
        if isinstance(cfg, str):
            cfg = json.loads(cfg)
        dlg = DialogBox(MAIN_ROOT, cfg)
        res = dlg.run()
        log("对话框结果", "INFO", res)
        return res
    except Exception as e:
        log("对话框异常", "ERROR", {"err": str(e), "trace": traceback.format_exc()})
        # 用置顶消息框显示错误
        top = tk.Toplevel(MAIN_ROOT)
        top.attributes('-topmost', True)
        top.withdraw()
        messagebox.showerror("对话框错误", f"无法显示对话框：{e}", parent=top)
        top.destroy()
        return None

# = 基础功能 =
def open_path(path):
    log("打开路径请求", "INFO", {"path": path})
    if not path:
        return {"code": -1, "msg": "路径为空"}
    if not safe_path(path):
        return {"code": -1, "msg": "非法路径"}
    if not os.path.exists(path):
        return {"code": -1, "msg": f"路径不存在: {path}"}
    try:
        os.startfile(path) if os.name == 'nt' else subprocess.Popen(['open', path])
        log("路径已打开", "INFO", {"path": path})
        return {"code": 0, "msg": "ok", "data": {"path": path}}
    except Exception as e:
        log("打开失败", "ERROR", {"path": path, "err": str(e)})
        return {"code": -1, "msg": str(e)}

def run_prog(path, args=None, wait=False):
    log("运行程序", "INFO", {"path": path, "args": args, "wait": wait})
    if not path:
        return {"code": -1, "msg": "程序路径为空"}
    if not safe_path(path):
        return {"code": -1, "msg": "非法路径"}
    if not os.path.exists(path):
        return {"code": -1, "msg": f"程序不存在: {path}"}
    cmd = [path]
    if args:
        cmd.extend(args.split())
    try:
        if wait:
            p = subprocess.run(cmd, shell=False, capture_output=True, text=True, timeout=300)
            log("程序运行结束", "INFO", {"returncode": p.returncode})
            return {"code": 0, "msg": "ok", "data": {"returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}}
        else:
            subprocess.Popen(cmd, shell=False)
            log("程序已启动（不等待）", "INFO")
            return {"code": 0, "msg": "程序已启动", "data": {"cmd": " ".join(cmd)}}
    except subprocess.TimeoutExpired:
        log("程序超时", "ERROR", {"cmd": " ".join(cmd)})
        return {"code": -1, "msg": "程序运行超时"}
    except Exception as e:
        log("运行失败", "ERROR", {"cmd": " ".join(cmd), "err": str(e)})
        return {"code": -1, "msg": str(e)}

def show_msg(text, typ="info", title="来自网页", image=None, w=0, h=0):
    log("弹窗请求", "INFO", {"text": text[:50], "type": typ, "title": title, "image": image})
    try:
        if image:
            cfg = {
                'title': title,
                'width': w or 500,
                'height': h or 400,
                'controls': [{'type': 'image', 'src': image}, {'type': 'label', 'text': text}],
                'buttons': ['确定']
            }
            return show_dialog(cfg)
        # 标准弹窗需置顶
        top = tk.Toplevel(MAIN_ROOT)
        top.attributes('-topmost', True)
        top.withdraw()
        if typ == "info":
            messagebox.showinfo(title, text, parent=top)
            return {"code": 0}
        elif typ == "warning":
            messagebox.showwarning(title, text, parent=top)
            return {"code": 0}
        elif typ == "error":
            messagebox.showerror(title, text, parent=top)
            return {"code": 0}
        elif typ == "question":
            res = messagebox.askquestion(title, text, parent=top)
            log("用户选择", "INFO", {"result": res})
            return {"code": 0, "data": res}
        elif typ == "yesno":
            res = messagebox.askyesno(title, text, parent=top)
            log("用户选择", "INFO", {"result": res})
            return {"code": 0, "data": res}
        elif typ == "okcancel":
            res = messagebox.askokcancel(title, text, parent=top)
            log("用户选择", "INFO", {"result": res})
            return {"code": 0, "data": res}
        elif typ == "yesnocancel":
            res = messagebox.askyesnocancel(title, text, parent=top)
            log("用户选择", "INFO", {"result": res})
            return {"code": 0, "data": res}
        else:
            messagebox.showinfo(title, text, parent=top)
            return {"code": 0}
        top.destroy()
    except Exception as e:
        log("弹窗异常", "ERROR", {"err": str(e)})
        return {"code": -1, "msg": str(e)}

# = 文件操作 =
def list_dir(path):
    if not path:
        return {"code": -1, "msg": "路径为空"}
    if not safe_path(path):
        return {"code": -1, "msg": "非法路径"}
    if not os.path.exists(path):
        return {"code": -1, "msg": f"路径不存在: {path}"}
    if not os.path.isdir(path):
        return {"code": -1, "msg": "不是目录"}
    try:
        items = []
        for name in os.listdir(path):
            full = os.path.join(path, name)
            is_dir = os.path.isdir(full)
            st = os.stat(full)
            items.append({
                "name": name,
                "is_dir": is_dir,
                "size": st.st_size if not is_dir else 0,
                "mtime": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })
        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        log("列出目录", "INFO", {"path": path, "count": len(items)})
        return {"code": 0, "msg": "ok", "data": items}
    except Exception as e:
        log("列出目录失败", "ERROR", {"path": path, "err": str(e)})
        return {"code": -1, "msg": str(e)}

def read_file(path):
    if not path:
        return {"code": -1, "msg": "路径为空"}
    if not safe_path(path):
        return {"code": -1, "msg": "非法路径"}
    if not os.path.exists(path):
        return {"code": -1, "msg": f"文件不存在: {path}"}
    if os.path.isdir(path):
        return {"code": -1, "msg": "不能读取目录"}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        log("读取文件", "INFO", {"path": path, "size": len(content)})
        return {"code": 0, "msg": "ok", "data": content}
    except UnicodeDecodeError:
        try:
            with open(path, 'r', encoding='gbk') as f:
                content = f.read()
            log("读取文件(GBK)", "INFO", {"path": path})
            return {"code": 0, "msg": "ok", "data": content}
        except Exception as e:
            log("读取文件失败", "ERROR", {"path": path, "err": str(e)})
            return {"code": -1, "msg": f"无法解码: {str(e)}"}
    except Exception as e:
        log("读取文件失败", "ERROR", {"path": path, "err": str(e)})
        return {"code": -1, "msg": str(e)}

def mkdir(path):
    if not path:
        return {"code": -1, "msg": "路径为空"}
    if not safe_path(path):
        return {"code": -1, "msg": "非法路径"}
    if os.path.exists(path):
        return {"code": -1, "msg": "目标已存在"}
    try:
        os.makedirs(path)
        log("创建文件夹", "INFO", {"path": path})
        return {"code": 0, "msg": "ok", "data": {"path": path}}
    except Exception as e:
        log("创建失败", "ERROR", {"path": path, "err": str(e)})
        return {"code": -1, "msg": str(e)}

def delete_path(path, recursive=False):
    if not path:
        return {"code": -1, "msg": "路径为空"}
    if not safe_path(path):
        return {"code": -1, "msg": "非法路径"}
    if not os.path.exists(path):
        return {"code": -1, "msg": "目标不存在"}
    try:
        if os.path.isdir(path):
            if recursive:
                shutil.rmtree(path)
            else:
                os.rmdir(path)
        else:
            os.remove(path)
        log("删除成功", "INFO", {"path": path, "recursive": recursive})
        return {"code": 0, "msg": "ok", "data": {"path": path}}
    except Exception as e:
        log("删除失败", "ERROR", {"path": path, "err": str(e)})
        return {"code": -1, "msg": str(e)}

def copy_path(src, dst):
    if not src or not dst:
        return {"code": -1, "msg": "源或目标为空"}
    if not safe_path(src) or not safe_path(dst):
        return {"code": -1, "msg": "非法路径"}
    if not os.path.exists(src):
        return {"code": -1, "msg": f"源不存在: {src}"}
    try:
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
        log("复制成功", "INFO", {"src": src, "dst": dst})
        return {"code": 0, "msg": "ok", "data": {"src": src, "dst": dst}}
    except Exception as e:
        log("复制失败", "ERROR", {"src": src, "dst": dst, "err": str(e)})
        return {"code": -1, "msg": str(e)}

def move_path(src, dst):
    if not src or not dst:
        return {"code": -1, "msg": "源或目标为空"}
    if not safe_path(src) or not safe_path(dst):
        return {"code": -1, "msg": "非法路径"}
    if not os.path.exists(src):
        return {"code": -1, "msg": f"源不存在: {src}"}
    try:
        shutil.move(src, dst)
        log("移动成功", "INFO", {"src": src, "dst": dst})
        return {"code": 0, "msg": "ok", "data": {"src": src, "dst": dst}}
    except Exception as e:
        log("移动失败", "ERROR", {"src": src, "dst": dst, "err": str(e)})
        return {"code": -1, "msg": str(e)}

def get_log(lines=100):
    try:
        if not os.path.exists(LOG_PATH):
            return {"code": 0, "data": "日志文件尚未生成。"}
        with open(LOG_PATH, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        tail = all_lines[-lines:] if len(all_lines) >= lines else all_lines
        return {"code": 0, "data": ''.join(tail)}
    except Exception as e:
        return {"code": -1, "msg": str(e)}

# = 蓝奏云下载 =
def lanzou_dl(url, pwd='', save_path=''):
    log("蓝奏云解析", "INFO", {"url": url, "pwd": pwd or "无"})
    try:
        api = f"https://api.bugpk.com/api/lanzou?url={urllib.parse.quote(url)}"
        if pwd:
            api += f"&pwd={urllib.parse.quote(pwd)}"
        req = urllib.request.Request(api, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode('utf-8'))
        if data.get('code') != 200:
            return False, None, None, f"解析失败: {data.get('msg', '未知错误')}"
        real_url = data['data'].get('url')
        api_name = data['data'].get('name', '')
        if not real_url:
            return False, None, None, "未获取到下载链接"
        # 提取真实文件名
        filename = None
        parsed = urllib.parse.urlparse(real_url)
        qs = urllib.parse.parse_qs(parsed.query)
        if 'fileName' in qs:
            filename = qs['fileName'][0]
        elif 'filename' in qs:
            filename = qs['filename'][0]
        if not filename:
            filename = api_name
        if not filename:
            filename = os.path.basename(parsed.path) or 'downloaded_file'

        log("蓝奏云解析成功", "INFO", {"filename": filename})
        # 保存路径
        if not save_path:
            save_path = os.path.join(DOWNLOAD_DIR, filename)
        else:
            if os.path.isdir(save_path) or (not os.path.exists(save_path) and '.' not in os.path.basename(save_path)):
                save_path = os.path.join(save_path, filename)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        # 下载
        req = urllib.request.Request(real_url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        with urllib.request.urlopen(req, timeout=60) as r:
            with open(save_path, 'wb') as f:
                f.write(r.read())
        log("蓝奏云下载完成", "INFO", {"save_path": save_path})
        return True, filename, save_path, None
    except Exception as e:
        log("蓝奏云异常", "ERROR", {"err": str(e)})
        return False, None, None, str(e)

# = Flask API =
app = Flask(__name__)
CORS(app)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"code": 0, "status": "running", "port": HTTP_PORT})

@app.route('/api/open', methods=['GET'])
def api_open():
    path = request.args.get('path', '')
    return jsonify(open_path(path))

@app.route('/api/msg', methods=['POST'])
def api_msg():
    data = request.json or {}
    text = data.get('text', '')
    typ = data.get('type', 'info')
    title = data.get('title', '来自网页')
    image = data.get('image', '')
    w = data.get('width', 0)
    h = data.get('height', 0)
    if not text:
        return jsonify({"code": -1, "msg": "缺少 text"})
    res = show_msg(text, typ, title, image, w, h)
    return jsonify({"code": 0, "msg": "ok", "data": res})

@app.route('/api/run', methods=['POST'])
def api_run():
    data = request.json or {}
    path = data.get('path', '')
    args = data.get('args', '')
    wait = data.get('wait', False)
    if not path:
        return jsonify({"code": -1, "msg": "缺少 path"})
    return jsonify(run_prog(path, args, wait))

@app.route('/api/dialog', methods=['POST'])
def api_dialog():
    data = request.json or {}
    cfg = data.get('config', '')
    if not cfg:
        return jsonify({"code": -1, "msg": "缺少 config"})
    res = show_dialog(cfg)
    return jsonify({"code": 0, "msg": "ok", "data": res})

@app.route('/api/listdir', methods=['GET'])
def api_listdir():
    path = request.args.get('path', '')
    if not path:
        path = os.path.expanduser("~")
    return jsonify(list_dir(path))

@app.route('/api/readfile', methods=['GET'])
def api_readfile():
    path = request.args.get('path', '')
    if not path:
        return jsonify({"code": -1, "msg": "缺少 path"})
    return jsonify(read_file(path))

@app.route('/api/mkdir', methods=['POST'])
def api_mkdir():
    data = request.json or {}
    path = data.get('path', '')
    if not path:
        return jsonify({"code": -1, "msg": "缺少 path"})
    return jsonify(mkdir(path))

@app.route('/api/delete', methods=['POST'])
def api_delete():
    data = request.json or {}
    path = data.get('path', '')
    rec = data.get('recursive', False)
    if not path:
        return jsonify({"code": -1, "msg": "缺少 path"})
    return jsonify(delete_path(path, rec))

@app.route('/api/copy', methods=['POST'])
def api_copy():
    data = request.json or {}
    src = data.get('src', '')
    dst = data.get('dest', '')
    if not src or not dst:
        return jsonify({"code": -1, "msg": "缺少 src 或 dest"})
    return jsonify(copy_path(src, dst))

@app.route('/api/move', methods=['POST'])
def api_move():
    data = request.json or {}
    src = data.get('src', '')
    dst = data.get('dest', '')
    if not src or not dst:
        return jsonify({"code": -1, "msg": "缺少 src 或 dest"})
    return jsonify(move_path(src, dst))

@app.route('/api/log', methods=['GET'])
def api_log():
    lines = request.args.get('lines', 100, type=int)
    return jsonify(get_log(lines))

@app.route('/api/lanzou/download', methods=['POST'])
def api_lanzou():
    data = request.json or {}
    url = data.get('url', '')
    pwd = data.get('pwd', '')
    save_path = data.get('save_path', '')
    if not url:
        return jsonify({"code": -1, "msg": "缺少 url"})
    ok, name, final, err = lanzou_dl(url, pwd, save_path)
    if ok:
        return jsonify({"code": 0, "msg": "下载成功", "data": {"filename": name, "save_path": final}})
    else:
        return jsonify({"code": -1, "msg": err})

@app.route('/api/sysinfo', methods=['GET'])
def sysinfo():
    import platform
    try:
        import psutil
        data = {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "disk_usage": psutil.disk_usage('/')._asdict()
        }
    except:
        data = {"system": platform.system(), "release": platform.release()}
    return jsonify({"code": 0, "msg": "ok", "data": data})

# = 托盘 =
def get_icon():
    if os.path.exists(ICON_PATH):
        try:
            return Image.open(ICON_PATH)
        except:
            pass
    # 默认生成
    img = Image.new('RGB', (64,64), (52,152,219))
    draw = ImageDraw.Draw(img)
    draw.rectangle((10,10,54,54), fill=(41,128,185))
    return img

def on_view_log(icon, item):
    if os.path.exists(LOG_PATH):
        os.startfile(LOG_PATH)
    else:
        top = tk.Toplevel(MAIN_ROOT)
        top.attributes('-topmost', True)
        top.withdraw()
        messagebox.showinfo("提示", "日志文件尚未生成。", parent=top)
        top.destroy()

def on_about(icon, item):
    about_win = tk.Toplevel(MAIN_ROOT)
    about_win.title("关于 BJS 数据接力")
    about_win.geometry("420x380")
    about_win.resizable(False, False)
    about_win.attributes('-topmost', True)
    # 居中
    about_win.update_idletasks()
    w = about_win.winfo_width(); h = about_win.winfo_height()
    x = (about_win.winfo_screenwidth() - w)//2
    y = (about_win.winfo_screenheight() - h)//2
    about_win.geometry(f"{w}x{h}+{x}+{y}")
    main = ttk.Frame(about_win, padding=30)
    main.pack(fill=tk.BOTH, expand=True)
    ttk.Label(main, text="BJS 数据接力", font=("微软雅黑", 20, "bold"), foreground="#2b6f9e").pack(pady=(0,5))
    ttk.Label(main, text="版本 6.0.α", font=("微软雅黑", 12), foreground="#6a8aa8").pack(pady=(0,15))
    ttk.Separator(main, orient='horizontal').pack(fill=tk.X, pady=10)
    ttk.Label(main, text="开发者：HXZXS", font=("微软雅黑", 12)).pack(pady=5)
    ttk.Separator(main, orient='horizontal').pack(fill=tk.X, pady=10)
    btn_frame = ttk.Frame(main)
    btn_frame.pack(pady=10)
    def open_url(url):
        try:
            webbrowser.open(url)
        except:
            pass
    ttk.Button(btn_frame, text="🌐 控制台", command=lambda: open_url("https://lcwd.rth1.xyz/WEB.html")).pack(pady=4, fill=tk.X)
    ttk.Button(btn_frame, text="📖 开发文档", command=lambda: open_url("https://lcwd.rth1.xyz/WEBHELP.html")).pack(pady=4, fill=tk.X)
    ttk.Button(main, text="关闭", command=about_win.destroy).pack(pady=15)

def on_exit(icon, item):
    icon.stop()
    os._exit(0)

def tray_loop():
    icon = pystray.Icon("bjs_relay", get_icon(), "BJS 数据接力",
                        menu=pystray.Menu(
                            pystray.MenuItem("📄 查看日志", on_view_log),
                            pystray.MenuItem("ℹ️ 关于", on_about),
                            pystray.MenuItem("🚪 退出", on_exit)
                        ))
    icon.run()

# = 启动HTTP服务 =
def start_http():
    try:
        log("HTTP服务启动", "INFO", {"port": HTTP_PORT})
        app.run(host='127.0.0.1', port=HTTP_PORT, debug=False, use_reloader=False)
    except Exception as e:
        log("HTTP服务启动失败", "ERROR", {"err": str(e)})

# = 主入口 =
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    MAIN_ROOT = root
    threading.Thread(target=start_http, daemon=True).start()
    threading.Thread(target=tray_loop, daemon=True).start()
    log("BJS 数据接力已启动", "INFO", {"base_dir": BASE_DIR, "http_port": HTTP_PORT})
    root.mainloop()
