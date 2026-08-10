```markdown
# BJS Data Relay

Connect web pages with local programs.

---

## What is this for?

Browsers run web pages, but they cannot directly access local files, show system dialogs, or run local programs by default.

BJS Data Relay solves this. It runs an HTTP service on the local machine. Web pages send requests, the service executes the corresponding local operations, and returns results to the web pages.

So you can:

- Open a folder on your computer from a web page
- Show a real system window from a web page
- Launch programs installed on your computer from a web page
- Browse, create, delete, copy, and move files using a web page
- Parse Lanzou cloud sharing links and download files from a web page
- ...and more

---

## Quick Start

### Download

Go to the [Releases](https://github.com/HXZXS/Better-JavaScript/releases) page and download the latest `bjs_relay.exe`. You can also run the Python source directly (see instructions below).

### Run

Double-click `bjs_relay.exe`, follow the installation steps, and wait for the program to start.
By default it listens on `127.0.0.1:8765`. Visit `http://127.0.0.1:8765/health` in your browser – if you see `{"code":0,"status":"running"}`, everything is working.

### Files Created

The following files and directories will be created in the program's folder:

| File/Directory | Description |
|----------------|-------------|
| `bjs.log` | Runtime log – check this first if something goes wrong |
| `logo.ico` | Tray icon; replace with your own, otherwise the default icon is used |
| `downloads/` | Default folder for files downloaded from Lanzou |

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

`code` is `0` on success, `-1` on failure. The actual response content varies per endpoint – see each endpoint's description.

### Health Check

```
GET /health
```

Check if the service is running.

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
| type | string | No | See below, default `info` |
| image | string | No | Image URL or local path |
| width | int | No | Window width in image mode |
| height | int | No | Window height in image mode |

Valid `type` values:

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
| args | string | No | Command-line arguments, space-separated |
| wait | bool | No | Whether to wait for the program to exit, default `false` |

```bash
curl -X POST http://127.0.0.1:8765/api/run \
  -H "Content-Type: application/json" \
  -d '{"path":"notepad.exe","args":"readme.txt"}'
```

When `wait` is `true`, the response includes the program's output:

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

Create a dialog with multiple controls using JSON configuration – suitable for collecting user input.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| config | string | Yes | JSON string describing the dialog layout |

**Configuration format:**

```json
{
  "title": "Dialog Title",
  "width": 500,
  "height": 400,
  "controls": [
    {"type": "label", "text": "A line of description"},
    {"type": "entry", "label": "Name", "id": "name", "default": "John Doe"},
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
| `entry` | Single-line input |
| `text` | Multi-line text input |
| `password` | Password input |
| `combobox` | Drop-down selection |
| `checkbox` | Multiple-choice checkboxes |
| `radio` | Radio buttons (single choice) |
| `progress` | Progress bar |
| `image` | Display an image |

Example call:

```bash
curl -X POST http://127.0.0.1:8765/api/dialog \
  -H "Content-Type: application/json" \
  -d '{"config":"{\"title\":\"Edit Info\",\"controls\":[{\"type\":\"entry\",\"label\":\"Name\",\"id\":\"name\"}],\"buttons\":[\"Save\"]}"}'
```

The response includes the button clicked and the values entered:

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

Automatically detects UTF-8 and GBK encoding.

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
| path | File or directory path to delete |
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

## Lanzou Cloud Download

```
POST /api/lanzou/download
```

Parse a Lanzou sharing link and download the file.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| url | string | Yes | Lanzou sharing link |
| pwd | string | No | Extraction password; leave empty if none |
| save_path | string | No | Save path; defaults to `downloads/` directory |

```bash
curl -X POST http://127.0.0.1:8765/api/lanzou/download \
  -H "Content-Type: application/json" \
  -d '{"url":"https://xxx.lanzouw.com/xxxxx","pwd":"h0fv"}'
```

---

## System Information

```
GET /api/sysinfo
```

Returns OS version, CPU cores, memory size, etc. If `psutil` is not installed, only basic system name is returned.

```bash
curl http://127.0.0.1:8765/api/sysinfo
```

---

## View Logs

```
GET /api/log?lines={lines}
```

Get the last N lines of logs – default 100 lines.

```bash
curl "http://127.0.0.1:8765/api/log?lines=50"
```

---

## Included Frontend Pages

The project includes two HTML pages in the `web/` directory – open them directly in your browser:

- **Console** – Interface for all features, handy for testing
- **Developer Documentation** – API documentation with online testing tools

---

## Running from Source

If you prefer not to use the executable, run the Python script directly:

```bash
# Install dependencies
pip install flask flask-cors pystray pillow

# Start
python bjs_relay.py
```

If you use the executable, use the pre-built package or package it manually.

---

## Security Notes

The service binds only to `127.0.0.1` by default, so only the local machine can access it – this is the recommended configuration.

If you change the bind address or expose the service via tunneling tools, consider adding an authentication layer in front.

---

## License

MIT License

Copyright (c) 2026 HXZXS

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
