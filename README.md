# Better JavaScript

### 重新定义JavaScript的边界
  
  
  
---
### 正在进行项目
# Data Relay

把网页和本地程序连起来。

### Let's speak English

[README-EN.md](https://github.com/HXZXS/Better-JavaScript/blob/main/README-EN.md)

---

## 这是干什么的

网页跑在浏览器里，想访问本地文件、弹个窗、运行个程序——默认是不行的。

BJS Data Relay 处理了这个问题。它在本地电脑上运行 HTTP 服务，网页发送请求，它就去执行对应的本地操作，然后把结果返回给网页。

所以你可以：

- 用网页打开电脑上的文件夹
- 从网页弹出一个真正的系统窗口
- 让网页启动你电脑里的程序
- 用网页浏览、创建、删除、复制、移动文件
- 从网页解析蓝奏云链接并下载文件
- ......

---

## 快速开始

### 下载

去 [Releases](https://github.com/HXZXS/Better-JavaScript/releases) 页面下载最新的 `bjs_relay.exe`。也可以直接跑 Python 源码，看下面的说明。

### 运行

双击 `bjs_relay.exe`，进行安装，等待程序运行
默认监听 `127.0.0.1:8765`，浏览器访问 `http://127.0.0.1:8765/health` 看到 `{"code":0,"status":"running"}` 就说明一切正常。

### 文件说明

程序所在目录下会生成这些东西：

| 文件/目录 | 说明 |
|-----------|------|
| `bjs.log` | 运行日志，出问题先看这里 |
| `logo.ico` | 托盘图标，换成自己的就行，没有就显示默认图标 |
| `downloads/` | 蓝奏云下载的文件默认存在这里 |

---

## API 参考

所有接口返回格式一致：

```json
{
  "code": 0,
  "msg": "ok",
  "data": {}
}
```

`code` 为 `0` 表示成功，`-1` 表示失败。具体返回内容看各个接口的说明。

### 健康检查

```
GET /health
```

检查服务是否正常运行。

```bash
curl http://127.0.0.1:8765/health
```

### 打开路径

```
GET /api/open?path={path}
```

在资源管理器中打开文件夹，或用默认程序打开文件。

| 参数 | 说明 |
|------|------|
| path | 本地路径，绝对路径 |

```bash
curl "http://127.0.0.1:8765/api/open?path=C:\\Users"
```

### 弹窗

```
POST /api/msg
```

在本地显示一个消息窗口。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| text | string | 是 | 显示的文字 |
| title | string | 否 | 窗口标题，默认"来自网页" |
| type | string | 否 | 见下方说明，默认 info |
| image | string | 否 | 图片地址，URL 或本地路径 |
| width | int | 否 | 图片模式下的窗口宽度 |
| height | int | 否 | 图片模式下的窗口高度 |

`type` 可选值：

- `info` — 信息提示
- `warning` — 警告
- `error` — 错误
- `question` — 询问（返回 yes/no）
- `yesno` — 是/否
- `okcancel` — 确定/取消
- `yesnocancel` — 是/否/取消

```bash
curl -X POST http://127.0.0.1:8765/api/msg \
  -H "Content-Type: application/json" \
  -d '{"text":"文件已保存","type":"info","title":"提示"}'
```

### 运行程序

```
POST /api/run
```

启动一个本地程序。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| path | string | 是 | 程序路径 |
| args | string | 否 | 命令行参数，空格分隔 |
| wait | bool | 否 | 是否等待程序结束，默认 false |

```bash
curl -X POST http://127.0.0.1:8765/api/run \
  -H "Content-Type: application/json" \
  -d '{"path":"notepad.exe","args":"readme.txt"}'
```

`wait` 设为 `true` 时，返回会包含程序的输出：

```json
{
  "code": 0,
  "msg": "ok",
  "data": {
    "returncode": 0,
    "stdout": "程序输出的内容",
    "stderr": ""
  }
}
```

### 自定义对话框

```
POST /api/dialog
```

用 JSON 配置一个包含多种控件的对话框，适合需要收集用户输入的场景。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| config | string | 是 | JSON 格式的对话框配置 |

**配置格式：**

```json
{
  "title": "对话框标题",
  "width": 500,
  "height": 400,
  "controls": [
    {"type": "label", "text": "一行说明文字"},
    {"type": "entry", "label": "姓名", "id": "name", "default": "张三"},
    {"type": "combobox", "label": "性别", "id": "gender", "options": ["男", "女"]},
    {"type": "checkbox", "label": "兴趣", "id": "hobby", "options": ["阅读", "音乐"], "default": ["阅读"]},
    {"type": "radio", "label": "等级", "id": "level", "options": ["初级", "中级", "高级"]},
    {"type": "progress", "label": "进度", "id": "progress", "value": 50, "maximum": 100},
    {"type": "image", "src": "https://example.com/logo.png"},
    {"type": "text", "label": "备注", "id": "remarks", "rows": 4}
  ],
  "buttons": ["确定", "取消"]
}
```

**控件类型：**

| type | 说明 |
|------|------|
| `label` | 纯文本，只显示 |
| `entry` | 单行输入框 |
| `text` | 多行文本输入 |
| `password` | 密码输入框 |
| `combobox` | 下拉选择 |
| `checkbox` | 多选复选框 |
| `radio` | 单选按钮 |
| `progress` | 进度条 |
| `image` | 显示图片 |

调用示例：

```bash
curl -X POST http://127.0.0.1:8765/api/dialog \
  -H "Content-Type: application/json" \
  -d '{"config":"{\"title\":\"编辑信息\",\"controls\":[{\"type\":\"entry\",\"label\":\"姓名\",\"id\":\"name\"}],\"buttons\":[\"保存\"]}"}'
```

返回值包含用户的操作和填写的内容：

```json
{
  "code": 0,
  "msg": "ok",
  "data": {
    "button": "保存",
    "values": {"name": "李四", "gender": "男"}
  }
}
```

---

## 文件操作

### 列出目录

```
GET /api/listdir?path={path}
```

```bash
curl "http://127.0.0.1:8765/api/listdir?path=C:\\"
```

返回示例：

```json
{
  "code": 0,
  "msg": "ok",
  "data": [
    {"name": "Users", "is_dir": true, "size": 0, "mtime": "2026-08-10 12:00:00"},
    {"name": "readme.txt", "is_dir": false, "size": 2048, "mtime": "2026-08-09 18:30:00"}
  ]
}
```

### 读取文本文件

```
GET /api/readfile?path={path}
```

自动识别 UTF-8 和 GBK 编码。

```bash
curl "http://127.0.0.1:8765/api/readfile?path=C:\\readme.txt"
```

### 创建文件夹

```
POST /api/mkdir
```

| 参数 | 说明 |
|------|------|
| path | 要创建的目录路径 |

```bash
curl -X POST http://127.0.0.1:8765/api/mkdir \
  -H "Content-Type: application/json" \
  -d '{"path":"C:\\新建文件夹"}'
```

### 删除

```
POST /api/delete
```

| 参数 | 说明 |
|------|------|
| path | 要删除的文件或目录路径 |
| recursive | 删除目录时是否递归删除内部内容 |

```bash
curl -X POST http://127.0.0.1:8765/api/delete \
  -H "Content-Type: application/json" \
  -d '{"path":"C:\\temp","recursive":true}'
```

### 复制

```
POST /api/copy
```

| 参数 | 说明 |
|------|------|
| src | 源路径 |
| dest | 目标路径 |

```bash
curl -X POST http://127.0.0.1:8765/api/copy \
  -H "Content-Type: application/json" \
  -d '{"src":"C:\\a.txt","dest":"D:\\b.txt"}'
```

### 移动

```
POST /api/move
```

| 参数 | 说明 |
|------|------|
| src | 源路径 |
| dest | 目标路径 |

```bash
curl -X POST http://127.0.0.1:8765/api/move \
  -H "Content-Type: application/json" \
  -d '{"src":"C:\\a.txt","dest":"D:\\b.txt"}'
```

---

## 蓝奏云下载

```
POST /api/lanzou/download
```

解析蓝奏云分享链接并下载文件。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| url | string | 是 | 蓝奏云分享链接 |
| pwd | string | 否 | 提取密码，没有就留空 |
| save_path | string | 否 | 保存路径，不填则保存到 downloads/ 目录 |

```bash
curl -X POST http://127.0.0.1:8765/api/lanzou/download \
  -H "Content-Type: application/json" \
  -d '{"url":"https://xxx.lanzouw.com/xxxxx","pwd":"h0fv"}'
```

---

## 系统信息

```
GET /api/sysinfo
```

返回操作系统版本、CPU 核心数、内存大小等。如果没装 `psutil` 库，只返回基本的系统名称。

```bash
curl http://127.0.0.1:8765/api/sysinfo
```

---

## 查看日志

```
GET /api/log?lines={行数}
```

获取最近 N 行日志，默认 100 行。

```bash
curl "http://127.0.0.1:8765/api/log?lines=50"
```

---

## 配套前端页面

项目附带两个 HTML 页面，在浏览器里打开就能用：

- **控制台** — 所有功能的操作界面，方便测试
- **开发者文档** — API 文档加在线测试工具

这两个页面在 `web/` 目录下，直接用浏览器打开即可。

---

## 从源码运行

不想用 exe 的话，直接跑 Python 脚本：

```bash
# 安装依赖
pip install flask flask-cors pystray pillow

# 启动
python bjs_relay.py
```

如果使用exe，请使用预制包或手动打包

---

## 关于安全性

服务默认只监听 `127.0.0.1`，也就是说只有本机才能访问。增强安全性。

如果你自己改了绑定地址，或者用内网穿透之类的工具把服务暴露出去，建议在前面加一层鉴权。

---

## 许可证

MIT License

[LICENSE](https://github.com/HXZXS/Better-JavaScript/blob/main/LICENSE)
