#!/usr/bin/python3
"""Native messaging host: relays JSON lines from ~/.ghosttab/<browser>.sock to the GhostTab extension."""
import itertools
import json
import os
import socket
import struct
import sys
import threading

BROWSER = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('chrome-extension') else 'chrome'
DIR = os.path.expanduser('~/.ghosttab')
SOCK = os.path.join(DIR, BROWSER + '.sock')
lock = threading.Lock()
waiting = {}
ids = itertools.count(1)


def send(obj):
    data = json.dumps(obj).encode()
    with lock:
        sys.stdout.buffer.write(struct.pack('<I', len(data)) + data)
        sys.stdout.buffer.flush()


def reader():
    while True:
        head = sys.stdin.buffer.read(4)
        if len(head) < 4:
            break
        msg = json.loads(sys.stdin.buffer.read(struct.unpack('<I', head)[0]))
        w = waiting.pop(msg.get('id'), None)
        if w:
            w[1] = msg
            w[0].set()
    try:
        os.unlink(SOCK)
    except OSError:
        pass
    os._exit(0)


def client(conn):
    try:
        f = conn.makefile('rwb')
        req = json.loads(f.readline())
        i = next(ids)
        w = waiting[i] = [threading.Event(), None]
        req['id'] = i
        send(req)
        w[0].wait(req.pop('timeout', 60))
        waiting.pop(i, None)
        f.write((json.dumps(w[1] or {'ok': False, 'e': 'timeout'}) + '\n').encode())
        f.flush()
    finally:
        conn.close()


def main():
    os.makedirs(DIR, exist_ok=True)
    try:
        os.unlink(SOCK)
    except OSError:
        pass
    srv = socket.socket(socket.AF_UNIX)
    srv.bind(SOCK)
    os.chmod(SOCK, 0o600)
    srv.listen(8)
    threading.Thread(target=reader, daemon=True).start()
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=client, args=(conn,), daemon=True).start()


if __name__ == '__main__':
    main()
