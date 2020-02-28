# Runnings Servo Failure Tests

```bash
cd servo/test
ln -s ../servo ./servo.py
ln -s ../measure.py ./measure.py
ln -s ../adjust.py ./adjust.py
ln -s ../state_store.py ./state_store.py
python3 -m pytest -s
```

Note: for test_servo_signals.py to function properly, an activle OCO backend app is required. Use the constants within test_servo_signals.py (ACCOUNT, APP_ID, AUTH_TOKEN_PATH) to set the neccesary data for communication with this backend
