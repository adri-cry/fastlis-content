#!/usr/bin/env python3
"""Screenshot file HTML lokal via Chrome DevTools Protocol (stdlib only).

Kenapa CDP: flag --screenshot chrome kadang gagal diam-diam (file lama
dianggap OK = false positive). Lewat CDP kita tahu pasti capture berhasil.

Pakai: cdp_shot.py <file.html> <out.png> [width] [height]
"""
import base64
import hashlib
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import time
import urllib.request


def find_chrome():
    cands = []
    env = os.environ.get("FASTLIS_CHROME")
    if env:
        cands.append(env)
    cands += [
        os.path.expanduser("~/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome"),
        "/opt/meta-chromium/chrome",
        "/opt/chrome/chrome-linux64/chrome",
    ]
    for c in cands:
        if c and os.path.exists(c) and os.access(c, os.X_OK):
            return c
    return None


def free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class WSClient:
    """WebSocket client minimal (stdlib): handshake + kirim/terima frame."""

    def __init__(self, url):
        # url: ws://127.0.0.1:PORT/devtools/page/XXX
        assert url.startswith("ws://")
        host_path = url[5:]
        host, path = host_path.split("/", 1)
        self.host = host
        self.path = "/" + path
        self.sock = socket.create_connection((host.split(":")[0], int(host.split(":")[1])), timeout=30)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (
            f"GET {self.path} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(req.encode())
        resp = b""
        while b"\r\n\r\n" not in resp:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise RuntimeError("handshake gagal")
            resp += chunk
        if b"101" not in resp.split(b"\r\n", 1)[0]:
            raise RuntimeError(f"handshake ditolak: {resp[:80]}")

    def _send_frame(self, data: bytes):
        # client->server: masked, single frame, opcode text(0x1)
        mask = os.urandom(4)
        n = len(data)
        hdr = bytearray([0x81])
        if n < 126:
            hdr.append(0x80 | n)
        elif n < 65536:
            hdr.append(0x80 | 126)
            hdr += struct.pack(">H", n)
        else:
            hdr.append(0x80 | 127)
            hdr += struct.pack(">Q", n)
        hdr += mask
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        self.sock.sendall(bytes(hdr) + masked)

    def _recv_exact(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise RuntimeError("koneksi WS putus")
            buf += chunk
        return buf

    def recv_msg(self, timeout=60):
        self.sock.settimeout(timeout)
        payload = b""
        while True:
            hdr = self._recv_exact(2)
            fin = hdr[0] & 0x80
            opcode = hdr[0] & 0x0F
            ln = hdr[1] & 0x7F
            if ln == 126:
                ln = struct.unpack(">H", self._recv_exact(2))[0]
            elif ln == 127:
                ln = struct.unpack(">Q", self._recv_exact(8))[0]
            # server->client tidak masked
            data = self._recv_exact(ln) if ln else b""
            if opcode == 0x8:
                raise RuntimeError("WS ditutup server")
            payload += data
            if fin:
                return payload.decode("utf-8", errors="replace")

    def send_json(self, obj):
        self._send_frame(json.dumps(obj).encode())

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


def http_json(url, data=None, method=None, timeout=15):
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


class ShotSession:
    """Satu Chrome dipakai ulang untuk banyak capture (jauh lebih cepat)."""

    def __init__(self, width=1080, height=1350):
        chrome = find_chrome()
        if not chrome:
            raise RuntimeError("chrome tidak ketemu")
        self.width, self.height = width, height
        self.port = free_port()
        self.profile = f"/tmp/cdp-shot-{os.getpid()}"
        self.proc = subprocess.Popen(
            [chrome, "--headless=new", "--no-sandbox", "--disable-gpu",
             "--disable-dev-shm-usage", "--no-first-run",
             f"--remote-debugging-port={self.port}", f"--user-data-dir={self.profile}",
             f"--window-size={width},{height}", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            try:
                http_json(f"http://127.0.0.1:{self.port}/json/version")
                break
            except Exception:
                time.sleep(0.5)
        else:
            self.close()
            raise RuntimeError("DevTools tidak siap")
        target = http_json(f"http://127.0.0.1:{self.port}/json/new?about:blank", method="PUT")
        self.ws = WSClient(target["webSocketDebuggerUrl"])
        self.mid = 0
        self._call("Page.enable")
        self._call("Emulation.setDeviceMetricsOverride",
                   {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": False})

    def _call(self, method, params=None):
        self.mid += 1
        i = self.mid
        self.ws.send_json({"id": i, "method": method, "params": params or {}})
        while True:
            msg = json.loads(self.ws.recv_msg())
            if msg.get("id") == i:
                if "error" in msg:
                    raise RuntimeError(f"CDP {method}: {msg['error']}")
                return msg.get("result", {})

    def capture(self, html, out, min_bytes=50000):
        if os.path.exists(out):
            os.remove(out)  # cegah false-positive file lama
        file_url = "file://" + os.path.abspath(html)
        self._call("Page.navigate", {"url": file_url})
        deadline = time.time() + 25
        while time.time() < deadline:
            self.mid += 1
            i = self.mid
            self.ws.send_json({"id": i, "method": "Runtime.evaluate",
                               "params": {"expression": "document.readyState"}})
            state = None
            while True:
                msg = json.loads(self.ws.recv_msg(timeout=30))
                if msg.get("id") == i:
                    state = msg.get("result", {}).get("result", {}).get("value")
                    break
            if state == "complete":
                break
            time.sleep(0.5)
        time.sleep(1.0)  # font lokal, cukup 1 detik
        res = self._call("Page.captureScreenshot", {"format": "png", "fromSurface": True})
        data = res.get("data")
        if not data:
            return False
        with open(out, "wb") as f:
            f.write(base64.b64decode(data))
        return os.path.exists(out) and os.path.getsize(out) > min_bytes

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()
        # bersihkan profile Chrome di /tmp (/tmp cuma 512MB!)
        try:
            shutil.rmtree(self.profile, ignore_errors=True)
        except Exception:
            pass


def main():
    args = sys.argv[1:]
    if args and args[0] == "--batch":
        # --batch jobs.json : [{"html":..,"out":..,"width":..,"height":..}]
        jobs = json.load(open(args[1]))
        sess = ShotSession()
        try:
            ok = True
            for jb in jobs:
                r = sess.capture(jb["html"], jb["out"])
                sz = os.path.getsize(jb["out"]) if os.path.exists(jb["out"]) else 0
                print(f"{os.path.basename(jb['out'])} {'OK' if r else 'FAIL'} {sz}", flush=True)
                ok = ok and r
            return 0 if ok else 1
        finally:
            sess.close()
    if len(args) < 2:
        print("pakai: cdp_shot.py <in.html> <out.png> [width] [height]  atau  --batch jobs.json")
        return 2
    html, out = args[0], args[1]
    width = int(args[2]) if len(args) > 2 else 1080
    height = int(args[3]) if len(args) > 3 else 1350
    sess = ShotSession(width, height)
    try:
        ok = sess.capture(html, out)
    finally:
        sess.close()
    sz = os.path.getsize(out) if os.path.exists(out) else 0
    print(f"screenshot {'OK' if ok else 'FAIL'} {sz}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
