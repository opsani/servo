
import pytest
import requests

import io
import os
import subprocess
import sys

import servo

ACCOUNT = 'kumul.us'
APP_ID = 'app2'
AUTH_TOKEN_PATH = ''

MOCK_STATUS_UNEXPEVNT = """{"status" : "unexpected-event", "msg": "..."}"""

class TestClass:
    whats_next_counter = 0
    progress_update_counter = 0
    adjust_started = False
    fail_phase = None
    error_text = ''
    status_code = 0

    # Pytest runs this before each test_*() function
    def setup_function(self):
        self.whats_next_counter = 0
        self.progress_update_counter = 0
        self.adjust_started = False

    def response_hook(self, response, *args, **kwargs):
        # Check data of response.request to see what action the servo last performed
        # If servo is at desired point of failure, return desired error code and text as new response
        # Else return the actual response from the backend (by returning nothing)
        pass

    # 200 with error message
    def test_adjust_200(self, monkeypatch, requests_mock):
        with monkeypatch.context() as m:
            # set command line arguments
            m.setattr(sys, 'argv', [ 'servo', '--auth-token', AUTH_TOKEN_PATH, '--account', ACCOUNT, APP_ID ])
            self.fail_phase = 'ADJUST'
            self.status_code = 200
            self.error_text = MOCK_STATUS_UNEXPEVNT

            # Init servo
            servo.initialize()
            # Attach response hook
            servo.session.hooks['response'].append(self.response_hook)
            # Execute servo
            servo.run()
             
    # rest of tests...
