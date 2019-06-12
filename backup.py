import datetime
import os
import json
import time
from apiclient.discovery import build
from apiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from traceback import format_exc

from misc import (
    error_and_exit,
    execute_command,
    format_subprocess_error,
    get_ecredentials,
    send_notif
)

config = {}

def read_config():
    config_file = open('/opt/ghost-backup/.config.json', 'r')
    config_file_json = json.loads(config_file.read())
    config_file_json['timestamp'] = datetime.datetime.fromtimestamp(
        time.time()).strftime('%Y%m%d')
    config.update(config_file_json)

def dump_db():
    if config['images'] and config['themes']:
        dump_path = config['images_dir'] if config['images'] else config['themes_dir']
        config['dump_path'] = os.path.normpath(dump_path + '/..')
    else:
        config['dump_path'] = os.getcwd()

    config['dump_file'] = config['dump_path'] + '/{0}.sql'.format(config['timestamp'])
    dump_command = ("mysqldump -h{mysql_hostname} -u'{mysql_username}' "
                    "-p'{mysql_password}' {mysql_db_name} > {0}".format(
                        config['dump_file'],
                        **config
                    )
    )
    status = execute_command(dump_command)

    if status.returncode != 0:
        print("state code here %s " %status.returncode)
        error_and_exit(
            '\nError while taking DB dump\n\n{0}'.format(format_subprocess_error(status)),
            config.get('telegram_user_id')
        )

def pack_files():
    compress_command = 'tar -C {0} -cvzf {1}.tar.gz {1}.sql'.format(
        config['dump_path'], config['timestamp'])

    if config['images']:
        compress_command += ' images'

    if config['themes']:
        compress_command += ' themes'
    status = execute_command(compress_command)

    if status.returncode != 0:
        print("state code here %s " %status.returncode)
        error_and_exit(
            '\nError while packing backup files\n\n{0}'.format(format_subprocess_error(status)),
            config.get('telegram_user_id')
        )

def upload_files():
    oauth_config = config['oauth']

    credentials = Credentials(
        None,
        refresh_token=oauth_config['refresh_token'],
        token_uri=oauth_config['token_uri'],
        client_id=get_ecredentials('yatch'),
        client_secret=get_ecredentials('bakery')
    )
    drive = build('drive', 'v3', credentials=credentials)

    media = MediaFileUpload('{0}.tar.gz'.format(config['timestamp']))
    file_metadata = {
        'name': ( '{app_name}' + '-' + config['timestamp'] + '.tar.gz').format(**config),
        'mimeType': 'application/gzip'
    }

    resp = drive.files().update(
        body=file_metadata,
        fileId=config['backup_file_id'],
        media_body=media
    ).execute()

def delete_backups():
    execute_command('rm {0} {1}.tar.gz'.format(config['dump_file'], config['timestamp']))

def main():
    read_config()
    dump_db()
    pack_files()
    upload_files()
    delete_backups()
    send_notif(config.get('telegram_user_id'), 'Backup completed successfully for ' + '{app_name}' + '.com' + '!').format(**config),

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        error_and_exit("\nFollowing error occured:\n{0}\n\n"
                       "More info about the error:\n{1}".format(e, format_exc()),
                       config.get('telegram_user_id')
        )
