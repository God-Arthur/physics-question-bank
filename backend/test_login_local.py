#!/usr/bin/env python3
import requests

url = 'http://localhost:5000/api/auth/login'
data = {'username': 'admin', 'password': 'admin123'}

try:
    response = requests.post(url, json=data)
    print(f'Status: {response.status_code}')
    if response.status_code == 200:
        print('Login successful!')
    else:
        print(f'Response: {response.text[:200]}')
except Exception as e:
    print(f'Error: {e}')