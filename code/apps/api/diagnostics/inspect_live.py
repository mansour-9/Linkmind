import json
r=json.load(open('/reports/sonnet_live.json'))
print('stop',r.get('stop_reason'))
for q in r['questions']:
 print(q['number'],q['http_status'],q['response'])
print('revision',r.get('revision'))
print('addition',r.get('user_addition'))
