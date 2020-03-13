import asyncio
import logging
import signal
import time
import json
from multiprocessing import Process
from multiprocessing import Queue 

from gym.infra.base import Plugin
from gym.infra.containernet.environment import Environment


logger = logging.getLogger(__name__)


class Parser:
    def __init__(self):       
        self.topology = None
        self.deploy = {}

    def get(self, what):
        if what == "topology":
            return self.topology
        if what == "deploy":
            return self.deploy
        return None

    def parse_nodes(self):
        nodes = self.topology.get("nodes")

        self.deploy["nodes"] = {}

        for node in nodes.values():
            node_id = node.get("id")
            self.deploy["nodes"][node_id] = node

            interfaces = node.get("connection_points")
            faces = {}
            if interfaces:
                for intf in interfaces.values():
                    intf_id = intf.get("id")
                    faces[intf_id] = intf
            self.deploy["nodes"][node_id]["interfaces"] = faces
                
    def parse_links(self):
        links = self.topology.get("links")

        self.deploy["links"] = {}
        self.deploy["switches"] = []
        self.deploy["port_maps"] = {}

        for link in links.values():
            link_id = link.get("id")
            link_type = link.get("type")

            if link_type == "E-Flow":
                link_network = link.get("network")
                if link_network not in self.deploy["switches"]:
                    self.deploy["switches"].append(link_network)

                adjacencies = link.get("connection_points")
                src, src_inft = adjacencies[0].split(":")
                dst, dst_intf = adjacencies[1].split(":")

                if link_network not in self.deploy["port_maps"]: 
                    self.deploy["port_maps"][link_network] = []
                self.deploy["port_maps"][link_network].append({'src':src_inft, 'dst':link_network})
                self.deploy["port_maps"][link_network].append({'src':link_network, 'dst':dst_intf})

                link_id_num = 0
                for (host,host_inft) in [(src,src_inft), (dst,dst_intf)]:
                    params_dst = {}                    
                    if host_inft in self.deploy["nodes"][host]["interfaces"]:
                        face = self.deploy["nodes"][host]["interfaces"].get(host_inft)
                        params_dst["ip"] = face.get("address", "")                  
                        link_id_parsed = link_id + str(link_id_num)
                        self.deploy["links"][link_id_parsed] = {
                            'type': link_type,
                            'src': link_network,
                            'dst': host,
                            'intf_dst': host_inft,
                            'params_dst': params_dst,
                        }

                    link_id_num += 1
        
            elif link_type == "E-LAN":
                link_network = link.get("network")
                if link_network not in self.deploy["switches"]:
                    self.deploy["switches"].append(link_network)

                adjacencies = link.get("connection_points")
                link_id_num = 0
                for adj in adjacencies:
                    dst, dst_intf = adj.split(":")

                    params_dst = {}
                    if dst_intf in self.deploy["nodes"][dst]["interfaces"]:
                        face = self.deploy["nodes"][dst]["interfaces"].get(dst_intf)
                        params_dst["ip"] = face.get("address", "")
                        link_id_parsed = link_id + str(link_id_num)
                        self.deploy["links"][link_id_parsed] = {
                            'type': link_type,
                            'src': link_network,
                            'dst': dst,
                            'intf_dst': dst_intf,
                            'params_dst': params_dst,
                        }
                        link_id_num += 1

            elif link_type == "E-Line":
                adjacencies = link.get("connection_points")
                logger.info(f"adjacencies: {adjacencies}")
                src, src_inft = adjacencies[0].split(":")
                dst, dst_intf = adjacencies[1].split(":")

                params_dst = {}
                if dst_intf in self.deploy["nodes"][dst]["interfaces"]:
                    face = self.deploy["nodes"][dst]["interfaces"].get(dst_intf)
                    params_dst["ip"] = face.get("address", "")

                params_src = {}
                if src_inft in self.deploy["nodes"][src]["interfaces"]:
                    face = self.deploy["nodes"][src]["interfaces"].get(src_inft)
                    params_src["ip"] = face.get("address", "")

                self.deploy["links"][link_id] = {
                    'type': link_type,
                    'src': src,
                    'intf_src': src_inft,
                    'dst': dst,
                    'intf_dst': dst_intf,
                    'params_src': params_src,
                    'params_dst': params_dst,
                }
            else:
                logger.info("unknown link type %s", link_type)

        logger.info("Plugin links %s", self.deploy["links"])

    def build(self, topology):
        logger.debug("Containernet plugin parsing topology")
        logger.debug(f"{topology}")
        self.topology = topology
        self.parse_nodes()
        self.parse_links()
        return self.deploy


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


class ContainernetPlugin(Plugin):
    def __init__(self):
        Plugin.__init__(self)
        self.parser = Parser()
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

    def _start(self):
        self.in_queue = Queue()
        self.out_queue = Queue()
        self.playground = Process(target=self.init)
        self.playground.start()
        logger.info("Started playground")
                            
    def _stop(self):       
        self.playground.join(1)
        time.sleep(0.5)
        logger.info("playground alive %s", self.playground.is_alive())        
        logger.info("playground exitcode ok %s", self.playground.exitcode)
        self.in_queue = None
        self.out_queue = None
        self.playground = None
        logger.info("Stoped playground")

    async def play(self, command, scenario):       
        if command == "start":
            if self.playground:
                logger.debug("Stopping running playground")
                await self.call("stop", None)
                self._stop()
            
            self._start()            
            reply = await self.call(command, scenario)

        elif command == "stop":
            reply = await self.call(command, scenario)
            self._stop()
        else:
            logger.debug(f"Unkown playground command {command}")
            return False, {}
       
        ack, info = reply.get("ok"), reply.get("msg")
        return ack, info

    async def start(self, scenario):
        logger.info("Containernet Start")
        cnet_scenario = self.parser.build(scenario)
        ok, msg = await self.play("start", cnet_scenario)
        logger.debug(f"Playground msg: {msg}")       
        return ok, msg

    async def stop(self, scenario=None):     
        logger.info("Containernet Stop")
        ok, msg = await self.play("stop", scenario)
        logger.debug(f"Playground msg: {msg}")
        return ok, msg
