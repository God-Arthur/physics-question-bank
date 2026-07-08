#!/usr/bin/env python3
import requests
import json

# 测试登录 API
try:
    response = requests.post(
        'http://127.0.0.1:5000/api/auth/login',
        json={'username': 'admin', 'password': 'admin1906'},
        timeout=5
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
