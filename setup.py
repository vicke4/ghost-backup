from getpass import getpass
import json
import os
import re
import requests
import time

from misc import display_msg, error_and_exit, execute_command, send_notif

backup_options = {}

def display_yn_prompt(prompt_msg, prompt_type, default_value='N', save=True):
    while(1):
        print("\n{0}".format(prompt_msg))
        display_msg('Y/N', 'options')
        display_msg(default_value, 'default_value')
        user_input = input().lower().strip() or default_value.lower()

        if user_input in ['y', 'n', 'yes', 'no', '']:
            boolean = False if user_input in [
                'n', 'no', ''] else True

            if save:
                backup_options[prompt_type] = boolean
                break
            else:
                return boolean
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

    if backup_key.find('password') != -1:
        user_input = getpass('')
    else:
        user_input = input().strip()

    if user_input == '':
        backup_options[backup_key] = prompt_default_value
    else:
        backup_options[backup_key] = user_input

    return backup_options[backup_key]

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

def get_credentials():
    from apiclient.discovery import build
    from google_auth_oauthlib.flow import InstalledAppFlow
    from apiclient.http import MediaFileUpload

    SCOPES = ['https://www.googleapis.com/auth/drive']
    client_config = {
        "installed": {
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://accounts.google.com/o/oauth2/token",
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
        }
    }

    client_config["installed"]['client_id'] = display_input_prompt(
        '\nGoogle API client id')
    client_config["installed"]['client_secret'] = display_input_prompt(
        '\nGoogle API client secret')

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    print('\n')

    try:
        credentials = flow.run_console(
            authorization_prompt_message='Please visit the below URL to get\n'
            'autorization code to authorize Google Drive access\n\n{url}',
            authorization_code_message='\nAuthorization Code\n'
        )

        client_config['installed']['refresh_token'] = credentials.refresh_token
        backup_options['oauth'] = client_config['installed']
    except Exception as e:
        error_and_exit(
            '\nAn Error occured while authenticating Gdrive access\n{0}'.format(e))

    return credentials

def setup_gdrive():
    credentials = get_credentials()

    display_msg('\nPlease wait till the Gdrive setup is complete..', 'bold')
    drive = build('drive', 'v3', credentials=credentials)

    folder_query = ('mimeType="application/vnd.google-apps.folder" and '
                    'name = "Ghost Backup" and trashed = False')

    try:
        resp = drive.files().list(q=folder_query).execute()
    except Exception as e:
        error_and_exit(
            '\n{0}\nAn Error occured while hitting request to Gdrive'.format(e))

    use_existing_folder = False

    if len(resp.get('files')) > 0:
        use_existing_folder = display_yn_prompt("Ghost Backup folder found "
                "on your Google Drive.\nDo you want to use it as your backup folder?\n"
                "(No will create a new folder with the same name)", '', 'Y', False)

    if use_existing_folder:
        resp = resp['files'][0]
        display_msg('Using existing folder', 'bold')
    else:
        file_metadata = {
            'name': 'Ghost Backup',
            'mimeType': 'application/vnd.google-apps.folder'
        }

        resp = drive.files().create(body=file_metadata, fields='id').execute()

    if resp.get('id') is not None:
        file_metadata = {
            'name': 'initial_backup.txt',
            'parents': [resp.get('id')]
        }
        status = execute_command(
            "echo 'This text file is the initial backup' > backup.txt")

        if status.returncode == 0:
            media = MediaFileUpload('backup.txt')
            resp = drive.files().create(body=file_metadata, media_body=media,
                                            fields='id').execute()
            backup_options['backup_file_id'] = resp.get('id')
            execute_command('rm backup.txt')
            display_msg('Google Drive configured successfully', 'options')
        else:
            error_and_exit('\nInitial file creation failed')
    else:
        error_and_exit('\nAn Error occured while creating folder on Gdrive')

def copy_files():
    if not os.path.isdir('/opt/ghost-backup'):
        os.makedirs('/opt/ghost-backup')

    execute_command('cp backup.py misc.py /opt/ghost-backup')

def setup_cron():
    from crontab import CronTab

    try:
        username = execute_command("whoami").stdout.strip()
        username = str(username, 'utf-8')
        cron = CronTab(user=username)
    except Exception as e:
        error_and_exit('\n{0}\n'
            'An Error occured while scheduling backup task'.format(e))

    script_command = 'python3 /opt/ghost-backup/backup.py > /opt/ghost-backup/backup.log 2>&1'
    jobs = cron.find_command(script_command)

    for job in jobs:
        if job.command == script_command:
            backup_options['cron_written'] = True
            break

    if not backup_options.get('cron_written', False):
        job = cron.new(
            command=script_command,
            comment='Ghost blog daily backup'
        )

        job.hour.on(0)
        job.minute.on(0)

        cron.write()
        backup_options['cron_written'] = True

def setup_notifications():
    retries = 0

    while(retries < 3):
        print("Send any message to Telegram bot @GhostBackupBot\n"
              "you can also use this link ", end="")
        display_msg("https://t.me/GhostBackupBot", "link", "")
        print("\nOnce done enter your Telegram username without '@'")

        user_input = input().lower().strip()
        print("\nWait for sometime to setup notifications..")
        time.sleep(2)

        resp = requests.get('https://api.telegram.org/bot484412347:'
        'AAH0ZavyA0yiYx1MYDngPQMt1HJkhcqTpmc/getUpdates')

        for message_obj in resp.json()['result']:
            chat_obj = message_obj['message']['chat']

            if chat_obj['username'] == user_input:
                backup_options['telegram_user_id'] = chat_obj['id']
                send_notif(chat_obj['id'],
                    "Hi {0}, starting today, you'll receive updates about "
                    "your Ghost blog backup on this chat. Have a nice day 😉"
                    .format(chat_obj['first_name'])
                )
                break

        if backup_options.get('telegram_user_id', None) != None:
            display_msg("\nNotification setup successfully completed!!!",
                                                        'options')
            break
        else:
            print("\nAre you sure your username is correct and you "
                    "sent a msg @GhostBackupBot?")
            print("As the notification setup failed, retrying...")
            retries += 1

    if not backup_options.get('telegram_user_id'):
        display_msg("\nNotification setup failed", "error")

def write_config():
    config_file = open('/opt/ghost-backup/.config.json', 'w')
    config_file.write(json.dumps(backup_options, indent=4, sort_keys=True))
    config_file.write('\n')
    config_file.close()

def main():
    display_msg("\nGhost Backup Setup Wizard\n"
                "-------------------------", 'bold')

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

    display_msg('Please wait to complete requirements download...')

    install_package("google-api-python-client python-crontab "
                    "google-auth-httplib2 google-auth-oauthlib google-auth")
    setup_gdrive()
    copy_files()
    setup_cron()

    display_yn_prompt("Would you like to get notifications\n"
                "on Telegram about backup status?", 'notification', 'Y')

    if backup_options['notification']:
        setup_notifications()

    write_config()

    display_msg('\nBackup setup completed succesfully!!!\n', 'options')

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        error_and_exit('Following error occured \n{0}\n'.format(e))
