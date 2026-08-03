import urllib.request, json
url = 'http://127.0.0.1:5000/api/what-if/simulate'
payload = {'scenario':'arrivals','params':{'extra_arrivals':6,'event':False,'weather':'clear'}}
data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type':'application/json'})
resp = urllib.request.urlopen(req)
text = resp.read().decode('utf-8')
print(text)
