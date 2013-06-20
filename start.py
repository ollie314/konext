#!/usr/bin/python
import sys
import subprocess
from multiprocessing import Process

from flashpolicyd import policy_server

try:
    policy_server(843, './flashpolicy.xml').run()
    Process(target=subprocess.call, args=(('./server.py', ), )).start()
except Exception, e:
    print >> sys.stderr, e
    sys.exit(1)
except KeyboardInterrupt:
    pass

#Process(target=subprocess.call, args=(('flashpolicyd.py', '--port', '843', '--file', './flashpolicy.xml', ), )).start()

