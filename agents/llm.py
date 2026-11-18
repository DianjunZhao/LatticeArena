import json
import os
import urllib.request

BASE = os.environ.get('LLM_BASE', 'https://api.deepseek.com/v1')


def chat(prompt, model):
    key = os.environ.get('LLM_API_KEY')
    if not key:
        raise ValueError('Set LLM_API_KEY before calling the model')
    body = json.dumps({'model': model,
                       'messages': [{'role': 'user', 'content': prompt}],
                       'response_format': {'type': 'json_object'},
                       'temperature': 0.8}).encode()
    request = urllib.request.Request(BASE + '/chat/completions', data=body,
                                     headers={'Content-Type': 'application/json',
                                              'Authorization': f'Bearer {key}'})
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.loads(response.read())['choices'][0]['message']['content']
