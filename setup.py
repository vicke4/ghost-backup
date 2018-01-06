import traceback
import subprocess
import os

subprocess_options = {
    'shell': True,
    'stderr': subprocess.PIPE,
    # 'stdout': subprocess.PIPE
}

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
                print("\nPip installation failed with the error\n{0}\n".format(
                    get_error(pip_install_status['error'])))
        else:
            print("\nInstallation of {0} failed with the error:\n{1}\n".format(
                package_name, get_error(e.args[0])))

print("\n\nPlease wait for sometime to complete some requirements download..")
install_package('requestsas')
