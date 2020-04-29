import logging
import os
from gym.infra.ssh.plugin import SSHProxy

logging.basicConfig(level=logging.DEBUG)

proxy = SSHProxy()

cfg = {
    "address": {
        "value": "172.17.0.2",
    },
    "port": {
        "value": "22",
    },
    "user": {
        "value": "gym",
    },
    "password": {
        "value": "R0cks.4l1v3",
    },
}

proxy.cfg(cfg)

filepath = os.path.join(
    os.path.dirname(__file__), 
    "gym.tar.xz")

proxy.upload_file(filepath, "/home/gym/")

cmd =   "cd /home/gym/ && tar xf gym.tar.xz && "\
        "cd gym && sudo python3.7 setup.py install"

ack = proxy.execute_command(cmd)
print(f"command ack {ack}")

cmd = "gym-agent --uuid agent --address 172.17.0.2:50056 > gym-agent.log 2>&1 &"
ack = proxy.execute_command(cmd)
print(f"command ack {ack}")