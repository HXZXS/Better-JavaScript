# Better JavaScript
### HXZXS
### 正在进行项目
# Data Relay

把网页和本地程序连起来。
<img width="570" height="274" alt="BJS" src="https://github.com/user-attachments/assets/e0260433-7be8-442a-b2c6-a2ec6d33778e" />

### Let's speak English

[README-EN.md](https://github.com/HXZXS/Better-JavaScript/blob/main/README-EN.md)

---

## 关于卡密
本项目长期开源

访问
[https://bjs.rth1.xyz/](https://bjs.rth1.xyz/key.html)

**无偿**获取开发者卡密（需在本地安装此产品）

## 这是干什么的

网页跑在浏览器里，想访问本地文件、运行本地程序——默认是不行的。

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

### 权限
> [!IMPORTANT]
> <img width="290" height="133" alt="image" src="https://github.com/user-attachments/assets/cfc0d48d-275a-435b-813a-a0f5b888a33f" />

请授予必要的运行权限

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
| `data/` | 存放卡密缓存、任务配置、版本历史等，位于 `%APPDATA%\BJS`（Windows）或 `~/.config/bjs`（Linux） |

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

> [!NOTE]
> 为确保安全性
> 发行版会屏蔽部分目录
>
> 此栏目仍在优化

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
> [!IMPORTANT]
> API服务来自第三方接口
> 
> 与此项目无关
> 
> 感谢
> [https://api.bugpk.com/](https://api.bugpk.com/doc-lanzou.html)
> 提供解析服务
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

## 高级功能（需卡密激活）

高级功能需要有效的卡密。卡密获取方式见本文开头“关于卡密”部分。验证后即可使用以下所有接口。

### 批量重命名

```
POST /api/advanced/batch-rename
```

用正则表达式批量修改文件名。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| path | string | 是 | 目录路径 |
| pattern | string | 是 | 正则表达式 |
| replacement | string | 是 | 替换内容 |
| preview | bool | 否 | 是否只预览不实际改名，默认 true |

```bash
curl -X POST http://127.0.0.1:8765/api/advanced/batch-rename \
  -H "Content-Type: application/json" \
  -d '{"path":"C:\\photos","pattern":"IMG_(\\d+)","replacement":"photo_$1","preview":true}'
```

返回示例（预览模式）：
```json
{
  "code": 0,
  "data": {
    "preview": true,
    "results": [
      {"old": "IMG_001.jpg", "new": "photo_001.jpg", "will_change": true}
    ]
  }
}
```

### 目录同步

```
POST /api/advanced/sync
```

将源目录的内容同步到目标目录，支持镜像、合并、更新三种模式。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| src | string | 是 | 源目录 |
| dest | string | 是 | 目标目录 |
| mode | string | 否 | 模式：`mirror`（镜像，目标多余文件会被删除）、`merge`（合并，只新增不删除）、`update`（只更新已有文件），默认 mirror |
| exclude | array | 否 | 排除的后缀列表，如 `[".tmp", ".log"]` |

```bash
curl -X POST http://127.0.0.1:8765/api/advanced/sync \
  -H "Content-Type: application/json" \
  -d '{"src":"C:\\work","dest":"E:\\backup","mode":"mirror","exclude":[".tmp"]}'
```

### 定时任务

```
POST /api/advanced/schedule
```

添加一个定时任务，按 cron 表达式或固定间隔执行动作。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 任务名称，唯一 |
| trigger | string | 是 | `cron` 或 `interval` |
| expression | string | 是 | cron 表达式或间隔秒数 |
| action | string | 是 | 目前支持 `sync`（目录同步） |
| params | object | 否 | 动作参数，如 `{"src":"C:\\data","dest":"E:\\backup"}` |

```bash
curl -X POST http://127.0.0.1:8765/api/advanced/schedule \
  -H "Content-Type: application/json" \
  -d '{"name":"dailybackup","trigger":"cron","expression":"0 2 * * *","action":"sync","params":{"src":"C:\\data","dest":"E:\\backup"}}'
```

### 剪贴板历史

```
GET /api/advanced/clipboard/history?limit={条数}
```

获取剪贴板最近保存的内容（最多 100 条）。

```bash
curl "http://127.0.0.1:8765/api/advanced/clipboard/history?limit=10"
```

恢复指定索引的内容：
```
POST /api/advanced/clipboard/restore
```
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| index | int | 是 | 历史记录中的索引（0 开始） |

```bash
curl -X POST http://127.0.0.1:8765/api/advanced/clipboard/restore \
  -H "Content-Type: application/json" \
  -d '{"index":0}'
```

### 文件监听

```
POST /api/advanced/watch
```

监听一个目录，当文件被创建或修改时自动执行动作（移动或复制）。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| path | string | 是 | 要监听的目录 |
| events | array | 否 | 事件列表，如 `["create","modify"]`，默认 `["create"]` |
| filter | string | 否 | 只处理指定扩展名的文件，如 `".pdf"`，默认 `*` |
| action | string | 是 | `move` 或 `copy` |
| target | string | 是 | 目标目录 |

```bash
curl -X POST http://127.0.0.1:8765/api/advanced/watch \
  -H "Content-Type: application/json" \
  -d '{"path":"C:\\incoming","action":"move","target":"C:\\archive","filter":".pdf"}'
```

停止监听：
```
POST /api/advanced/watch/stop
```
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| path | string | 是 | 要停止监听的目录 |

### 全文搜索

```
POST /api/advanced/search
```

在目录中按文件名或内容搜索关键词。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| path | string | 是 | 搜索根目录 |
| keyword | string | 是 | 关键词 |
| filetype | string | 否 | 扩展名过滤，如 `"docx,pdf"` |

```bash
curl -X POST http://127.0.0.1:8765/api/advanced/search \
  -H "Content-Type: application/json" \
  -d '{"path":"C:\\documents","keyword":"合同","filetype":"docx,pdf"}'
```

返回结果包含匹配的文件路径和匹配类型（`filename` 或 `content`）。

### 版本管理

每次修改文件时，BJS 自动保存一个历史版本副本（存放在 `data/versions/` 下）。

查看文件版本列表：
```
GET /api/advanced/versions?path={文件路径}
```

```bash
curl "http://127.0.0.1:8765/api/advanced/versions?path=C:\\report.docx"
```

恢复指定版本：
```
POST /api/advanced/versions/restore
```
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| path | string | 是 | 文件路径 |
| version | string | 是 | 版本时间戳，如 `20260810_143022` |

```bash
curl -X POST http://127.0.0.1:8765/api/advanced/versions/restore \
  -H "Content-Type: application/json" \
  -d '{"path":"C:\\report.docx","version":"20260810_143022"}'
```

### 重复文件查找

```
POST /api/advanced/duplicates
```

扫描目录找出内容完全相同的文件（基于 MD5 或 SHA1）。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| path | string | 是 | 扫描目录 |
| algorithm | string | 否 | `md5` 或 `sha1`，默认 md5 |
| min_size | int | 否 | 最小文件大小（字节），小于此值的文件忽略，默认 1024 |

```bash
curl -X POST http://127.0.0.1:8765/api/advanced/duplicates \
  -H "Content-Type: application/json" \
  -d '{"path":"C:\\downloads","algorithm":"md5","min_size":1024}'
```

### 压缩包管理

解压 ZIP：
```
POST /api/advanced/archive/extract
```
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| archive | string | 是 | 压缩包路径 |
| target | string | 是 | 解压目标目录 |

创建 ZIP：
```
POST /api/advanced/archive/create
```
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| sources | array | 是 | 要打包的文件或目录路径列表 |
| target | string | 是 | 输出 zip 路径 |
| format | string | 否 | 目前仅支持 `zip` |

```bash
curl -X POST http://127.0.0.1:8765/api/advanced/archive/create \
  -H "Content-Type: application/json" \
  -d '{"sources":["C:\\docs","C:\\photos"],"target":"C:\\backup.zip"}'
```

### 局域网分享（占位）

```
POST /api/advanced/share
```
生成一个临时局域网访问链接（目前为占位功能，后续会实现真正的文件服务）。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| path | string | 是 | 要分享的路径 |
| expires_in | int | 否 | 有效期（秒），默认 3600 |

### 远程协助（占位）

```
POST /api/advanced/remote/token
```
生成一次性访问令牌（占位功能）。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| expires_in | int | 否 | 有效期（秒），默认 300 |

### 多设备同步（占位）

```
POST /api/advanced/sync/device
```
配置设备间的同步（占位功能，后续扩展）。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| device_id | string | 是 | 设备标识 |
| sync_path | string | 是 | 同步目录 |
| auto_sync | bool | 否 | 是否自动同步 |

### 插件管理（占位）

安装插件：
```
POST /api/advanced/plugin/install
```
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| source | string | 是 | 插件下载地址 |
| name | string | 是 | 插件名称 |

执行插件：
```
POST /api/advanced/plugin/exec
```
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| plugin | string | 是 | 插件名称 |
| action | string | 是 | 动作名称 |

### 自定义脚本执行

```
POST /api/advanced/script/exec
```
执行一段 Python 脚本并返回结果。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| script | string | 是 | Python 代码 |
| timeout | int | 否 | 超时时间（秒），默认 10 |

```bash
curl -X POST http://127.0.0.1:8765/api/advanced/script/exec \
  -H "Content-Type: application/json" \
  -d '{"script":"print(\"Hello from BJS\")"}'
```

---

## 卡密验证接口

查询当前卡密状态：
```
GET /api/license/status
```

手动验证卡密：
```
POST /api/license/verify
```
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| key | string | 是 | 卡密字符串 |

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
```

如果使用exe，请使用预制包或手动打包

---

## 其他功能

### 开机自启
首次运行时会自动添加开机启动项（Windows 注册表或 Linux `~/.config/autostart`），方便服务常驻。

### 自动更新
程序启动时会检查 GitHub 上的新版本。如果发现更新，会在托盘菜单中提示，点击“检查更新”即可下载并安装新版本（需要管理员权限以替换文件）。

### 召回机制
用于特殊情况下远程通知用户执行操作。该功能仅在必要时触发，不影响正常使用。

---

## 关于安全性

服务**默认**只监听 `127.0.0.1`，也就是说只有本机才能访问。增强安全性。
> [!WARNING]
> 不建议开放HTTP接口 除非在内网环境或有足够的安全措施

> [!CAUTION]
> 如果你自己改了绑定地址，或者用内网穿透之类的工具把服务暴露出去，强烈建议在前面加一层鉴权。

> [!IMPORTANT]
> 开发者 HXZXS 不对任何类型的问题承担任何责任
---

## 许可证

Apache License 2.0

> [!TIP]
> 分发时请注明原作者 HXZXS


[LICENSE](https://github.com/HXZXS/Better-JavaScript/blob/main/LICENSE)
