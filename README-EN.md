# English Version

# Better JavaScript

**HXZXS**
**Work in progress**

## Data Relay

Connect web pages to local programs.

<img width="570" height="274" alt="BJS" src="https://github.com/user-attachments/assets/e0260433-7be8-442a-b2c6-a2ec6d33778e" />

中文版：[README.md](https://github.com/HXZXS/Better-JavaScript/blob/main/README.md)

---

## About the license key

This project is open source long-term. Developer keys are free but require the product to be installed locally:

[https://bjs.rth1.xyz/key.html](https://bjs.rth1.xyz/key.html)

Base features work without a key. Advanced features (scheduled tasks, file watching, version history, LAN sharing, etc.) need one.

## What this is

Web pages run in a browser sandbox. They can't touch local files or launch programs. BJS Data Relay fixes that by running a local HTTP service — the page sends a request, the service does the work, and returns the result.

What you can do:

- Open folders or files with their default programs
- Pop real system dialogs (including image dialogs)
- Launch local programs, optionally wait for output
- Browse, read, write, create, delete, copy, move files
- Parse Lanzou Cloud links and download
- Share files over the LAN with password and upload support
- Windows stuff: file attributes, recycle bin, Explorer reveal, system notifications
- Batch rename, directory sync, full-text search, version history, duplicate finder
- Archives, scheduled tasks, file watching, clipboard history
- ...

## Getting started

### Download

Grab `bjs_relay.exe` from [Releases](https://github.com/HXZXS/Better-JavaScript/releases). Or run the source directly — see "Running from source" below.

### Permissions

> [!IMPORTANT]
> <img width="290" height="133" alt="image" src="https://github.com/user-attachments/assets/cfc0d48d-275a-435b-813a-a0f5b888a33f" />

Grant the necessary permissions. On Windows you'll see a UAC prompt on first launch.

The program does a few things automatically at startup:

- Requests admin (Windows)
- Adds a firewall rule for port 8765
- Registers itself for autostart
- Starts clipboard monitoring

### Run

Double-click. The service listens on `127.0.0.1:8765`.

Open `http://127.0.0.1:8765/health` in a browser. If you see this, it's working:

```json
{"code":0,"status":"running","port":8765,"version":"6.0.4.α"}
```

### File locations

User data (logs, cache, task config) lives here:

- Windows: `%APPDATA%\BJS`
- Linux/macOS: `~/.config/bjs`

The program folder may contain `logo.ico` (tray icon) and `BJS developer key.exe` (key service). If they're missing, defaults are used.

---

## API reference

All endpoints return the same shape:

```json
{"code": 0, "msg": "ok", "data": {}}
```

`code = 0` means success, `-1` means failure.

### Health check

```
GET /health
```

```bash
curl http://127.0.0.1:8765/health
```

### Open path

```
GET /api/open?path={path}
```

Opens folders in Explorer, files with their associated program.

```bash
curl "http://127.0.0.1:8765/api/open?path=C:\\Users"
```

### Dialog

```
POST /api/msg
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | yes | Message |
| title | string | no | Window title |
| type | string | no | See below |
| image | string | no | Image URL or local path |
| width | int | no | Image dialog width |
| height | int | no | Image dialog height |

`type` values: `info`, `warning`, `error`, `question`, `yesno`, `okcancel`, `yesnocancel`.

```bash
curl -X POST http://127.0.0.1:8765/api/msg \
  -H "Content-Type: application/json" \
  -d '{"text":"Saved","type":"info"}'
```

### Run program

```
POST /api/run
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | string | yes | Program path |
| args | string | no | Space-separated args |
| wait | bool | no | Wait for exit, default false |

With `wait=true` you get the program's output:

```json
{"code":0,"data":{"returncode":0,"stdout":"...","stderr":""}}
```

### Custom dialog

```
POST /api/dialog
```

Build a multi-control dialog from JSON. Control types: `label`, `entry`, `text`, `password`, `combobox`, `checkbox`, `radio`, `progress`, `image`.

```json
{
  "title": "Edit",
  "width": 500,
  "controls": [
    {"type":"entry","label":"Name","id":"name"},
    {"type":"combobox","label":"Gender","id":"gender","options":["M","F"]}
  ],
  "buttons": ["Save", "Cancel"]
}
```

Returns the button clicked and the values:

```json
{"code":0,"data":{"button":"Save","values":{"name":"John"}}}
```

---

## File operations

> [!NOTE]
> Release builds block a few system paths to prevent accidents.

### List directory

```
GET /api/listdir?path={path}
```

```json
{"code":0,"data":[
  {"name":"Users","is_dir":true,"size":0,"size_str":"","mtime":"2026-08-10 12:00:00"}
]}
```

### Read text file

```
GET /api/readfile?path={path}
```

Tries UTF-8 / UTF-8-BOM / GBK / Latin-1 in order. Optional line range:

| Parameter | Description |
|-----------|-------------|
| start_line | 1-based start |
| end_line | End line |

Files over 8MB get truncated.

### Write file

```
POST /api/writefile
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | string | yes | File path |
| content | string | yes | Content |
| encoding | string | no | Default utf-8 |
| append | bool | no | Append mode |

Parent directories are created automatically.

### Create directory

```
POST /api/mkdir
```

### Delete

```
POST /api/delete
```

⚠️ Straight delete, no recycle bin. Use `/api/win/recycle` to keep the file recoverable.

### Copy / move

```
POST /api/copy
POST /api/move
```

### Rename

```
POST /api/rename
```

New name can't contain path separators.

### File info

```
GET /api/fileinfo?path={path}
```

Returns timestamps, extension, and (on Windows) hidden/readonly/system/archive flags.

### Directory size

```
GET /api/dirsize?path={path}
```

```json
{"code":0,"data":{"bytes":1073741824,"human":"1.0GB","files":1234,"dirs":56}}
```

### Replace in file

```
POST /api/replace
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | string | yes | File path |
| find | string | yes | Search text |
| replace | string | yes | Replacement |
| regex | bool | no | Treat find as regex |
| count | int | no | 0 = replace all |

---

## Windows-only

### Set file attributes

```
POST /api/win/attr
```

Fields not provided stay as-is.

### Send to recycle bin

```
POST /api/win/recycle
```

### Reveal in Explorer

```
POST /api/win/reveal
```

### System notification

```
POST /api/win/notify
```

Shows a tray balloon. Requires the app to be running.

---

## Lanzou Cloud download

```
POST /api/lanzou/download
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| url | string | yes | Share link |
| pwd | string | no | Extraction password |
| save_path | string | no | Target; defaults to downloads/ |

> [!IMPORTANT]
> Parsing is done by [https://api.bugpk.com/](https://api.bugpk.com/doc-lanzou.html), unrelated to this project.

---

## System info

```
GET /api/sysinfo
```

Returns OS, CPU count, memory, disk. Detailed if `psutil` is installed.

## Log

```
GET /api/log?lines={n}
```

Last N lines, default 100.

---

## Advanced features (require key)

### Batch rename

```
POST /api/advanced/batch-rename
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | string | yes | Directory |
| pattern | string | yes | Regex |
| replacement | string | yes | Replacement |
| preview | bool | no | Preview only, default true |

```bash
curl -X POST http://127.0.0.1:8765/api/advanced/batch-rename \
  -H "Content-Type: application/json" \
  -d '{"path":"C:\\photos","pattern":"IMG_(\\d+)","replacement":"photo_$1","preview":true}'
```

### Directory sync

```
POST /api/advanced/sync
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| src | string | yes | Source |
| dest | string | yes | Destination |
| mode | string | no | `mirror` / `merge` / `update` |
| exclude | array | no | Suffixes to skip, e.g. `[".tmp"]` |

`mirror` deletes extras in target. `merge` only adds. `update` only touches existing files.

### Scheduled tasks

```
POST /api/advanced/schedule
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| name | string | yes | Unique name |
| trigger | string | yes | `cron` or `interval` |
| expression | string | yes | Cron expression or seconds |
| action | string | yes | Only `sync` for now |
| params | object | no | Action params |

Tasks persist across restarts.

### Clipboard history

```
GET /api/advanced/clipboard/history?limit={n}
```

Up to 100 entries, monitored via pywin32.

```
POST /api/advanced/clipboard/restore
```

### File watching

```
POST /api/advanced/watch
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | string | yes | Directory to watch |
| events | array | no | Default `["create"]` |
| filter | string | no | Extension, default `*` |
| action | string | yes | `move` or `copy` |
| target | string | yes | Destination |

```
POST /api/advanced/watch/stop
```

### Full-text search

```
POST /api/advanced/search
```

Searches filenames and contents. Capped at 100 results.

### Version history

```
GET /api/advanced/versions?path={path}
POST /api/advanced/versions/restore
```

A copy is saved before any file-modifying operation.

### Duplicate finder

```
POST /api/advanced/duplicates
```

MD5 or SHA1 by content.

### Archives

```
POST /api/advanced/archive/extract
POST /api/advanced/archive/create
```

ZIP only for now.

### LAN sharing

```
POST /api/advanced/share
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | string | yes | Path to share |
| expires_in | int | no | Seconds, default 3600 |
| readonly | bool | no | Default true |
| password | string | no | Access password |
| upload | bool | no | Allow uploads |
| note | string | no | Note |

Returns a URL reachable from the same subnet. The share page supports drag-and-drop upload, ZIP download, filtering, sorting.

Session management:

```
GET /api/advanced/share/list
POST /api/advanced/share/close
```

### Remote assistance

```
POST /api/advanced/remote/token
```

Read-only temporary token, rooted at the user's home directory.

### Multi-device sync

```
POST /api/advanced/sync/device
```

Registers a device. Persisted locally for future extension.

### Plugin management

```
POST /api/advanced/plugin/install
POST /api/advanced/plugin/exec
```

Installs Python plugins from URL or local path to `data/plugins/`.

### Custom scripts

```
POST /api/advanced/script/exec
```

Runs Python code. ⚠️ Currently a placeholder — sandboxing comes later.

---

## License endpoints

```
GET /api/license/status
POST /api/license/verify
```

---

## Web UI

Two HTML pages in `web/`:

- **Console** (`WEB.html`) — GUI for every feature
- **Docs** (`WEBHELP.html`) — API reference with an inline tester

Just open them in a browser.

---

## Running from source

```bash
pip install flask flask-cors pystray pillow pywin32 wmi psutil apscheduler watchdog
python bjs_relay.py
```

Package with PyInstaller if you want an exe.

---

## Other

### Autostart

Checked and updated every launch. Windows registry on Windows, `~/.config/autostart` on Linux.

### Auto-update

Checks GitHub Releases on startup. Click "Check for updates" in the tray menu to download and install.

### Recall

Remote signal to uninstall or remove the key service. Only fires when needed.

### Announcements

Server-side push, 5 levels:

| Level | Behavior |
|-------|----------|
| O | Orange flashing dialog, closes after 10s |
| A | Orange dialog, 5s |
| B | Blue dialog, 3s |
| C | Plain info dialog |
| D | Tray balloon, click to view details |

---

## Security

The service binds to `127.0.0.1` by default — localhost only.

> [!WARNING]
> Don't expose the HTTP interface unless you're on a trusted network or have proper auth in front.

> [!CAUTION]
> If you change the bind address or put the service behind a tunnel, add authentication. Seriously.

> [!IMPORTANT]
> HXZXS accepts no responsibility for any problems that arise.

---

## License

Apache License 2.0. Please credit HXZXS when redistributing.

[LICENSE](https://github.com/HXZXS/Better-JavaScript/blob/main/LICENSE)
