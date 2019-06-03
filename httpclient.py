import requests

r = requests.get('http://httpbin.org/json')
print(r.status_code, r.json())

r = requests.post('http://httpbin.org/post', json={
    "hello": "hello world"
})
print(r.status_code, r.json())
