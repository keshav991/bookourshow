import urllib.request
import json
import time

try:
    req = urllib.request.urlopen('http://127.0.0.1:8000/shows/1/seats')
    print('Status:', req.status)
    data = req.read().decode()
    print(json.dumps(data, indent=2))
except Exception as e:
    print('Error:', type(e).__name__, str(e))
