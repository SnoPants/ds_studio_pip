import maya.cmds as cmds

if not cmds.commandPort(':7001', q=True):
    cmds.commandPort(name=':7001', sourceType='python')

# This is to allow maya to execute python commands sent from external applications.
# You just need to run this script once in maya and the command port will be open and ready to recieve commands.

import socket

def send_to_maya(command, host='127.0.0.1', port=7001):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    s.send((command + '\n').encode('utf-8'))
    result = s.recv(4096).decode('utf-8')
    s.close()
    return result

# This funtion can be used to send python commands to maya from an external application.
# Just call send_to_maya('your_python_command_here') and it will execute the command in maya.