import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DEDSECAI_HOME',str(Path(__file__).resolve().parents[1]/'.test-data'))
import hardware
import desktop


class WindowsCompatibilityTests(unittest.TestCase):
    def test_decimal_temperature_and_missing_sensors_preserve_vram(self):
        for sensors,expected in [('1,44.22',44.22),('[N/A],[N/A]',None)]:
            def command(args,**kwargs):
                return 'Test GPU,12288,11070,'+sensors if args[0]=='nvidia-smi' else ''
            with patch.object(hardware,'command',side_effect=command):
                gpu=hardware.detect(refresh=True)['gpus'][0]
                self.assertEqual(gpu['vram_bytes'],12*1024**3)
                self.assertEqual(gpu['temp'],expected)

    @unittest.skipUnless(os.name=='nt','Windows console')
    def test_pythonw_launches_console_python_with_literal_project_path(self):
        with patch.object(desktop.sys,'executable',r'C:\Python\pythonw.exe'),patch.object(desktop.subprocess,'Popen') as popen:
            desktop.launch_pi(r'C:\Projects\тест & example')
            args=popen.call_args.args[0]
            self.assertEqual(args[0],r'C:\Python\python.exe')
            self.assertEqual(args[-1],r'C:\Projects\тест & example')
            self.assertEqual(popen.call_args.kwargs['creationflags'],desktop.subprocess.CREATE_NEW_CONSOLE)

    @unittest.skipUnless(os.name=='nt','Windows Pi launcher')
    def test_managed_pi_uses_node_directly(self):
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder);entry=home/'.pi/agent/bin/pi-launcher.js'
            entry.parent.mkdir(parents=True);entry.touch()
            with patch.object(desktop,'HOME',home),patch.object(desktop,'APP_HOME',home/'studio'),patch.object(desktop.shutil,'which',side_effect=lambda name:'node.exe' if name=='node' else None):
                self.assertEqual(desktop.pi_command(),['node.exe',str(entry)])

if __name__=='__main__':unittest.main()
