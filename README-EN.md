# Better JavaScript
### Ongoing Project
# Data Relay

Connect web pages with local programs.
<img width="570" height="274" alt="BJS" src="https://github.com/user-attachments/assets/e0260433-7be8-442a-b2c6-a2ec6d33778e" />

### 让我们说中文

[README.md](https://github.com/HXZXS/Better-JavaScript/blob/main/README.md)

---

## What is this for?

Web pages run in browsers and, by default, cannot access local files or run local programs.

BJS Data Relay solves this problem. It runs an HTTP service on the local computer. The web page sends requests, the service executes the corresponding local operations, and then returns the results to the web page.

So you can:

- Open a folder on your computer from a web page
- Show a real system dialog from a web page
- Launch programs on your computer from a web page
- Browse, create, delete, copy, and move files from a web page
- Parse Lanzou cloud links and download files from a web page
- ......

---

## Quick Start

### Download

Go to the [Releases](https://github.com/HXZXS/Better-JavaScript/releases) page and download the latest `bjs_relay.exe`. You can also run the Python source code directly; see the instructions below.

### Run

Double-click `bjs_relay.exe` to install and wait for the program to start.
It listens on `127.0.0.1:8765` by default. Visit `http://127.0.0.1:8765/health` in your browser and see `{"code":0,"status":"running"}` – everything is working.

### Files generated

The following files and directories will be created in the program's directory:

| File/Directory | Description |
|----------------|-------------|
| `bjs.log` | Runtime log; check here first if something goes wrong |
| `logo.ico` | Tray icon; replace with your own, otherwise the default icon is shown |
| `downloads/` | Default directory for files downloaded from Lanzou |

---

## API Reference

All endpoints return a consistent response format:

```json
{
  "code": 0,
  "msg": "ok",
  "data": {}
}
```

`code` = `0` means success, `-1` means failure. See each endpoint's description for specific return contents.

### Health Check

```
GET /health
```

Check whether the service is running properly.

```bash
curl http://127.0.0.1:8765/health
```

### Open Path

```
GET /api/open?path={path}
```

Open a folder in File Explorer, or open a file with its default program.

| Parameter | Description |
|-----------|-------------|
| path | Local path, absolute path |

```bash
curl "http://127.0.0.1:8765/api/open?path=C:\\Users"
```

### Message Box

```
POST /api/msg
```

Display a message window locally.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | The text to display |
| title | string | No | Window title, default "From Web" |
| type | string | No | See below, default info |
| image | string | No | Image URL or local path |
| width | int | No | Window width in image mode |
| height | int | No | Window height in image mode |

`type` options:

- `info` — information
- `warning` — warning
- `error` — error
- `question` — question (returns yes/no)
- `yesno` — Yes/No
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

Launch a local program.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | string | Yes | Program path |
| args | string | No | Command‑line arguments, space‑separated |
| wait | bool | No | Whether to wait for the program to finish, default false |

```bash
curl -X POST http://127.0.0.1:8765/api/run \
  -H "Content-Type: application/json" \
  -d '{"path":"notepad.exe","args":"readme.txt"}'
```

When `wait` is set to `true`, the response includes the program's output:

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

Configure a dialog with various controls using JSON – suitable for collecting user input.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| config | string | Yes | JSON configuration for the dialog |

**Configuration format:**

```json
{
  "title": "Dialog Title",
  "width": 500,
  "height": 400,
  "controls": [
    {"type": "label", "text": "A line of description"},
    {"type": "entry", "label": "Name", "id": "name", "default": "Zhang San"},
    {"type": "combobox", "label": "Gender", "id": "gender", "options": ["Male", "Female"]},
    {"type": "checkbox", "label": "Interests", "id": "hobby", "options": ["Reading", "Music"], "default": ["Reading"]},
    {"type": "radio", "label": "Level", "id": "level", "options": ["Beginner", "Intermediate", "Advanced"]},
    {"type": "progress", "label": "Progress", "id": "progress", "value": 50, "maximum": 100},
    {"type": "image", "src": "https://example.com/logo.png"},
    {"type": "text", "label": "Remarks", "id": "remarks", "rows": 4}
  ],
  "buttons": ["OK", "Cancel"]
}
```

**Control types:**

| type | Description |
|------|-------------|
| `label` | Plain text, display only |
| `entry` | Single‑line input |
| `text` | Multi‑line text input |
| `password` | Password input |
| `combobox` | Drop‑down selection |
| `checkbox` | Multiple‑choice checkboxes |
| `radio` | Radio buttons |
| `progress` | Progress bar |
| `image` | Display an image |

Example call:

```bash
curl -X POST http://127.0.0.1:8765/api/dialog \
  -H "Content-Type: application/json" \
  -d '{"config":"{\"title\":\"Edit Info\",\"controls\":[{\"type\":\"entry\",\"label\":\"Name\",\"id\":\"name\"}],\"buttons\":[\"Save\"]}"}'
```

The response includes the user's action and entered values:

```json
{
  "code": 0,
  "msg": "ok",
  "data": {
    "button": "Save",
    "values": {"name": "Li Si", "gender": "Male"}
  }
}
```

---

## File Operations

> [!NOTE]
> For security reasons,
> the release version blocks certain directories.
>
> This section is still being optimised.

### List Directory

```
GET /api/listdir?path={path}
```

```bash
curl "http://127.0.0.1:8765/api/listdir?path=C:\\"
```

Example response:

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

Automatically detects UTF‑8 and GBK encoding.

```bash
curl "http://127.0.0.1:8765/api/readfile?path=C:\\readme.txt"
```

### Create Folder

```
POST /api/mkdir
```

| Parameter | Description |
|-----------|-------------|
| path | Path of the directory to create |

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
| path | Path of the file or directory to delete |
| recursive | Whether to delete contents recursively when deleting a directory |

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

## Lanzou Cloud Download

```
POST /api/lanzou/download
```

Parse a Lanzou sharing link and download the file.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| url | string | Yes | Lanzou sharing link |
| pwd | string | No | Extraction password; leave empty if none |
| save_path | string | No | Save path; if not provided, saves to the downloads/ directory |

```bash
curl -X POST http://127.0.0.1:8765/api/lanzou/download \
  -H "Content-Type: application/json" \
  -d '{"url":"https://xxx.lanzouw.com/xxxxx","pwd":"h0fv"}'
```
> [!IMPORTANT]
> The API service is provided by a third‑party interface.
>
> It is not affiliated with this project.
>
> Thanks to
> [https://api.bugpk.com/](https://api.bugpk.com/doc-lanzou.html)
> for providing the parsing service.

---

## System Information

```
GET /api/sysinfo
```

Returns operating system version, CPU core count, memory size, etc. If the `psutil` library is not installed, only basic OS name is returned.

```bash
curl http://127.0.0.1:8765/api/sysinfo
```

---

## View Logs

```
GET /api/log?lines={lines}
```

Get the most recent N lines of logs; default is 100 lines.

```bash
curl "http://127.0.0.1:8765/api/log?lines=50"
```

---

## Companion Frontend Pages

The project includes two HTML pages – open them in a browser and use them directly:

- **Console** — an interface for all functions, convenient for testing
- **Developer Documentation** — API documentation with online testing tools

These pages are located in the `web/` directory. Open them directly with your browser.

---

## Running from Source

If you prefer not to use the .exe, run the Python script directly:

```bash
# Install dependencies
pip install flask flask-cors pystray pillow
```

If using the .exe, use the pre‑built package or package it manually.

---

## About Security

The service **by default** listens only on `127.0.0.1`, meaning only the local machine can access it. This enhances security.
> [!WARNING]
> It is not recommended to expose the HTTP interface unless in an intranet environment or with sufficient security measures.

> [!CAUTION]
> If you change the binding address yourself, or expose the service via tools like ngrok, it is strongly recommended to add an authentication layer in front.

> [!IMPORTANT]
> The developer HXZXS assumes no responsibility for any issues of any kind.

---

## License

Apache License 2.0

> [!TIP]
> When distributing, please credit the original author HXZXS.

[LICENSE](https://github.com/HXZXS/Better-JavaScript/blob/main/LICENSE)

---
## About

*Translation provided by Deepseek.*
