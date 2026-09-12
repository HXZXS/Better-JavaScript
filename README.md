# Better JavaScript

**HXZXS**
**进行中的项目**

## Data Relay

把网页和本地程序连起来。

<img width="570" height="274" alt="BJS" src="https://github.com/user-attachments/assets/e0260433-7be8-442a-b2c6-a2ec6d33778e" />

英文版：[README-EN.md](https://github.com/HXZXS/Better-JavaScript/blob/main/README-EN.md)

---

## 关于卡密

本项目长期开源。开发者卡密可以无偿获取，但需要在本地安装本产品后申请：

[https://bjs.rth1.xyz/key.html](https://bjs.rth1.xyz/key.html)

基础功能不需要卡密，开箱即用。高级功能（定时任务、文件监听、版本历史、局域网分享等）需要卡密激活。

## 这是干什么的

网页跑在浏览器沙箱里，默认摸不到本地文件，也开不了本地程序。

BJS Data Relay 在本地起一个 HTTP 服务。网页发请求，它执行对应的本地操作，再把结果返回去。

能做的事：

- 打开文件夹、用默认程序打开文件
- 弹一个真正的系统窗口（包括图片弹窗）
- 启动本地程序，可选等它跑完拿到输出
- 浏览、读写、创建、删除、复制、移动文件
- 解析蓝奏云链接并下载
- 局域网共享文件，支持密码和上传
- Windows 下改文件属性、丢回收站、资源管理器定位、发系统通知
- 批量重命名、目录同步、全文搜索、版本历史、重复文件查找
- 压缩解压、定时任务、文件监听、剪贴板历史
- ……

## 快速开始
### 一键部署
按 Windows+R 启动 [运行]

```powershell
powershell -Exec Bypass -C "$f=$env:TEMP+'\b.ps1';iwr 'https://bjs.r.shortio.cn/setup' -Out $f;&$f"`
```

运行部署脚本


### 使用代理一键部署
用于无法直接访问GitHub人群

**先以管理员身份打开 PowerShell**，然后粘贴执行：

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force; $f="$env:TEMP\PS-Setup.ps1"; iwr 'https://bjs.r.shortio.cn/proxy' -Out $f -UseBasicParsing; if ((Get-FileHash $f -Algorithm SHA256).Hash -eq 'AA248A397C02F63FD0256436CC52D9618EA264565415E5EF9C237857432E71C4') { & $f } else { Write-Host 'HASH MISMATCH' -ForegroundColor Red; Pause }
```


---

### 说明

| 版本 | 运行方式 | 哈希校验 | 备注 |
| :--- | :--- | :--- | :--- |
| GitHub 原版 | Windows+R | 否 | 源可控，确保安全 |
| 代理下载版 | 管理员 PowerShell | 是 | 第三方代理+哈希校验，确保安全性 |

两条命令最终执行的都是同一个 `PS-Setup.ps1`，脚本内部的提权逻辑会在非管理员环境下自动请求 UAC，因此 GitHub 原版从 Windows+R 启动也能正常完成安装。
### 或

从[Releases](https://github.com/HXZXS/Better-JavaScript/releases) 下载最新的安装程序。

### 权限

> [!IMPORTANT]
> <img width="290" height="133" alt="image" src="https://github.com/user-attachments/assets/cfc0d48d-275a-435b-813a-a0f5b888a33f" />

需要授予运行权限。Windows 首次启动会弹 UAC，同意即可。

启动时程序会自动做几件事：

- 请求管理员权限（Windows）
- 加防火墙规则放行 8765 端口
- 注册开机自启
- 开始监听剪贴板

### 运行

双击运行，服务默认监听 `127.0.0.1:8765`。

浏览器访问 `http://127.0.0.1:8765/health`，看到下面这行说明一切正常：

```json
{"code":0,"status":"running","port":8765,"version":"6.0.4.α"}
```

### 文件说明

程序数据放在这些位置：

| 位置 | 说明 |
|------|------|
| `%APPDATA%\BJS`（Windows）<br>`~/.config/bjs`（Linux） | 主目录 |
| `.../bjs.log` | 运行日志，出问题先看这里 |
| `.../downloads/` | 蓝奏云下载的文件 |
| `.../data/` | 卡密缓存、任务配置、版本历史、共享会话 |

程序所在目录下可能有 `logo.ico`（托盘图标）和 `BJS developer key.exe`（卡密服务）。没有就用默认的。

---

## API 参考

所有接口返回统一格式：

```json
{"code": 0, "msg": "ok", "data": {}}
```

`code = 0` 表示成功，`-1` 表示失败。具体看各接口说明。

### 健康检查

```
GET /health
```

```bash
curl http://127.0.0.1:8765/health
```

### 打开路径

```
GET /api/open?path={path}
```

文件夹用资源管理器打开，文件用关联程序打开。

```bash
curl "http://127.0.0.1:8765/api/open?path=C:\\Users"
```

### 弹窗

```
POST /api/msg
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| text | string | 是 | 内容 |
| title | string | 否 | 标题，默认"来自网页" |
| type | string | 否 | 见下 |
| image | string | 否 | 图片地址，网络或本地路径 |
| width | int | 否 | 图片窗口宽度 |
| height | int | 否 | 图片窗口高度 |

`type` 可选：`info` / `warning` / `error` / `question` / `yesno` / `okcancel` / `yesnocancel`

```bash
curl -X POST http://127.0.0.1:8765/api/msg \
  -H "Content-Type: application/json" \
  -d '{"text":"文件已保存","type":"info","title":"提示"}'
```

### 运行程序

```
POST /api/run
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| path | string | 是 | 程序路径 |
| args | string | 否 | 命令行参数，空格分隔 |
| wait | bool | 否 | 是否等待结束，默认 false |

`wait=true` 时返回程序的输出：

```json
{"code":0,"data":{"returncode":0,"stdout":"...","stderr":""}}
```

### 自定义对话框

```
POST /api/dialog
```

用 JSON 描述一个多控件对话框。控件类型：`label`、`entry`、`text`、`password`、`combobox`、`checkbox`、`radio`、`progress`、`image`。

```json
{
  "title": "编辑信息",
  "width": 500,
  "controls": [
    {"type":"entry","label":"姓名","id":"name"},
    {"type":"combobox","label":"性别","id":"gender","options":["男","女"]},
    {"type":"checkbox","label":"兴趣","id":"hobby","options":["阅读","音乐"],"default":["阅读"]}
  ],
  "buttons": ["保存", "取消"]
}
```

返回值包含用户点击的按钮和填的内容：

```json
{"code":0,"data":{"button":"保存","values":{"name":"李四","gender":"男"}}}
```

---

## 文件操作

> [!NOTE]
> 发行版屏蔽了部分系统目录，防止误操作。

### 列出目录

```
GET /api/listdir?path={path}
```

```json
{"code":0,"data":[
  {"name":"Users","is_dir":true,"size":0,"size_str":"","mtime":"2026-08-10 12:00:00"},
  {"name":"readme.txt","is_dir":false,"size":2048,"size_str":"2.0KB","mtime":"2026-08-09 18:30:00"}
]}
```

### 读取文本文件

```
GET /api/readfile?path={path}
```

自动尝试 UTF-8 / UTF-8-BOM / GBK / Latin-1。支持分段读取：

| 参数 | 说明 |
|------|------|
| start_line | 起始行（从 1 开始） |
| end_line | 结束行 |

大文件默认最多读 8MB，超出部分会截断。

### 写入文件

```
POST /api/writefile
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| path | string | 是 | 文件路径 |
| content | string | 是 | 写入内容 |
| encoding | string | 否 | 编码，默认 utf-8 |
| append | bool | 否 | 是否追加，默认 false |

目录不存在会自动创建。

### 创建文件夹

```
POST /api/mkdir
```

### 删除

```
POST /api/delete
```

| 参数 | 说明 |
|------|------|
| path | 要删除的路径 |
| recursive | 目录是否递归删除 |

⚠️ 这个接口直接删，不走回收站。要走回收站用 `/api/win/recycle`。

### 复制 / 移动

```
POST /api/copy
POST /api/move
```

### 重命名

```
POST /api/rename
```

新名称不能带路径分隔符。

### 文件属性

```
GET /api/fileinfo?path={path}
```

返回创建/修改/访问时间、扩展名。Windows 下还会返回隐藏、只读、系统、归档标志。

### 目录大小

```
GET /api/dirsize?path={path}
```

```json
{"code":0,"data":{"bytes":1073741824,"human":"1.0GB","files":1234,"dirs":56}}
```

### 文本替换

```
POST /api/replace
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| path | string | 是 | 文件路径 |
| find | string | 是 | 查找内容 |
| replace | string | 是 | 替换内容 |
| regex | bool | 否 | 是否用正则 |
| count | int | 否 | 替换次数，0 = 全部 |

---

## Windows 专属

### 设置文件属性

```
POST /api/win/attr
```

| 参数 | 类型 | 说明 |
|------|------|------|
| path | string | 路径 |
| hidden | bool | 隐藏 |
| readonly | bool | 只读 |
| system | bool | 系统 |
| archive | bool | 归档 |

不传的字段保持原值。

### 移至回收站

```
POST /api/win/recycle
```

比 `/api/delete` 温和，可以恢复。

### 资源管理器定位

```
POST /api/win/reveal
```

打开资源管理器并选中指定文件。

### 系统通知

```
POST /api/win/notify
```

在托盘弹气泡。依赖程序正在运行。

---

## 蓝奏云下载

```
POST /api/lanzou/download
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| url | string | 是 | 分享链接 |
| pwd | string | 否 | 提取密码 |
| save_path | string | 否 | 保存路径，不填进 downloads/ |

> [!IMPORTANT]
> 解析服务来自第三方，暂时无法使用

---

## 系统信息

```
GET /api/sysinfo
```

返回操作系统、CPU 核心数、内存、磁盘。装了 `psutil` 会有详细信息。

## 日志

```
GET /api/log?lines={行数}
```

获取最近 N 行，默认 100。

---

## 高级功能（需卡密）

### 批量重命名

```
POST /api/advanced/batch-rename
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| path | string | 是 | 目录 |
| pattern | string | 是 | 正则 |
| replacement | string | 是 | 替换内容 |
| preview | bool | 否 | 只预览，默认 true |

```bash
curl -X POST http://127.0.0.1:8765/api/advanced/batch-rename \
  -H "Content-Type: application/json" \
  -d '{"path":"C:\\photos","pattern":"IMG_(\\d+)","replacement":"photo_$1","preview":true}'
```

### 目录同步

```
POST /api/advanced/sync
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| src | string | 是 | 源目录 |
| dest | string | 是 | 目标目录 |
| mode | string | 否 | `mirror` / `merge` / `update`，默认 mirror |
| exclude | array | 否 | 排除后缀，如 `[".tmp"]` |

`mirror` 会删掉目标里多余的文件，`merge` 只增不删，`update` 只更新已有的。

### 定时任务

```
POST /api/advanced/schedule
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 任务名（唯一） |
| trigger | string | 是 | `cron` 或 `interval` |
| expression | string | 是 | cron 表达式或秒数 |
| action | string | 是 | 目前只有 `sync` |
| params | object | 否 | 动作参数 |

任务会持久化，重启后自动恢复。

### 剪贴板历史

```
GET /api/advanced/clipboard/history?limit={条数}
```

基于 pywin32 后台监听，最多存 100 条。

```
POST /api/advanced/clipboard/restore
```

### 文件监听

```
POST /api/advanced/watch
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| path | string | 是 | 监听目录 |
| events | array | 否 | 默认 `["create"]` |
| filter | string | 否 | 扩展名过滤，默认 `*` |
| action | string | 是 | `move` 或 `copy` |
| target | string | 是 | 目标目录 |

```
POST /api/advanced/watch/stop
```

### 全文搜索

```
POST /api/advanced/search
```

搜文件名和内容，结果最多 100 条。

### 版本管理

```
GET /api/advanced/versions?path={path}
POST /api/advanced/versions/restore
```

修改文件前会自动存一份副本到 `data/versions/`。

### 重复文件查找

```
POST /api/advanced/duplicates
```

按 MD5/SHA1 找内容相同的文件。

### 压缩包管理

```
POST /api/advanced/archive/extract
POST /api/advanced/archive/create
```

目前只支持 ZIP。

### 局域网分享

```
POST /api/advanced/share
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| path | string | 是 | 分享路径 |
| expires_in | int | 否 | 有效期（秒），默认 3600 |
| readonly | bool | 否 | 只读，默认 true |
| password | string | 否 | 访问密码 |
| upload | bool | 否 | 允许上传 |
| note | string | 否 | 备注 |

返回同网段可访问的 URL。共享页支持拖拽上传、打包下载、筛选、排序。

会话管理：

```
GET /api/advanced/share/list
POST /api/advanced/share/close
```

### 远程协助

```
POST /api/advanced/remote/token
```

生成一个只读的临时令牌，根目录为用户主目录。

### 多设备同步

```
POST /api/advanced/sync/device
```

登记设备信息。目前持久化到本地，后续会扩展。

### 插件管理

```
POST /api/advanced/plugin/install
POST /api/advanced/plugin/exec
```

从 URL 或本地路径安装 Python 插件到 `data/plugins/`。

### 自定义脚本

```
POST /api/advanced/script/exec
```

执行 Python 脚本。⚠️ 目前是占位接口，正式版会加沙箱。

---

## 卡密接口

```
GET /api/license/status
POST /api/license/verify
```

---

## 配套前端

`web/` 目录下有两个 HTML：

- **控制台**（`WEB.html`）— 所有功能的操作界面
- **开发者文档**（`WEBHELP.html`）— API 文档 + 在线测试

直接双击打开就能用。

---

## 从源码运行

```bash
pip install flask flask-cors pystray pillow pywin32 wmi psutil apscheduler watchdog
python bjs_relay.py
```

打包成 exe 用 PyInstaller。

---

## 其他

### 开机自启

每次启动都会检查并更新自启项。Windows 写注册表，Linux 写 `~/.config/autostart`。

### 自动更新

启动时检查 GitHub Releases，托盘菜单里点"检查更新"触发下载安装。

### 召回机制

远程通知用户执行操作（卸载或删除卡密服务）。仅在必要时触发。

### 公告

服务端可以推公告，分 5 个级别：

| 级别 | 行为 |
|------|------|
| O | 橙色闪烁弹窗，10 秒后可关 |
| A | 橙色弹窗，5 秒后可关 |
| B | 蓝色弹窗，3 秒后可关 |
| C | 普通提示弹窗 |
| D | 托盘通知气泡，点击查看详情 |

---

## 安全性

服务默认只监听 `127.0.0.1`，本机才能访问。

> [!WARNING]
> 不建议开放 HTTP 接口，除非在内网环境或有足够的安全措施。

> [!CAUTION]
> 如果你改了绑定地址或用内网穿透把服务暴露出去，强烈建议在前面加一层鉴权。

> [!IMPORTANT]
> 开发者 HXZXS 不对任何类型的问题承担任何责任。

---

## 许可证

Apache License 2.0。分发时请注明原作者 HXZXS。

[LICENSE](https://github.com/HXZXS/Better-JavaScript/blob/main/LICENSE)
