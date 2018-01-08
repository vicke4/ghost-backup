from getpass import getpass
import os
import traceback
import re
import requests
import subprocess
import time

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

backup_options = {}

def display_msg(msg, msg_type=None, msg_end="\n"):
    bold = color_codes['BOLD'] if msg_type in ['error', 'options', 'default_value', 'bold'] else ''

    if msg_type in ['error', 'default_value']:
        color = color_codes['RED']
    elif msg_type == 'options':
        color = color_codes['GREEN']
    elif msg_type == 'link':
        color = color_codes['BLUE']
    else:
        color = ''

    print ("{0}{1}{2}{END}".format(bold, color, msg, **color_codes), end=msg_end)

def display_yn_prompt(prompt_msg, prompt_type):
    while(1):
        print("\n{0}".format(prompt_msg))
        display_msg('Y/N', 'options')
        display_msg('N', 'default_value')
        user_input = input().lower().strip()

        if user_input in ['y', 'n', 'yes', 'no', '']:
            backup_options[prompt_type] = False if user_input in [
                'n', 'no', ''] else True
            break
        else:
            display_msg('Invalid Input please try again', 'error')

    if prompt_type in ['images', 'themes'] and backup_options[prompt_type]:
        while(1):
            print("\n{0} directory".format(prompt_type))
            default_dir = '/var/www/ghost/content/{0}/'.format(prompt_type)
            display_msg(default_dir, 'default_value')
            user_input = input().lower().strip() or default_dir

            if os.path.isdir(user_input):
                backup_options['{0}_dir'.format(prompt_type)] = user_input
                break
            else:
                display_msg('Invalid Input please try again', 'error')

def display_input_prompt(prompt_msg, prompt_default_value=''):
    print(prompt_msg)

    if prompt_default_value != '':
        display_msg(prompt_default_value, 'default_value')

    backup_key = re.sub(' ', '_', prompt_msg).lower().strip()
    user_input = getpass('') if backup_key.find('password') != -1 else input().lower().strip()
    backup_options[backup_key] = prompt_default_value if user_input == '' else user_input

def get_error(e):
    return str(e, 'utf-8').strip() if type(e) != str else e.strip()

def install_pip():
    pip_script_present = 'get-pip.py' in os.listdir()

    if not pip_script_present:
        status = subprocess.run(
            "wget https://bootstrap.pypa.io/get-pip.py", **subprocess_options)

    if pip_script_present or status.returncode == 0:
        status = subprocess.run(
            "python get-pip.py", **subprocess_options)

        if status.returncode == 0:
            return {'status': True, 'error': None}

    return {'status': False, 'error': status.stderr}


def install_package(package_name):
    try:
        status = subprocess.run("pip install {0}".format(
            package_name), **subprocess_options)

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
                display_msg("\nPip installation failed with the error\n{0}\n".format(
                    get_error(pip_install_status['error'])), 'error')
        else:
            display_msg("\nInstallation of {0} failed with the error:\n{1}\n".format(
                package_name, get_error(e.args[0])), 'error')


display_msg("\nInstructions\n------------", 'bold')

print("1. Valid options will be displayed in ", end="")
display_msg('Green', 'options', "")
print(" and separated by forward slash (/)")

print("2. Default value will be displayed in ", end="")
display_msg('Red', 'default_value')

print("3. Just press ENTER to go with default value else input your custom value")

display_yn_prompt("\nWould you like to backup images?", 'images')
display_yn_prompt("\nWould you like to backup themes?", 'themes')

display_input_prompt('\nMySQL hostname', 'localhost')
display_input_prompt('\nMySQL username', 'root')
display_input_prompt('\nMySQL password')

display_yn_prompt("\nWould you like to get notifications\non Telegram about backup status?", 'notification')

if backup_options['notification']:
    retries = 0

    while(retries < 3):
        print("\nSend any message to Telegram bot @GhostBackupBot\nyou can also use this link ", end="")
        display_msg("https://t.me/GhostBackupBot", "link", "")
        print("\nOnce done enter your Telegram username without '@'")

        user_input = input().lower().strip()
        print("\nWait for sometime to setup notfications..")
        time.sleep(2)

        resp = requests.get('https://api.telegram.org/bot484412347:AAH0ZavyA0yiYx1MYDngPQMt1HJkhcqTpmc/getUpdates')

        for message_obj in resp.json()['result']:
            chat_obj = message_obj['message']['chat']

            if chat_obj['username'] == user_input:
                backup_options['telegram_user_id'] = chat_obj['id']
                break

        if backup_options.get('telegram_user_id', None) != None:
            display_msg("\nNotification setup successfully completed", 'options')
            break
        else:
            print("\nAre you sure your username is correct and you sent a msg @GhostBackupBot?")
            print("As the notification setup failed retrying...")
            retries += 1

print("\n\nBackup json {0}\n".format(backup_options))
