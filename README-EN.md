# Better JavaScript
### HXZXS
### Work in Progress
# Data Relay

Bridge between web pages and local programs.
<img width="570" height="274" alt="BJS" src="https://github.com/user-attachments/assets/e0260433-7be8-442a-b2c6-a2ec6d33778e" />

### 中文版本

[README.md](https://github.com/HXZXS/Better-JavaScript/blob/main/README.md)

---

## About the License Key

This project is open source long-term.

Visit [https://bjs.rth1.xyz/](https://bjs.rth1.xyz/key.html) to get a **free** developer license key (requires local installation of this product).

## What This Does

Web pages running in a browser can't normally access local files or run local programs.

BJS Data Relay solves that. It runs an HTTP service on your local machine. Web pages send requests, the service executes the corresponding local operations, and returns results to the page.

So you can:

- Open folders on your computer from a web page
- Display real system dialog windows from a web page
- Launch local programs from a web page
- Browse, create, delete, copy, and move files through a web page
- Parse and download files from Lanzou cloud storage via a web page
- ......

---

## Quick Start

### Download

Get the latest `bjs_relay.exe` from the [Releases](https://github.com/HXZXS/Better-JavaScript/releases) page. You can also run the Python source directly, see instructions below.

### Permissions
> [!IMPORTANT]
> <img width="290" height="133" alt="image" src="https://github.com/user-attachments/assets/cfc0d48d-275a-435b-813a-a0f5b888a33f" />

Please grant the necessary execution permissions.

### Run

Double-click `bjs_relay.exe` to install and start the program.
Listens on `127.0.0.1:8765` by default. Visit `http://127.0.0.1:8765/health` in your browser. If you see `{"code":0,"status":"running"}`, everything is working.

### Files and Directories

The following will be created in the program directory:

| File/Directory | Description |
|----------------|-------------|
| `bjs.log` | Runtime logs, check here first if something breaks |
| `logo.ico` | Tray icon, replace with your own, defaults to generic if missing |
| `downloads/` | Default storage for Lanzou downloads |
| `data/` | License cache, task configs, version history, etc. Located at `%APPDATA%\BJS` (Windows) or `~/.config/bjs` (Linux) |

---

## API Reference

All endpoints return a consistent format:

```json
{
  "code": 0,
  "msg": "ok",
  "data": {}
}
```

`code` of `0` means success, `-1` means failure. Check individual endpoint descriptions for specific response contents.

### Health Check

```
GET /health
```

Checks if the service is running.

```bash
curl http://127.0.0.1:8765/health
```

### Open Path

```
GET /api/open?path={path}
```

Opens a folder in Explorer, or opens a file with its default program.

| Parameter | Description |
|-----------|-------------|
| path | Local absolute path |

```bash
curl "http://127.0.0.1:8765/api/open?path=C:\\Users"
```

### Show Message

```
POST /api/msg
```

Displays a native message dialog.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | Message content |
| title | string | No | Window title, defaults to "来自网页" |
| type | string | No | See below, defaults to info |
| image | string | No | Image URL or local path |
| width | int | No | Window width for image mode |
| height | int | No | Window height for image mode |

`type` values:

- `info` — informational
- `warning` — warning
- `error` — error
- `question` — question (returns yes/no)
- `yesno` — yes/no
- `okcancel` — OK/Cancel
- `yesnocancel` — Yes/No/Cancel

```bash
curl -X POST http://127.0.0.1:8765/api/msg \
  -H "Content-Type: application/json" \
  -d '{"text":"File saved","type":"info","title":"Notice"}'
```

### Run Program

```
POST /api/run
```

Launches a local program.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | string | Yes | Program path |
| args | string | No | Command line arguments, space-separated |
| wait | bool | No | Wait for program to finish, default false |

```bash
curl -X POST http://127.0.0.1:8765/api/run \
  -H "Content-Type: application/json" \
  -d '{"path":"notepad.exe","args":"readme.txt"}'
```

When `wait` is `true`, the response includes program output:

```json
{
  "code": 0,
  "msg": "ok",
  "data": {
    "returncode": 0,
    "stdout": "program output",
    "stderr": ""
  }
}
```

### Custom Dialog

```
POST /api/dialog
```

Configures a dialog with multiple input controls via JSON. Good for collecting user input.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| config | string | Yes | JSON dialog configuration |

**Configuration format:**

```json
{
  "title": "Dialog Title",
  "width": 500,
  "height": 400,
  "controls": [
    {"type": "label", "text": "Some description text"},
    {"type": "entry", "label": "Name", "id": "name", "default": "John"},
    {"type": "combobox", "label": "Gender", "id": "gender", "options": ["Male", "Female"]},
    {"type": "checkbox", "label": "Interests", "id": "hobby", "options": ["Reading", "Music"], "default": ["Reading"]},
    {"type": "radio", "label": "Level", "id": "level", "options": ["Beginner", "Intermediate", "Advanced"]},
    {"type": "progress", "label": "Progress", "id": "progress", "value": 50, "maximum": 100},
    {"type": "image", "src": "https://example.com/logo.png"},
    {"type": "text", "label": "Notes", "id": "remarks", "rows": 4}
  ],
  "buttons": ["OK", "Cancel"]
}
```

**Control types:**

| type | Description |
|------|-------------|
| `label` | Plain text, display only |
| `entry` | Single-line text input |
| `text` | Multi-line text input |
| `password` | Password input |
| `combobox` | Dropdown selection |
| `checkbox` | Multi-choice checkboxes |
| `radio` | Radio buttons |
| `progress` | Progress bar |
| `image` | Display an image |

Example:

```bash
curl -X POST http://127.0.0.1:8765/api/dialog \
  -H "Content-Type: application/json" \
  -d '{"config":"{\"title\":\"Edit Info\",\"controls\":[{\"type\":\"entry\",\"label\":\"Name\",\"id\":\"name\"}],\"buttons\":[\"Save\"]}"}'
```

Response includes the user's action and entered values:

```json
{
  "code": 0,
  "msg": "ok",
  "data": {
    "button": "Save",
    "values": {"name": "Jane", "gender": "Female"}
  }
}
```

---

## File Operations

> [!NOTE]
> For safety, some system directories are blocked in release builds.
>
> This section is still being refined.

### List Directory

```
GET /api/listdir?path={path}
```

```bash
curl "http://127.0.0.1:8765/api/listdir?path=C:\\"
```

Response:

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

### Read Text File

```
GET /api/readfile?path={path}
```

Auto-detects UTF-8 and GBK encoding.

```bash
curl "http://127.0.0.1:8765/api/readfile?path=C:\\readme.txt"
```

### Create Folder

```
POST /api/mkdir
```

| Parameter | Description |
|-----------|-------------|
| path | Directory path to create |

```bash
curl -X POST http://127.0.0.1:8765/api/mkdir \
  -H "Content-Type: application/json" \
  -d '{"path":"C:\\NewFolder"}'
```

### Delete

```
POST /api/delete
```

| Parameter | Description |
|-----------|-------------|
| path | File or directory path |
| recursive | Whether to delete directory contents recursively |

```bash
curl -X POST http://127.0.0.1:8765/api/delete \
  -H "Content-Type: application/json" \
  -d '{"path":"C:\\temp","recursive":true}'
```

### Copy

```
POST /api/copy
```

| Parameter | Description |
|-----------|-------------|
| src | Source path |
| dest | Destination path |

```bash
curl -X POST http://127.0.0.1:8765/api/copy \
  -H "Content-Type: application/json" \
  -d '{"src":"C:\\a.txt","dest":"D:\\b.txt"}'
```

### Move

```
POST /api/move
```

| Parameter | Description |
|-----------|-------------|
| src | Source path |
| dest | Destination path |

```bash
curl -X POST http://127.0.0.1:8765/api/move \
  -H "Content-Type: application/json" \
  -d '{"src":"C:\\a.txt","dest":"D:\\b.txt"}'
```

---

## Lanzou Download

```
POST /api/lanzou/download
```

Parses a Lanzou share link and downloads the file.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| url | string | Yes | Lanzou share link |
| pwd | string | No | Extraction password, leave empty if none |
| save_path | string | No | Save location, defaults to downloads/ directory |

```bash
curl -X POST http://127.0.0.1:8765/api/lanzou/download \
  -H "Content-Type: application/json" \
  -d '{"url":"https://xxx.lanzouw.com/xxxxx","pwd":"h0fv"}'
```
> [!IMPORTANT]
> This uses a third-party API service.
>
> Not affiliated with this project.
>
> Thanks to [https://api.bugpk.com/](https://api.bugpk.com/doc-lanzou.html) for providing the parsing service.

---

## System Information

```
GET /api/sysinfo
```

Returns OS version, CPU cores, memory size, etc. If `psutil` isn't installed, returns basic system info only.

```bash
curl http://127.0.0.1:8765/api/sysinfo
```

---

## View Logs

```
GET /api/log?lines={lines}
```

Gets the most recent N lines of logs, default 100.

```bash
curl "http://127.0.0.1:8765/api/log?lines=50"
```

---

## Advanced Features (License Key Required)

Advanced features require a valid license key. See the "About the License Key" section at the top for how to get one. Once activated, all the following endpoints become available.

### Batch Rename

```
POST /api/advanced/batch-rename
```

Renames files in bulk using regular expressions.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | string | Yes | Directory path |
| pattern | string | Yes | Regular expression pattern |
| replacement | string | Yes | Replacement string |
| preview | bool | No | Preview only, don't actually rename, default true |

```bash
curl -X POST http://127.0.0.1:8765/api/advanced/batch-rename \
  -H "Content-Type: application/json" \
  -d '{"path":"C:\\photos","pattern":"IMG_(\\d+)","replacement":"photo_$1","preview":true}'
```

Response (preview mode):
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

### Directory Sync

```
POST /api/advanced/sync
```

Syncs source directory contents to destination. Supports mirror, merge, and update modes.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| src | string | Yes | Source directory |
| dest | string | Yes | Destination directory |
| mode | string | No | Mode: `mirror` (delete extra files in dest), `merge` (add only, no delete), `update` (update existing only). Default mirror |
| exclude | array | No | Extension list to exclude, e.g., `[".tmp", ".log"]` |

```bash
curl -X POST http://127.0.0.1:8765/api/advanced/sync \
  -H "Content-Type: application/json" \
  -d '{"src":"C:\\work","dest":"E:\\backup","mode":"mirror","exclude":[".tmp"]}'
```

### Scheduled Tasks

```
POST /api/advanced/schedule
```

Adds a scheduled task that runs actions at specified times using cron expressions or fixed intervals.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| name | string | Yes | Task name, must be unique |
| trigger | string | Yes | `cron` or `interval` |
| expression | string | Yes | Cron expression or interval in seconds |
| action | string | Yes | Currently only `sync` (directory sync) |
| params | object | No | Action parameters, e.g., `{"src":"C:\\data","dest":"E:\\backup"}` |

```bash
curl -X POST http://127.0.0.1:8765/api/advanced/schedule \
  -H "Content-Type: application/json" \
  -d '{"name":"dailybackup","trigger":"cron","expression":"0 2 * * *","action":"sync","params":{"src":"C:\\data","dest":"E:\\backup"}}'
```

### Clipboard History

```
GET /api/advanced/clipboard/history?limit={count}
```

Gets recently saved clipboard contents (up to 100 entries).

```bash
curl "http://127.0.0.1:8765/api/advanced/clipboard/history?limit=10"
```

Restore a specific entry:
```
POST /api/advanced/clipboard/restore
```
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| index | int | Yes | Index in history (0-based) |

```bash
curl -X POST http://127.0.0.1:8765/api/advanced/clipboard/restore \
  -H "Content-Type: application/json" \
  -d '{"index":0}'
```

### File Watch

```
POST /api/advanced/watch
```

Watches a directory and automatically moves or copies files when created or modified.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | string | Yes | Directory to watch |
| events | array | No | Events to watch, e.g., `["create","modify"]`, default `["create"]` |
| filter | string | No | Filter by extension, e.g., `".pdf"`, default `*` |
| action | string | Yes | `move` or `copy` |
| target | string | Yes | Target directory |

```bash
curl -X POST http://127.0.0.1:8765/api/advanced/watch \
  -H "Content-Type: application/json" \
  -d '{"path":"C:\\incoming","action":"move","target":"C:\\archive","filter":".pdf"}'
```

Stop watching:
```
POST /api/advanced/watch/stop
```
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | string | Yes | Directory to stop watching |

### Full-Text Search

```
POST /api/advanced/search
```

Searches a directory for keywords in filenames or file contents.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | string | Yes | Root directory |
| keyword | string | Yes | Search keyword |
| filetype | string | No | Extension filter, e.g., `"docx,pdf"` |

```bash
curl -X POST http://127.0.0.1:8765/api/advanced/search \
  -H "Content-Type: application/json" \
  -d '{"path":"C:\\documents","keyword":"contract","filetype":"docx,pdf"}'
```

Returns file paths and match type (`filename` or `content`).

### Version Management

Every time a file is modified, BJS automatically saves a historical copy (stored in `data/versions/`).

List versions:
```
GET /api/advanced/versions?path={file_path}
```

```bash
curl "http://127.0.0.1:8765/api/advanced/versions?path=C:\\report.docx"
```

Restore a version:
```
POST /api/advanced/versions/restore
```
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | string | Yes | File path |
| version | string | Yes | Version timestamp, e.g., `20260810_143022` |

```bash
curl -X POST http://127.0.0.1:8765/api/advanced/versions/restore \
  -H "Content-Type: application/json" \
  -d '{"path":"C:\\report.docx","version":"20260810_143022"}'
```

### Find Duplicates

```
POST /api/advanced/duplicates
```

Scans a directory for duplicate files (based on MD5 or SHA1).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | string | Yes | Directory to scan |
| algorithm | string | No | `md5` or `sha1`, default md5 |
| min_size | int | No | Minimum file size in bytes, smaller files ignored, default 1024 |

```bash
curl -X POST http://127.0.0.1:8765/api/advanced/duplicates \
  -H "Content-Type: application/json" \
  -d '{"path":"C:\\downloads","algorithm":"md5","min_size":1024}'
```

### Archive Management

Extract ZIP:
```
POST /api/advanced/archive/extract
```
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| archive | string | Yes | Archive path |
| target | string | Yes | Extraction destination |

Create ZIP:
```
POST /api/advanced/archive/create
```
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| sources | array | Yes | List of files/directories to pack |
| target | string | Yes | Output zip path |
| format | string | No | Currently only `zip` |

```bash
curl -X POST http://127.0.0.1:8765/api/advanced/archive/create \
  -H "Content-Type: application/json" \
  -d '{"sources":["C:\\docs","C:\\photos"],"target":"C:\\backup.zip"}'
```

### LAN Share (Placeholder)

```
POST /api/advanced/share
```
Generates a temporary LAN access link (placeholder, full file serving coming later).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | string | Yes | Path to share |
| expires_in | int | No | Expiry time in seconds, default 3600 |

### Remote Assistance (Placeholder)

```
POST /api/advanced/remote/token
```
Generates a one-time access token (placeholder).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| expires_in | int | No | Expiry time in seconds, default 300 |

### Multi-Device Sync (Placeholder)

```
POST /api/advanced/sync/device
```
Configures sync between devices (placeholder, will be expanded later).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| device_id | string | Yes | Device identifier |
| sync_path | string | Yes | Sync directory |
| auto_sync | bool | No | Auto-sync on/off |

### Plugin Management (Placeholder)

Install plugin:
```
POST /api/advanced/plugin/install
```
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| source | string | Yes | Plugin download URL |
| name | string | Yes | Plugin name |

Execute plugin:
```
POST /api/advanced/plugin/exec
```
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| plugin | string | Yes | Plugin name |
| action | string | Yes | Action name |

### Custom Script Execution

```
POST /api/advanced/script/exec
```
Executes a piece of Python code and returns the result.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| script | string | Yes | Python code |
| timeout | int | No | Timeout in seconds, default 10 |

```bash
curl -X POST http://127.0.0.1:8765/api/advanced/script/exec \
  -H "Content-Type: application/json" \
  -d '{"script":"print(\"Hello from BJS\")"}'
```

---

## License Key Verification Endpoints

Check current license status:
```
GET /api/license/status
```

Manually verify a license key:
```
POST /api/license/verify
```
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| key | string | Yes | License key string |

---

## Included Web Pages

Two HTML pages are included with the project, open them in your browser:

- **Console** — UI for all functions, good for testing
- **Developer Docs** — API documentation with built-in test tools

These pages are in the `web/` directory. Open them directly in your browser.

---

## Running from Source

If you prefer to run the Python script directly instead of using the EXE:

```bash
# Install dependencies
pip install flask flask-cors pystray pillow
```

For EXE builds, use the prebuilt package or package it manually.

---

## Additional Features

### Auto-Start
First run automatically adds a startup entry (Windows Registry or Linux `~/.config/autostart`) so the service stays resident.

### Auto-Update
The program checks GitHub for new versions on startup. If an update is found, the tray menu will notify you. Click "Check for Updates" to download and install the new version (requires admin privileges to replace files).

### Recall Mechanism
Emergency remote notification system used to trigger actions (uninstall or delete key service) when necessary. This only activates under specific conditions and does not affect normal use.

---

## Security Considerations

The service **defaults** to listening only on `127.0.0.1`, meaning only localhost can access it.
> [!WARNING]
> Exposing this HTTP interface publicly is not recommended unless you're in a trusted network environment with adequate security measures.

> [!CAUTION]
> If you modify the binding address or use tunneling tools to expose the service externally, it is strongly recommended to add authentication in front of it.

> [!IMPORTANT]
> Developer HXZXS assumes no responsibility for any issues arising from any use case.

---

## License

Apache License 2.0

> [!TIP]
> Please credit the original author HXZXS when redistributing.


[LICENSE](https://github.com/HXZXS/Better-JavaScript/blob/main/LICENSE)
---
## About

*Translation provided by Deepseek.*
