import json
import re
import requests
import subprocess
from cryptography.fernet import Fernet

subprocess_options = {
    'shell': True,
    'stderr': subprocess.PIPE,
    'stdout': subprocess.PIPE
}

color_codes = {
    'HEADER': '\033[95m',
    'BLUE': '\033[94m',
    'GREEN': '\033[92m',
    'WARNING': '\033[93m',
    'RED': '\033[91m',
    'END': '\033[0m',
    'BOLD': '\033[1m',
    'UNDERLINE': '\033[4m'
}

get_cred = json.loads(open('.niceneeded.json', 'r').read())
key_obj = Fernet('bf0h361TnXNKGJtY7nyRSOZ4m5fEMlqXzVFyGB-isEI='.encode('utf-8'))

def execute_command(command):
    return subprocess.run(command, **subprocess_options)

def send_notif(userid, msg):
    endpoint = 'https://api.telegram.org/bot484412347:AAH0ZavyA0yiYx1MYDngPQMt1HJkhcqTpmc/sendMessage'

    payload = {
        'chat_id': userid,
        'text': msg
    }

    requests.post(endpoint, data=payload) if userid != None else ''

def display_msg(msg, msg_type=None, msg_end="\n"):
    bold = color_codes['BOLD'] if msg_type in ['error',
                                               'options', 'default_value', 'bold'] else ''

    if msg_type in ['error', 'default_value']:
        color = color_codes['RED']
    elif msg_type == 'options':
        color = color_codes['GREEN']
    elif msg_type == 'link':
        color = color_codes['BLUE']
    else:
        color = ''

    print ("{0}{1}{2}{END}".format(bold, color, msg, **color_codes),
           end=msg_end)

def error_and_exit(msg, telegram_userid=None):
    display_msg(msg, 'error')

    if telegram_userid:
        send_notif(telegram_userid, msg)

    exit()

def format_subprocess_error(completed_process):
    error_str = str(completed_process.stderr, 'utf-8')
    return re.sub('/bin/sh: 1: ', '', error_str)

def get_ecredentials(text):
    return key_obj.decrypt(get_cred[text[0]].encode('utf-8')).decode('utf-8')
