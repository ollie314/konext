__author__ = 'mehdi'

from uuid import uuid1
import libkonext
import time


class Task:
    """
    Define a task to be processed in the queue (eibd side and client side)

    From eibd side, information will be processed using command information
    From client side, information will be processed using the response information.

    Request task will be forge and pushed into the request queue by the client socket thread.
    Request task will be processed by an eibdWriter (thread able to consume a specific queue).

    Response task will be forge by a thread responsible to handle response from the eibd socket and these response
    will be pushed into response queue and sometimes into the watching queue.
    Response task will be processed by a two specific threads started in the client socket thread. One for reading process
    and another one for watching process.
    """

    READ_TASK = 1
    WRITE_TASK = 2

    def __init__(self, raw_command, command, value, kind, group_address=None, response=None):
        self.uuid = uuid1()
        self.created_at = time.time()
        self.raw_command = raw_command
        self.command = command
        self.group_address = group_address
        self.value = value
        self.kind = kind
        self.response = response

    def set_response(self, response):
        self.response = response
        return self

    @staticmethod
    def create_task_from_raw(raw_command):
        """
        Create a task without parsing the command. It means that if more than one tasks is asking, the process
        doesn't make any difference. Another process will split it in atomic task for eibd.

        :param raw_command: the command sent by the client (on the socket)
        :return: a task representing the command sent
        """
        command = libkonext.get_header(raw_command)         # SE, RE, WE or UE
        value = libkonext.get_body(raw_command)             # 15/0/1,15/0/3 ... or 15/0/2=FF,1/2/3=AA ...
        kind = libkonext.get_command_kind(command)          # NKX_NONE, KNX_READ, KNX_WRITE, KNX_RESPONSE(not use by the writer)
        task = Task(raw_command, command, value, kind)
        return task

    @staticmethod
    def clone_task(task):
        """
        Clone a task based.

        :param task: the task to clone
        :return: the cloned task
        """
        _task = Task(task.raw_command, task.command, task.value, task.kind, task.group_address, task.response)
        return _task

    @staticmethod
    def stringify(task):
        result = ''
        result += "Raw command : %s\n" % task.raw_command
        result += "Command : %s\n" % task.command
        result += "Group address : %s\n" % task.group_address
        result += "Value : %s\n" % task.value
        result += "Kind : %s\n" % task.kind
        result += "Response : %s\n" % task.response
        return result

    @staticmethod
    def extract_tasks(task):
        """
        Extracting tasks from the command.
        A command is something like the following examples :
            - 15/0/1,15/0/2, ...
            - 15/0/1=FF,15/0/2=AA, ...

        In the first case, a task containing the command is created and no value is assign to the task
            _t = {
                [...]
                command: RE or WE or UE
                kind:READ or WATCH or UNWATCH
                group_address:15/0/1
                value:None
                [...]
            }
        In the second case a task containing the command (group address) and a value (value to write) will be created
            _t = {
                [...]
                command: SE
                kind:WRITE
                group_address:15/0/1
                value:FF
                [...]
            }

        :param task:the task to extract info from
        :return: an array of task to do on the eibd queue
        """
        tasks = []
        orders = task.value.split(',')
        for order in orders:
            _t = Task.clone_task(task)
            if task.kind == libkonext.KNX_WRITE_FLAG:
                (group_address, val) = order.split('=')
                _t.group_address = group_address
                _t.value = val
            else:
                _t.group_address = order
                _t.value = None
            tasks.append(_t)
        return tasks


if __name__ == '__main__':
    import sys
    command = sys.argv[1]
    command = command.strip('"')
    print "Group address is %s" % command
    task = Task.create_task_from_raw(command)
    tasks = Task.extract_tasks(task)
    for t in tasks:
        r = Task.stringify(t)
        print "Task is : %s" % r
    print "End of work"