"""Exercise the actual server entry point on Windows and Ubuntu CI runners."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request


class StartupTests(unittest.TestCase):
    def test_panel_starts_and_serves_hardware_without_models(self):
        root=Path(os.environ.get('DEDSECAI_TEST_APP',Path(__file__).resolve().parents[1]))
        with tempfile.TemporaryDirectory() as folder:
            with socket.socket() as sock:
                sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            env=dict(os.environ,DEDSECAI_HOME=folder,DEDSECAI_PANEL_PORT=str(port))
            with (Path(folder)/'startup.log').open('w+b') as log:
                process=subprocess.Popen([sys.executable,str(root/'cli.py'),'serve'],cwd=root,env=env,stdout=log,stderr=log)
                try:
                    deadline=time.monotonic()+30
                    while time.monotonic()<deadline:
                        try:
                            with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/state',timeout=2) as response:
                                state=json.load(response)
                            break
                        except (OSError,urllib.error.URLError):
                            if process.poll() is not None:break
                            time.sleep(.2)
                    else:state=None
                    if process.poll() is not None or 'state' not in locals() or state is None:
                        log.seek(0);self.fail(log.read().decode('utf-8','replace'))
                    self.assertIn('hardware',state)
                    self.assertGreater(state['hardware']['ram_bytes'],0)
                    with urllib.request.urlopen(f'http://127.0.0.1:{port}/',timeout=3) as response:
                        self.assertEqual(response.status,200)
                        self.assertIn(b'DedsecAI',response.read())
                finally:
                    process.terminate()
                    try:process.wait(timeout=10)
                    except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)

if __name__=='__main__':unittest.main()
