
import pytest
import requests

import io
import json
import os
import subprocess
import sys

from servo import initialize, run

ACCOUNT = 'kumul.us'
APP_ID = 'app2'

MOCK_WHATS_NEXT_QUEUE = [
    {"cmd": "DESCRIBE", "param": {}},
    {"cmd": "MEASURE", "param": {"metrics": ["TEST_METRIC", "TEST_TIME_TAKEN"], "control": {"load": {}}}},
    {"cmd": "ADJUST", "param": {"state": {"application": {"components": {"TEST": {"settings": {"TEST1": {"value": 51.0, "index": 0}, "TEST2": {"value": "A", "index": 1}}}}}}, "control": {}}},
    {"cmd": "MEASURE", "param": {"metrics": ["TEST_METRIC", "TEST_TIME_TAKEN"], "control": {"load": {}}}},
    {"cmd": "EXIT"},
]

MOCK_STATUS_OKAY = """{"status": "ok"}"""

MOCK_STATUS_UNEXPEVNT = """{"status" : "unexpected-event", "msg": "..."}"""

class TestClass:
    whats_next_counter = 0
    progress_update_counter = 0
    fail_phase = None
    error_text = ''
    status_code = 0

    # Pytest runs this before each test_*() function
    def setup_function(self):
        self.whats_next_counter = 0
        self.progress_update_counter = 0

    # Callback to replicate optune api functionality
    def mock_backend(self, request: requests.Request, context):
        req_dict = request.json()
        print('Mock handling: {}'.format(req_dict))
        if req_dict['event'] == 'WHATS_NEXT':
            self.progress_update_counter = 0
            resp = MOCK_WHATS_NEXT_QUEUE[self.whats_next_counter]
            self.whats_next_counter += 1
            resp_str = json.dumps(resp)
        elif req_dict['event'] == 'MEASUREMENT' and 'progress' in req_dict['param']:
            if self.fail_phase == 'MEASURE' and self.progress_update_counter == 1:
                context.status_code = self.status_code
                resp_str = self.error_text
            else:
                resp_str = MOCK_STATUS_OKAY
            self.progress_update_counter += 1
        elif req_dict['event'] == 'ADJUSTMENT' and 'progress' in req_dict['param']:
            if self.fail_phase == 'ADJUST' and self.progress_update_counter == 1:
                context.status_code = self.status_code
                resp_str = self.error_text
            else:
                resp_str = MOCK_STATUS_OKAY
            self.progress_update_counter += 1
        else:
            resp_str = MOCK_STATUS_OKAY
        
        print('Mock response ({}): {}'.format(context.status_code, resp_str))
        return resp_str

    # 200 with error message
    def test_adjust_200(self, monkeypatch, requests_mock):
        with monkeypatch.context() as m:
            # set command line arguments
            m.setattr(sys, 'argv', [ 'servo', '--no-auth', '--account', ACCOUNT, APP_ID ])
            self.fail_phase = 'ADJUST'
            self.status_code = 200
            self.error_text = MOCK_STATUS_UNEXPEVNT
            requests_mock.register_uri(
                'POST',
                'https://api.optune.ai/accounts/{}/applications/{}/servo'.format(ACCOUNT, APP_ID),
                text = self.mock_backend
            )
            # Execute servo
            initialize()
            with pytest.raises(SystemExit) as exit_exception:
                run()
            assert exit_exception.type == SystemExit
            assert exit_exception.value.code == 0

    def test_measure_200(self, monkeypatch, requests_mock):
        with monkeypatch.context() as m:
            # set command line arguments
            m.setattr(sys, 'argv', [ 'servo', '--no-auth', '--account', ACCOUNT, APP_ID ])
            self.fail_phase = 'MEASURE'
            self.status_code = 200
            self.error_text = MOCK_STATUS_UNEXPEVNT
            requests_mock.register_uri(
                'POST',
                'https://api.optune.ai/accounts/{}/applications/{}/servo'.format(ACCOUNT, APP_ID),
                text = self.mock_backend
            )
            # Execute servo
            initialize()
            with pytest.raises(SystemExit) as exit_exception:
                run()
            assert exit_exception.type == SystemExit
            assert exit_exception.value.code == 0


    # 400
    def test_adjust_400(self, monkeypatch, requests_mock):
        with monkeypatch.context() as m:
            # set command line arguments
            m.setattr(sys, 'argv', [ 'servo', '--no-auth', '--account', ACCOUNT, APP_ID ])
            self.fail_phase = 'ADJUST'
            self.status_code = 400
            self.error_text = "Invalid input"
            requests_mock.register_uri(
                'POST',
                'https://api.optune.ai/accounts/{}/applications/{}/servo'.format(ACCOUNT, APP_ID),
                text = self.mock_backend
            )
            # Execute servo
            initialize()
            with pytest.raises(SystemExit) as exit_exception:
                run()
            assert exit_exception.type == SystemExit
            assert exit_exception.value.code == 0

    def test_measure_400(self, monkeypatch, requests_mock):
        with monkeypatch.context() as m:
            # set command line arguments
            m.setattr(sys, 'argv', [ 'servo', '--no-auth', '--account', ACCOUNT, APP_ID ])
            self.fail_phase = 'MEASURE'
            self.status_code = 400
            self.error_text = "Invalid input"
            requests_mock.register_uri(
                'POST',
                'https://api.optune.ai/accounts/{}/applications/{}/servo'.format(ACCOUNT, APP_ID),
                text = self.mock_backend
            )
            # Execute servo
            initialize()
            with pytest.raises(SystemExit) as exit_exception:
                run()
            assert exit_exception.type == SystemExit
            assert exit_exception.value.code == 0

    # 503
    def test_adjust_503(self, monkeypatch, requests_mock):
        with monkeypatch.context() as m:
            # set command line arguments
            m.setattr(sys, 'argv', [ 'servo', '--no-auth', '--account', ACCOUNT, APP_ID ])
            self.fail_phase = 'ADJUST'
            self.status_code = 503
            self.error_text = "Unknown route"
            requests_mock.register_uri(
                'POST',
                'https://api.optune.ai/accounts/{}/applications/{}/servo'.format(ACCOUNT, APP_ID),
                text = self.mock_backend
            )
            # Execute servo
            initialize()
            with pytest.raises(SystemExit) as exit_exception:
                run()
            assert exit_exception.type == SystemExit
            assert exit_exception.value.code == 0

    def test_measure_503(self, monkeypatch, requests_mock):
        with monkeypatch.context() as m:
            # set command line arguments
            m.setattr(sys, 'argv', [ 'servo', '--no-auth', '--account', ACCOUNT, APP_ID ])
            self.fail_phase = 'MEASURE'
            self.status_code = 503
            self.error_text = "Unknown route"
            requests_mock.register_uri(
                'POST',
                'https://api.optune.ai/accounts/{}/applications/{}/servo'.format(ACCOUNT, APP_ID),
                text = self.mock_backend
            )
            # Execute servo
            initialize()
            with pytest.raises(SystemExit) as exit_exception:
                run()
            assert exit_exception.type == SystemExit
            assert exit_exception.value.code == 0
