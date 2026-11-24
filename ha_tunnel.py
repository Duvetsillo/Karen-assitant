"""Private HA-to-Core transport over the user's existing SSH connection.

The remote listener is a mode-0600 Unix socket inside HA's existing config
mount, not a TCP port. Only the already-authenticated conversation API uses it.
"""
import shlex
import subprocess
import threading


class HATunnel:
    def __init__(self, host='friday-datacenter'):
        self.host = host
        self.stopped = threading.Event()
        self.process = None
        self.last_error = None
        self.thread = None

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._run, name='KarenHAChannel', daemon=True)
        self.thread.start()

    def _run(self):
        flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        while not self.stopped.is_set():
            try:
                result = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5', self.host,
                                         'lxc-info -n 101 -pH'], capture_output=True, text=True, timeout=10, creationflags=flags, check=True)
                pid = result.stdout.strip()
                if not pid.isdigit() or int(pid) < 2:
                    raise ValueError('Invalid container PID')
                path = f'/proc/{pid}/root/opt/stacks/homeassistant/config/.storage/karen-core.sock'
                prepare = ("import os,socket,stat,sys; p=" + repr(path) + "; "
                    "\nif os.path.lexists(p):\n"
                    " assert stat.S_ISSOCK(os.stat(p).st_mode)\n"
                    " c=socket.socket(socket.AF_UNIX); c.settimeout(1)\n"
                    " try: c.connect(p)\n"
                    " except (ConnectionRefusedError,FileNotFoundError): os.unlink(p)\n"
                    " else: print('ACTIVE'); sys.exit(0)\n"
                    " finally: c.close()\n"
                    "print('READY')")
                ready = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5', self.host,
                    shlex.join(['python3', '-c', prepare])], capture_output=True, text=True, timeout=10, check=True, creationflags=flags)
                if ready.stdout.strip() == 'ACTIVE':
                    self.last_error = None
                    self.stopped.wait(10)
                    continue
                self.process = subprocess.Popen(['ssh', '-N', '-T', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5',
                    '-o', 'ExitOnForwardFailure=yes', '-o', 'ServerAliveInterval=20', '-o', 'ServerAliveCountMax=3',
                    '-o', 'StreamLocalBindMask=0177', '-o', 'StreamLocalBindUnlink=yes',
                    '-R', path + ':127.0.0.1:18793', self.host], stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
                # Unprivileged LXC root uses a mapped host UID. Keep 0600 and give
                # ownership to HA's config owner, rather than widening permissions.
                ownership = ("import os,stat,time; p=" + repr(path) + "; "
                    "parent=os.path.dirname(p); "
                    "\nfor _ in range(40):\n"
                    " if os.path.exists(p): break\n time.sleep(.1)\n"
                    "s=os.stat(p); assert stat.S_ISSOCK(s.st_mode); owner=os.stat(parent); "
                    "os.chown(p,owner.st_uid,owner.st_gid); os.chmod(p,0o600)")
                subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5', self.host,
                    shlex.join(['python3', '-c', ownership])], capture_output=True, timeout=10, check=True, creationflags=flags)
                self.last_error = None
                while not self.stopped.wait(1) and self.process.poll() is None:
                    pass
                if not self.stopped.is_set():
                    self.last_error = 'ssh_channel_lost'
            except (OSError, ValueError, subprocess.SubprocessError):
                self.last_error = 'ssh_channel_unavailable'
            finally:
                if self.process and self.process.poll() is None:
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                        self.process.wait()
            self.stopped.wait(10)

    def close(self):
        self.stopped.set()
        if self.process and self.process.poll() is None:
            self.process.terminate()
        if self.thread:
            self.thread.join(7)


if __name__ == '__main__':
    tunnel = HATunnel()
    tunnel.start()
    try:
        while not tunnel.stopped.wait(30):
            pass
    except KeyboardInterrupt:
        tunnel.close()
