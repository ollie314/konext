__author__ = 'mehdi'

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