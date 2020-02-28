import pytest

import os
import select
import subprocess
import signal
import sys
import time

ACCOUNT = 'kumul.us'
APP_ID = 'app2'
AUTH_TOKEN_PATH = './optune_auth_token'

def test_measure_sigterm():
    all_output = b''
    cmd = [ 'python3', 'servo.py', '--verbose', '--auth-token', AUTH_TOKEN_PATH, '--account', ACCOUNT, APP_ID ]
    proc = subprocess.Popen(cmd, bufsize=0, stdout=subprocess.PIPE)
    while True:
        output = proc.stdout.readline()
        if output == b'' and proc.poll() is not None:
            break
        if output:
            print(output.strip())
            all_output += output
        if output and output.startswith(b'measuring'):
            time.sleep(1)
            os.kill(proc.pid, signal.SIGTERM)

    rc = proc.poll()
    out_str1 = b'Cancelling due to signal: #10'
    out_str2 = b'Cancelling measure test'
    print('rc {}'.format(rc))
    print(str(all_output, encoding='UTF-8'))
    assert rc == 15
    assert out_str1 in all_output
    assert out_str2 in all_output
