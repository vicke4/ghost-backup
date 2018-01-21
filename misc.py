import json
import os
import re
import requests
import subprocess

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

def error_and_exit(msg, telegram_userid=None):
    display_msg(msg, 'error')

    if telegram_userid:
        send_notif(telegram_userid, msg)

    exit()

def get_error(e):
    return str(e, 'utf-8').strip() if type(e) != str else e.strip()

def install_pip():
    pip_script_present = 'get-pip.py' in os.listdir()

    if not pip_script_present:
        status = execute_command("wget https://bootstrap.pypa.io/get-pip.py")

    if pip_script_present or status.returncode == 0:
        status = execute_command("python3 get-pip.py")

        if status.returncode == 0:
            return {'status': True, 'error': None}

    return {'status': False, 'error': status.stderr}

def install_package(package_name):
    try:
        status = execute_command("pip install {0}".format(package_name))

        if status.returncode == 127:
            raise Exception('pip not found')
        elif status.returncode != 0:
            raise Exception(status.stderr)

    except Exception as e:
        if e.args[0] == 'pip not found':
            pip_install_status = install_pip()

            if pip_install_status['status']:
                install_package(package_name)
            else:
                error_and_exit("\nPip installation failed with the error\n{0}\n".format(
                    get_error(pip_install_status['error'])))
        else:
            error_and_exit("\nInstallation of {0} failed with the error:\n{1}\n".format(
                package_name, get_error(e.args[0])))

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

try:
    from cryptography.fernet import Fernet
except:
    display_msg('\nPlease wait required dependency is downloading...')
    install_package('cryptography')
    from cryptography.fernet import Fernet

try:
    get_cred = json.loads(open('/opt/ghost-backup/.niceneeded.json', 'r').read())
except:
    get_cred = json.loads(open('.niceneeded.json', 'r').read())

key_obj = Fernet('bf0h361TnXNKGJtY7nyRSOZ4m5fEMlqXzVFyGB-isEI='.encode('utf-8'))

def format_subprocess_error(completed_process):
    error_str = str(completed_process.stderr, 'utf-8')
    return re.sub('/bin/sh: 1: ', '', error_str)

def get_ecredentials(text):
    return key_obj.decrypt(get_cred[text[0]].encode('utf-8')).decode('utf-8')
