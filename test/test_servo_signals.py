import pytest

import os
import select
import subprocess
import signal
import sys

ACCOUNT = 'kumul.us'
APP_ID = 'app2'
AUTH_TOKEN_PATH = './optune_auth_token'

def test_measure_sigterm():
    all_output = b''
    cmd = [ 'python3', 'servo.py', '--verbose', '--auth-token', AUTH_TOKEN_PATH, '--account', ACCOUNT, APP_ID ]
    proc = subprocess.Popen(cmd, bufsize=0, stdout=subprocess.PIPE)
    while True:
        output = proc.stdout.readline()
        if output == '' and proc.poll() is not None:
            break
        if output:
            # print(output.strip())
            all_output += output
        if output and output.startswith(b'measuring'):
            os.kill(proc.pid, signal.SIGTERM)
    # TODO: Execution never reaches here for some reason
    rc = proc.poll()
    print('rc {}'.format(rc))

    print(all_output)