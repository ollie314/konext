__author__ = 'mehdi'

import os
import shutil
from liblogging import init_logger


def setup_config(app_name):
    config_file = open('/etc/%s/application.conf' % app_name)
    tmp_config = config_file.readlines()
    app_config = {}
    config_file.close()
    it = iter(tmp_config)
    for item in it:
        tmp = item.split('=')
        app_config[tmp[0]] = tmp[1].rstrip()
    return app_config


def mark_pid_on_fs():
    pid = os.getpid()
    target_dir = '/tmp/konext'

    if os.path.exists(target_dir):
        shutil.rmtree(target_dir, True)

    os.makedirs(target_dir)

    with open(os.path.join(target_dir, ".pid"), 'w') as temp_file:
        temp_file.write("%d" % pid)