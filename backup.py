import datetime
import os
import json
import time
from apiclient.discovery import build
from google.oauth2.credentials import Credentials
from traceback import format_exc

from misc import (
    error_and_exit,
    execute_command,
    format_subprocess_error,
    send_notif
)

config = {}

def read_config():
    config_file = open('/opt/ghost-backup/.config.json', 'r')
    config_file_json = json.loads(config_file.read())
    config_file_json['timestamp'] = datetime.datetime.fromtimestamp(
        time.time()).strftime('%Y%m%d%H%M%S')
    config.update(config_file_json)

def dump_db():
    if config['images'] and config['themes']:
        config['dump_path'] = os.getcwd()
    else:
        dump_path = config['images_dir'] if config['images'] else config['themes_dir']
        config['dump_path'] = os.path.normpath(dump_path + '/..')

    dump_path = config['dump_path'] + '/{0}.sql'.format(config['timestamp'])
    dump_command = ("mysqldump -h{mysql_hostname} -u{mysql_username} "
            "-p{mysql_password} {mysql_db_name} > {0}".format(dump_path, **config)
    )
    status = execute_command(dump_command)

    if status.returncode != 0:
        print("state code here %s " %status.returncode)
        error_and_exit(
            '\nError while taking DB dump\n\n{0}'.format(format_subprocess_error(status)),
            config['telegram_user_id']
        )

def main():
    read_config()
    dump_db()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        error_and_exit("\nFollowing error occured:\n{0}\n\n"
                       "More info about the error:\n{1}".format(e, format_exc()),
                       config['telegram_user_id']
        )
