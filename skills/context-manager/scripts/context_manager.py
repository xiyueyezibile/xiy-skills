#!/usr/bin/env python3
"""Local WebSocket context editor and context reader."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mimetypes
import os
import socket
import struct
import threading
import uuid
import webbrowser
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


DEFAULT_PORT = 8765
DEFAULT_DATA_DIR = Path.home() / ".context-manage"
MAX_IMAGE_BYTES = 20 * 1024 * 1024
HTML_PAGE = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Context Manager</title><style>
:root{font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#16202b;background:#eef2f6}
*{box-sizing:border-box}body{max-width:1080px;margin:0 auto;padding:34px 24px 64px}
.topbar{display:flex;align-items:center;justify-content:space-between;gap:20px;margin-bottom:42px}
.brand{display:flex;align-items:center;gap:12px}.mark{width:38px;height:38px;display:grid;place-items:center;border-radius:12px;background:#1d2939;color:#fff;font-weight:800;box-shadow:0 8px 18px #1d29391f}
h1{font-size:18px;letter-spacing:-.02em;margin:0}.eyebrow{font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:#64748b;margin:0 0 2px}
.connection{display:flex;align-items:center;gap:8px;color:#64748b;font-size:12px}.dot{width:8px;height:8px;border-radius:50%;background:#f59e0b}.dot.online{background:#22c55e}
.intro{max-width:700px;margin-bottom:24px}.intro h2{font-size:42px;line-height:1.08;letter-spacing:-.055em;margin:0 0 12px;color:#101828}.intro p{font-size:16px;color:#667085;margin:0}
.workspace{display:grid;grid-template-columns:minmax(0,1.02fr) minmax(300px,.98fr);gap:22px;align-items:start}
.composer,.items-panel{background:#fff;border:1px solid #dfe5ec;border-radius:18px;box-shadow:0 14px 34px #1d29390c}
.composer{padding:22px}.panel-head{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:18px}.panel-title{font-size:15px;font-weight:700;margin:0}.panel-note{font-size:12px;color:#98a2b3;margin:3px 0 0}.count{font-size:12px;color:#667085;background:#f2f4f7;border-radius:999px;padding:5px 9px;white-space:nowrap}
.field-label{display:block;color:#667085;font-size:12px;font-weight:600;margin:0 0 7px}.title-input{width:100%;margin-bottom:14px}
button,input,textarea{font:inherit;border:1px solid #d0d5dd;border-radius:10px;background:#fff;padding:10px 12px;color:#16202b;outline:none;transition:border-color .18s,box-shadow .18s,transform .18s}
input:focus,textarea:focus{border-color:#4b8df8;box-shadow:0 0 0 4px #4b8df81c}
button{cursor:pointer;background:#2268d8;border-color:#2268d8;color:#fff;font-weight:650}button:hover{transform:translateY(-1px);background:#1858be}
button.secondary{background:#f8fafc;border-color:#dfe5ec;color:#344054}button.secondary:hover{background:#eef4ff;border-color:#b6cffc;color:#1858be}
.title-input,textarea{display:block;width:100%}textarea{min-height:190px;resize:vertical}.composer-actions{display:flex;gap:10px;justify-content:space-between;align-items:center;margin-top:14px}.action-group{display:flex;gap:9px;flex-wrap:wrap}
.hint{font-size:12px;color:#98a2b3}.items-panel{padding:22px}.items-list{display:grid;gap:10px}
.item{background:#fbfcfe;border:1px solid #e6ebf1;border-radius:13px;padding:15px 16px;transition:border-color .18s,box-shadow .18s}.item:hover{border-color:#b7cdf3;box-shadow:0 7px 18px #2268d80d}
.item header{display:flex;justify-content:space-between;gap:10px;align-items:start}.item h3{font-size:14px;margin:0;color:#1d2939}.item .meta{font-size:11px;color:#98a2b3;margin:5px 0 10px}.item p{white-space:pre-wrap;color:#475467;margin:0}.item img{display:block;max-width:100%;max-height:360px;margin-top:8px;border-radius:9px}.delete{padding:5px 8px;font-size:11px}
.item.archived{background:#f8fafc;opacity:.78}.item-actions{display:flex;gap:6px}.item-actions button{padding:5px 8px;font-size:11px}
.empty{padding:34px 20px;text-align:center;color:#98a2b3;border:1px dashed #d0d5dd;border-radius:12px}.empty strong{display:block;color:#667085;margin-bottom:4px}
@media(max-width:760px){body{padding:22px 16px 42px}.topbar{margin-bottom:30px}.intro h2{font-size:34px}.workspace{grid-template-columns:1fr}.composer,.items-panel{border-radius:15px}.composer-actions{align-items:flex-start;flex-direction:column}.hint{order:2}}
</style></head><body><header class="topbar"><div class="brand"><div class="mark">C</div><div><p class="eyebrow">Workspace</p><h1>上下文管理</h1></div></div><div class="connection"><span class="dot" id="statusDot"></span><span id="statusText">连接中</span></div></header>
<section class="intro"><h2>把重要上下文，<br>留在下一次对话之前。</h2><p>把任务、约束和参考图片拆成独立条目保存。每次对话前，AI 会按条读取这些内容。</p></section>
<section class="workspace"><section class="composer"><div class="panel-head"><div><p class="panel-title">新增上下文</p><p class="panel-note">每次提交都会创建一条独立记录</p></div><span class="count" id="count">0 条</span></div><label class="field-label" for="title">条目标题</label><input class="title-input" id="title" placeholder="例如：本周要完成的事项"><label class="field-label" for="draft">内容</label><textarea id="draft" placeholder="输入任务、约束或资料……"></textarea><div class="composer-actions"><span class="hint">支持文字 / TODO 与图片</span><div class="action-group"><button id="addText">添加文字</button><label><button class="secondary" id="pick">添加图片</button><input id="file" type="file" accept="image/*" hidden></label></div></div></section><section class="items-panel"><div class="panel-head"><div><p class="panel-title">已启用条目</p><p class="panel-note">只有启用内容会注入 AI</p></div><span class="count" id="savedLabel">暂无</span></div><main class="items-list" id="list"></main><div class="panel-head" style="margin:24px 0 12px"><div><p class="panel-title">历史条目</p><p class="panel-note">停用后保留，可一键复用</p></div><span class="count" id="historyLabel">暂无</span></div><main class="items-list" id="history"></main></section></section>
<script>
const list=document.querySelector('#list'), history=document.querySelector('#history'), title=document.querySelector('#title'), draft=document.querySelector('#draft'), file=document.querySelector('#file');
const ws=new WebSocket(`ws://${location.host}/ws`);
function send(action){ws.send(JSON.stringify(action))}
function esc(v){return String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function card(i,n,archived){return `<article class="item${archived?' archived':''}"><header><h3>条目 ${n+1}：${esc(i.title||'未命名')}</h3><div class="item-actions">${archived?`<button class="secondary" data-reuse="${i.id}">复用</button>`:`<button class="secondary" data-toggle="${i.id}">停用</button>`}</div></header><div class="meta">${i.kind==='image'?'图片':'文字 / TODO'} · ${archived?'历史条目':'已启用'} · ${esc(i.updated_at||i.created_at||'')}</div>${i.kind==='image'?`<img src="${i.url}" alt="${esc(i.title||'上下文图片')}"><p>${esc(i.mime_type||'image')}</p>`:`<p>${esc(i.content)}</p>`}</article>`}
function render(items){const active=items.filter(i=>i.enabled!==false), archived=items.filter(i=>i.enabled===false);document.querySelector('#count').textContent=`${active.length} 条`;document.querySelector('#savedLabel').textContent=active.length?`${active.length} 条记录`:'暂无';document.querySelector('#historyLabel').textContent=archived.length?`${archived.length} 条`:'暂无';list.innerHTML=active.length?active.map((i,n)=>card(i,n,false)).join(''):'<div class="empty"><strong>还没有启用条目</strong>从左侧添加第一条任务或资料。</div>';history.innerHTML=archived.length?archived.map((i,n)=>card(i,n,true)).join(''):'<div class="empty"><strong>暂无历史条目</strong>停用的内容会保留在这里。</div>'}
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.type==='state')render(m.items);if(m.type==='error')alert(m.message)}
ws.onopen=()=>{document.querySelector('#statusDot').classList.add('online');document.querySelector('#statusText').textContent='已连接';send({action:'get_state'})};ws.onclose=()=>{document.querySelector('#statusDot').classList.remove('online');document.querySelector('#statusText').textContent='连接已断开'}; document.querySelector('#addText').onclick=()=>{if(!draft.value.trim())return;send({action:'add_text',title:title.value,content:draft.value});draft.value='';title.value=''}
document.querySelector('#pick').onclick=()=>file.click(); file.onchange=()=>{const f=file.files[0];if(!f)return;if(f.size>20*1024*1024)return alert('图片不能超过 20MB');const r=new FileReader();r.onload=()=>send({action:'add_image',title:title.value||f.name,mime_type:f.type,data_url:r.result});r.readAsDataURL(f);file.value='';title.value=''}
list.onclick=e=>{const id=e.target.dataset.toggle;if(id)send({action:'set_enabled',id,enabled:false})}
history.onclick=e=>{const id=e.target.dataset.reuse;if(id)send({action:'set_enabled',id,enabled:true})}
</script></body></html>"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ContextStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.image_dir = root / "images"
        self.file = root / "context.json"
        self.lock = threading.RLock()
        self.root.mkdir(parents=True, exist_ok=True)
        self.image_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        with self.lock:
            if not self.file.exists():
                return {"version": 1, "updated_at": now(), "items": []}
            try:
                value = json.loads(self.file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise RuntimeError(f"无法读取上下文文件: {exc}") from exc
            if not isinstance(value, dict) or not isinstance(value.get("items"), list):
                raise RuntimeError("上下文文件格式无效")
            for item in value["items"]:
                if isinstance(item, dict):
                    item.setdefault("enabled", True)
            return value

    def save(self, state: dict[str, Any]) -> None:
        with self.lock:
            state["updated_at"] = now()
            temp = self.file.with_suffix(".tmp")
            temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
            temp.replace(self.file)

    def add_text(self, title: str, content: str) -> dict[str, Any]:
        if not content.strip():
            raise ValueError("文字内容不能为空")
        state = self.load()
        item = {"id": uuid.uuid4().hex, "kind": "text", "title": title.strip(), "content": content,
                "created_at": now(), "updated_at": now(), "enabled": True}
        state["items"].append(item)
        self.save(state)
        return item

    def add_image(self, title: str, mime_type: str, data_url: str) -> dict[str, Any]:
        prefix = f"data:{mime_type};base64,"
        if not data_url.startswith(prefix):
            raise ValueError("图片必须是匹配 MIME 类型的 Data URL")
        try:
            raw = base64.b64decode(data_url[len(prefix):], validate=True)
        except (ValueError, base64.binascii.Error) as exc:
            raise ValueError("图片数据无效") from exc
        if len(raw) > MAX_IMAGE_BYTES:
            raise ValueError("图片不能超过 20MB")
        suffix = mimetypes.guess_extension(mime_type) or ".bin"
        image_name = f"{uuid.uuid4().hex}{suffix}"
        (self.image_dir / image_name).write_bytes(raw)
        state = self.load()
        item = {"id": uuid.uuid4().hex, "kind": "image", "title": title.strip() or image_name,
                "mime_type": mime_type, "path": str(self.image_dir / image_name),
                "created_at": now(), "updated_at": now(), "enabled": True}
        state["items"].append(item)
        self.save(state)
        return item

    def delete(self, item_id: str) -> None:
        self.set_enabled(item_id, False)

    def set_enabled(self, item_id: str, enabled: bool) -> None:
        state = self.load()
        for item in state["items"]:
            if item.get("id") == item_id:
                item["enabled"] = enabled
                item["updated_at"] = now()
        self.save(state)

    def markdown(self) -> str:
        state = self.load()
        active_items = [item for item in state["items"] if item.get("enabled", True)]
        lines = ["# Context Manager 上下文", f"- 启用条目数：{len(active_items)}", f"- 更新时间：{state.get('updated_at', 'unknown')}"]
        if not active_items:
            lines.append("\n## 暂无条目")
            lines.append("- 当前没有启用的上下文。")
        for index, item in enumerate(active_items, start=1):
            title = str(item.get("title") or "未命名").replace("\n", " ")
            kind = "图片" if item.get("kind") == "image" else "文字 / TODO"
            lines.extend(["", f"## 条目 {index}：{title}", f"- 类型：{kind}", f"- 更新时间：{item.get('updated_at', item.get('created_at', 'unknown'))}"])
            if item.get("kind") == "image":
                lines.append(f"- MIME：`{item.get('mime_type', 'image')}`")
                lines.append(f"- 图片路径：`file://{item.get('path', '')}`")
            else:
                lines.append("- 状态：待处理")
                lines.append(f"- 内容：\n\n{item.get('content', '')}")
        return "\n".join(lines)

    def public_items(self) -> list[dict[str, Any]]:
        state = self.load()
        result = []
        for item in state["items"]:
            copy = dict(item)
            if copy.get("kind") == "image":
                copy["url"] = "/images/" + Path(str(copy["path"])).name
            result.append(copy)
        return result


def ws_frame(payload: str) -> bytes:
    data = payload.encode("utf-8")
    length = len(data)
    if length < 126:
        header = struct.pack("!BB", 0x81, length)
    elif length < 65536:
        header = struct.pack("!BBH", 0x81, 126, length)
    else:
        header = struct.pack("!BBQ", 0x81, 127, length)
    return header + data


def ws_read(sock: socket.socket) -> str | None:
    try:
        header = sock.recv(2)
    except OSError:
        return None
    if len(header) < 2:
        return None
    first, second = header
    opcode = first & 0x0F
    length = second & 0x7F
    masked = bool(second & 0x80)
    if length == 126:
        length = struct.unpack("!H", sock.recv(2))[0]
    elif length == 127:
        length = struct.unpack("!Q", sock.recv(8))[0]
    mask = sock.recv(4) if masked else b""
    data = bytearray()
    while len(data) < length:
        try:
            chunk = sock.recv(length - len(data))
        except OSError:
            return None
        if not chunk:
            return None
        data.extend(chunk)
    if masked:
        data = bytearray(byte ^ mask[index % 4] for index, byte in enumerate(data))
    if opcode == 8:
        return None
    if opcode == 9:
        sock.sendall(struct.pack("!BB", 0x8A, len(data)) + data)
        return ""
    return data.decode("utf-8")


class App:
    def __init__(self, store: ContextStore) -> None:
        self.store = store
        self.clients: set[socket.socket] = set()
        self.lock = threading.RLock()

    def broadcast(self) -> None:
        message = json.dumps({"type": "state", "items": self.store.public_items()}, ensure_ascii=False)
        frame = ws_frame(message)
        with self.lock:
            dead = []
            for client in self.clients:
                try:
                    client.sendall(frame)
                except OSError:
                    dead.append(client)
            for client in dead:
                self.clients.discard(client)

    def handle_ws(self, sock: socket.socket, headers: str) -> None:
        key = next((line.split(":", 1)[1].strip() for line in headers.splitlines()
                    if line.lower().startswith("sec-websocket-key:")), "")
        accept = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()).decode()
        sock.sendall(("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                      f"Sec-WebSocket-Accept: {accept}\r\n\r\n").encode())
        with self.lock:
            self.clients.add(sock)
        try:
            while True:
                raw = ws_read(sock)
                if raw is None:
                    break
                if not raw:
                    continue
                try:
                    message = json.loads(raw)
                    action = message.get("action")
                    if action == "get_state":
                        response = {"type": "state", "items": self.store.public_items()}
                        sock.sendall(ws_frame(json.dumps(response, ensure_ascii=False)))
                    elif action == "add_text":
                        self.store.add_text(str(message.get("title", "")), str(message.get("content", "")))
                        self.broadcast()
                    elif action == "add_image":
                        self.store.add_image(str(message.get("title", "")), str(message.get("mime_type", "")),
                                             str(message.get("data_url", "")))
                        self.broadcast()
                    elif action == "set_enabled":
                        self.store.set_enabled(str(message.get("id", "")), bool(message.get("enabled", False)))
                        self.broadcast()
                    elif action == "delete":
                        self.store.delete(str(message.get("id", "")))
                        self.broadcast()
                except (ValueError, RuntimeError, json.JSONDecodeError) as exc:
                    sock.sendall(ws_frame(json.dumps({"type": "error", "message": str(exc)}, ensure_ascii=False)))
        finally:
            with self.lock:
                self.clients.discard(sock)
            sock.close()


def handle_http(sock: socket.socket, request: str, app: App) -> None:
    request_line = request.splitlines()[0] if request.splitlines() else ""
    parts = request_line.split()
    path = urlparse(parts[1]).path if len(parts) >= 2 else "/"
    if path == "/":
        body = HTML_PAGE.encode("utf-8")
        response = (f"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n"
                    f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n").encode() + body
        sock.sendall(response)
        sock.close()
        return
    if path.startswith("/images/"):
        name = Path(path.removeprefix("/images/")).name
        image_path = app.store.image_dir / name
        if image_path.is_file():
            body = image_path.read_bytes()
            content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
            response = (f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\n"
                        f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n").encode() + body
            sock.sendall(response)
        else:
            sock.sendall(b"HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n")
        sock.close()
        return
    if path == "/api/context":
        body = json.dumps({"items": app.store.public_items()}, ensure_ascii=False).encode("utf-8")
        response = (f"HTTP/1.1 200 OK\r\nContent-Type: application/json; charset=utf-8\r\n"
                    f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n").encode() + body
        sock.sendall(response)
        sock.close()
        return
    sock.sendall(b"HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n")
    sock.close()


class RequestHandler(BaseHTTPRequestHandler):
    app: App

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
            return
        if parsed.path.startswith("/images/"):
            name = Path(parsed.path.removeprefix("/images/")).name
            path = self.app.store.image_dir / name
            if not path.is_file():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", mimetypes.guess_type(name)[0] or "application/octet-stream")
            self.end_headers()
            self.wfile.write(path.read_bytes())
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, format_string: str, *args: object) -> None:
        return


class WebSocketServer(ThreadingHTTPServer):
    def get_request(self) -> tuple[socket.socket, Any]:
        sock, address = super().get_request()
        return sock, address


def serve(store: ContextStore, port: int, open_browser: bool) -> None:
    app = App(store)
    class Handler(RequestHandler):
        pass
    Handler.app = app
    server = WebSocketServer(("127.0.0.1", port), Handler)

    def accept_loop() -> None:
        while True:
            sock, _ = server.socket.accept()
            sock.settimeout(None)
            request = b""
            while b"\r\n\r\n" not in request:
                chunk = sock.recv(4096)
                if not chunk:
                    sock.close()
                    continue
                request += chunk
            headers = request.decode("iso-8859-1")
            if "Upgrade: websocket" in headers or "upgrade: websocket" in headers:
                threading.Thread(target=app.handle_ws, args=(sock, headers), daemon=True).start()
            else:
                threading.Thread(target=handle_http, args=(sock, headers, app), daemon=True).start()

    threading.Thread(target=accept_loop, daemon=True).start()
    url = f"http://127.0.0.1:{port}"
    print(f"Context Manager running at {url}")
    if open_browser:
        webbrowser.open(url)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Local context manager")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("read")
    read_json = subparsers.choices["read"].add_argument
    read_json("--format", choices=("markdown", "json"), default="markdown")
    start = subparsers.add_parser("start")
    start.add_argument("--port", type=int, default=DEFAULT_PORT)
    start.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    store = ContextStore(args.data_dir)
    if args.command == "read":
        if args.format == "json":
            print(json.dumps(store.load(), ensure_ascii=False, indent=2))
        else:
            print(store.markdown())
        return
    serve(store, args.port, not args.no_browser)


if __name__ == "__main__":
    main()
