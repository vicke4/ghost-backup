import subprocess
import requests

subprocess_options = {
    'shell': True,
    'stderr': subprocess.PIPE,
    'stdout': subprocess.PIPE
}

def execute_command(command):
    return subprocess.run(command, **subprocess_options)

def send_notif(userid, msg):
    endpoint = 'https://api.telegram.org/bot484412347:AAH0ZavyA0yiYx1MYDngPQMt1HJkhcqTpmc/sendMessage'

    payload = {
        'chat_id': userid,
        'text': msg
    }

    requests.post(endpoint, data=payload)
