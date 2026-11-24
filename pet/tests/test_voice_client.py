"""Real loopback transport cancellation; no model, credential, or microphone."""
import pathlib
import http.client
import socket
import sys
import threading
import unittest

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'python'))
from shared_voice_client import CancellableConnection


class ClientCancellationTests(unittest.TestCase):
    def test_cancel_before_connect_never_opens_socket(self):
        stop = threading.Event()
        stop.set()
        client = CancellableConnection(stop)
        with self.assertRaises(InterruptedError):
            client.request('POST','/speech',body=b'{}')
        self.assertIsNone(client.sock)

    def check_transport(self, headers):
        listener = socket.socket()
        listener.bind(('127.0.0.1',0))
        listener.listen()
        listener.settimeout(2)
        started, finished = threading.Event(), threading.Event()
        stop = threading.Event()
        errors = []
        client = CancellableConnection(stop,port=listener.getsockname()[1])

        def server():
            with listener.accept()[0] as connection:
                connection.settimeout(2)
                received = b''
                while b'\r\n\r\n' not in received:
                    received += connection.recv(4096)
                if headers:
                    connection.sendall(b'HTTP/1.0 200 OK\r\nContent-Length: 1000\r\n\r\n')
                started.set()
                while connection.recv(4096):
                    pass

        def request():
            try:
                client.request('POST','/speech',body=b'{}')
                client.getresponse().read()
            except (OSError, EOFError, http.client.HTTPException):
                errors.append(True)
            finally:
                client.close()
                finished.set()

        serving, requesting = threading.Thread(target=server), threading.Thread(target=request)
        serving.start()
        requesting.start()
        try:
            self.assertTrue(started.wait(2))
            if headers:
                # Let getresponse transfer socket ownership to its response file.
                finished.wait(.05)
            stop.set()
            client.interrupt()
            self.assertTrue(finished.wait(1))
        finally:
            client.interrupt()
            listener.close()
            serving.join(3)
            requesting.join(3)
        self.assertFalse(requesting.is_alive())
        self.assertTrue(errors)

    def test_cancel_while_waiting_for_headers(self):
        self.check_transport(False)

    def test_cancel_while_waiting_for_body(self):
        self.check_transport(True)


if __name__ == '__main__':
    unittest.main()
