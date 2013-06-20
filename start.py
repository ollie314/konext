#!/usr/bin/python
import subprocess
from multiprocessing import Process

Process(target=subprocess.call, args=(('flashpolicyd.py', '--port', '843', '--file', './flashpolicy.xml', ), )).start()
Process(target=subprocess.call, args=(('server.py', ), )).start()
