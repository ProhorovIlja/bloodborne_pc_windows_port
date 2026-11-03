#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V410 raw Windows/Linux HTTP socket tests for actual source-pinned YT directory.

No Redis, network beyond 127.0.0.1, shard secrets or owner credentials.
Uses YT's ORIGINAL serve()/make_handler() with minimal fictional call object.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import socket
import sys
import threading
import unittest

root=Path(os.environ.get("SHYT_V410_YT_CHECKOUT","")).resolve()
if not (root/"server"/"directory"/"directory.py").is_file():
    raise SystemExit("SHYT_V410_YT_CHECKOUT must identify checkout")
sys.path.insert(0,str(root/"server"/"directory"))
import directory as original_yt  # noqa: E402

class FictionalDirectory:
    def heartbeat(self,body):
        return {"accepted": True, "keys": sorted(body)}
    def claim_account(self,body):
        return {"ok": True}
    def invite(self,body):
        return {"ok": True}

class RealHttpDirectoryRegression(unittest.TestCase):
    def setUp(self):
        self.server=original_yt.serve(
            FictionalDirectory(),token="synthetic-local-only",
            port=0,host="127.0.0.1")
        self.thread=threading.Thread(
            target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.endpoint=("127.0.0.1",self.server.server_address[1])
    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
    def connect(self):
        return socket.create_connection(self.endpoint,timeout=3)
    @staticmethod
    def response(sock):
        sock.settimeout(3)
        chunks=[]
        while True:
            data=sock.recv(4096)
            if not data:break
            chunks.append(data)
            if sum(map(len,chunks))>16000:
                raise AssertionError("unexpected huge response")
        return b"".join(chunks)
    def test_unauthorized_401_is_not_sent_before_complete_body(self):
        body=json.dumps({"shard":"invented","count":2}).encode()
        with self.connect() as sock:
            sock.sendall(
                b"POST /v1/heartbeat HTTP/1.1\r\n"
                b"Host: localhost\r\n"
                b"Authorization: Bearer wrong\r\n"
                +f"Content-Length: {len(body)}\r\n\r\n".encode())
            sock.settimeout(0.2)
            with self.assertRaises(socket.timeout):
                sock.recv(1)
            sock.sendall(body)
            reply=self.response(sock)
        self.assertTrue(reply.startswith(b"HTTP/1.0 401"),reply[:140])
        self.assertIn(b'"token"',reply)
    def test_valid_authorized_heartbeat_still_works(self):
        body=b'{"shard":"invented"}'
        with self.connect() as sock:
            sock.sendall(
                b"POST /v1/heartbeat HTTP/1.1\r\n"
                b"Host: localhost\r\n"
                b"Authorization: Bearer synthetic-local-only\r\n"
                +f"Content-Length: {len(body)}\r\n\r\n".encode()+body)
            reply=self.response(sock)
        self.assertTrue(reply.startswith(b"HTTP/1.0 200"),reply[:140])
        self.assertIn(b'"accepted": true',reply)
    def test_negative_length_rejected_without_unbounded_read(self):
        with self.connect() as sock:
            sock.sendall(
                b"POST /v1/heartbeat HTTP/1.1\r\n"
                b"Host: localhost\r\nContent-Length: -1\r\n\r\n")
            reply=self.response(sock)
        self.assertTrue(reply.startswith(b"HTTP/1.0 400"),reply[:140])
    def test_malformed_length_rejected(self):
        with self.connect() as sock:
            sock.sendall(
                b"POST /v1/heartbeat HTTP/1.1\r\n"
                b"Host: localhost\r\nContent-Length: nonsense\r\n\r\n")
            reply=self.response(sock)
        self.assertTrue(reply.startswith(b"HTTP/1.0 400"),reply[:140])
    def test_oversize_input_still_refused_without_reading_body(self):
        with self.connect() as sock:
            sock.sendall(
                b"POST /v1/heartbeat HTTP/1.1\r\n"
                b"Host: localhost\r\n"
                +f"Content-Length: {original_yt.BODY_MAX+1}\r\n\r\n".encode())
            reply=self.response(sock)
        self.assertTrue(reply.startswith(b"HTTP/1.0 413"),reply[:140])

if __name__=="__main__":
    unittest.main(verbosity=2)
