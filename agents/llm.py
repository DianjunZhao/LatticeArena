import json
import os
import urllib.request
from pathlib import Path

BASE = os.environ.get('LLM_BASE', 'https://api.deepseek.com/v1')
KEY = os.environ.get('LLM_API_KEY') or (Path.home() / 'Desktop' / 'api.key').read_text().strip()
THINKING = os.environ.get('LLM_THINKING', 'disabled')


def chat(prompt, model='deepseek-flash'):
    body = json.dumps({'model': model,
                       'messages': [{'role': 'user', 'content': prompt}],
                       'response_format': {'type': 'json_object'},
                       'thinking': {'type': THINKING},
                       'temperature': 0.8}).encode()
    request = urllib.request.Request(BASE + '/chat/completions', data=body,
                                     headers={'Content-Type': 'application/json',
                                              'Authorization': f'Bearer {KEY}'})
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.loads(response.read())['choices'][0]['message']['content']
