import asyncio
import logging
import signal
import time
import json
from multiprocessing import Process
from multiprocessing import Queue 

from grpclib.utils import graceful_exit
from grpclib.server import Server

from google.protobuf import json_format

from gym.common.protobuf.gym_grpc import InfraBase
from gym.common.protobuf.gym_pb2 import Deploy, Built

from plugin import ContainernetPlugin
from environment import Environment


logger = logging.getLogger(__name__)


class Playground:
    def __init__(self, in_queue, out_queue):
        self.exp_topo = None
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.init()

    def init(self):
        self.loop(self.in_queue, self.out_queue)
        
    def loop(self, in_queue, out_queue):
        logger.info("Playground loop started")
        while True:
            try:
                msg = in_queue.get()
            except Exception as e:
                logger.debug(f"Exception in the loop: {e}")
            else:
                cmd = msg.get("cmd")
                scenario = msg.get("scenario")
                
                logger.info("Playground command %s", cmd)

                if cmd == "start":
                    reply = self.start(scenario)
                elif cmd == "stop":
                    reply = self.stop()
                else:
                    reply = {}

                out_queue.put(reply)

                if cmd == "stop":
                    break

    def start(self, scenario):
        self.clear()
        self.exp_topo = Environment(scenario)       
        ok, info = self.exp_topo.start()       
        logger.info("hosts info %s", info)
        

        msg = {
            "info": info,
            "error": None,
        }

        ack = {
            'ok': str(ok),
            'msg': msg, 
        }
        return ack

    def stop(self):
        logger.info("Stopping topo %s", self.exp_topo)
        ack = self.exp_topo.stop()
        self.exp_topo = None

        msg = {
            "info": "",
            "error": "",
        }

        ack = {
            'ok': str(ack),
            'msg': msg, 
        }
        return ack

    def clear(self):
        exp = Environment({})
        exp.mn_cleanup()
        logger.info("Experiments cleanup OK")


class Scenario(InfraBase):
    def __init__(self):
        self.plugin = ContainernetPlugin()
        self.playground = None
        self.in_queue = Queue()
        self.out_queue = Queue()

    async def call(self, cmd, scenario):
        msg = {"cmd": cmd, "scenario": scenario}
        self.in_queue.put(msg)
        reply = self.out_queue.get()
        return reply

    def init(self):
        Playground(self.in_queue, self.out_queue)
        print("Finished Playground")

    def start(self):
        self.in_queue = Queue()
        self.out_queue = Queue()
        self.playground = Process(target=self.init)
        self.playground.start()
        logger.info("Started playground")
                            
    def stop(self):       
        self.playground.join(1)
        time.sleep(0.5)
        logger.info("playground alive %s", self.playground.is_alive())        
        logger.info("playground exitcode ok %s", self.playground.exitcode)
        self.in_queue = None
        self.out_queue = None
        self.playground = None
        logger.info("Stoped playground")

    async def play(self, id, command, scenario):       
        if command == "start":
            if self.playground:
                logger.debug("Stopping running playground")
                await self.call("stop", None)
                self.stop()
            
            self.start()            
            reply = await self.call(command, scenario)

        elif command == "stop":
            reply = await self.call(command, scenario)
            self.stop()
        else:
            logger.debug(f"Unkown playground command {command}")
            return False, {}
       
        ack, info = reply.get("ok"), reply.get("msg")
        return ack, info

    async def Run(self, stream):
        deploy = await stream.recv_message()        
        deploy_dict = json_format.MessageToDict(deploy, preserving_proto_field_name=True)
        
        id = deploy_dict.get("id")
        command = deploy_dict.get("workflow")
        scenario = self.plugin.build(deploy_dict.get("scenario"))
        
        ok, msg = await self.play(id, command, scenario)
        logger.debug(f"Playground msg: {msg}")
        
        error = msg.get("error")
        info = json.dumps(msg.get("info"))
        built_info = info.encode('utf-8')
        logger.debug(f"Encoded info {built_info}")

        built = Built(id=id, ack=ok, error=error, info=built_info)
        await stream.send_message(built)


if __name__ == "__main__":
    
    logging.basicConfig(level=logging.DEBUG)

    async def main(*, host='127.0.0.1', port=50051):
        server = Server([Scenario()])
        with graceful_exit([server]):
            await server.start(host, port)
            print(f'Serving on {host}:{port}')
            await server.wait_closed()

    asyncio.run(main())