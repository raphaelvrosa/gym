import logging

logger = logging.getLogger(__name__)


class ContainernetPlugin:
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
