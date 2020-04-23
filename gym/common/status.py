import logging
import platform as pl
import psutil as ps


logger = logging.getLogger(__name__)


class Environment():
    def __init__(self):
        self._info = self._node()

    def info(self):
        return self._info

    def _get_node_info(self):
        info = {}
        system, node, release, version, _, processor = pl.uname()
        info['system'] = system
        info['host'] = node
        info['release'] = release
        info['version'] = version
        info['processor'] = processor
        return info

    def _get_node_cpu(self):
        cpu = {}
        cpu['logical'] = ps.cpu_count(logical=True)
        cpu['cores'] = ps.cpu_count(logical=False)
        return cpu

    def _get_node_mem(self):
        mem = {}
        mem['pyshical'] = ps.virtual_memory().total
        mem['swap'] = ps.swap_memory().total
        return mem

    def _get_node_storage(self):
        total = ps.disk_usage('/').total
        percent = ps.disk_usage('/').percent
        
        storage = {
            "total": total,
            "percent": percent,
        }
        return storage

    def _get_node_net(self):
        net = {}
        addrs = ps.net_if_addrs()      
        for face in addrs:
            face_addrs = [addr for addr in addrs[face] if addr.family==2]
            if face_addrs:
                face_addr = face_addrs.pop()
                net[face] = face_addr.address                
        return net

    def _get_node_resources(self):
        resources = {}
        resources['cpu'] = self._get_node_cpu()
        resources['memory'] = self._get_node_mem()
        resources['disk'] = self._get_node_storage()
        resources['network'] = self._get_node_net()
        return resources

    def _node(self):
        """Extracts environment info using psutil
        containing details of host system/platform/release
        and resources (cpu, mem, disk, net)

        Returns:
            dict -- Host node resources categorized in
            cpu, memory, disk, network and Host node 
            system description (system, release, platform, version,
            hostname)
        """
        info = self._get_node_info()
        resource = self._get_node_resources()
        info.update(resource)
        return info

class Identity:
    def __init__(self, info, env=False):
        self._env = Environment()
        self.uuid = info.get("uuid")
        self.role = info.get("role")
        self.address = info.get("address")
        self.contacts = info.get("contacts", [])
        self.apparatus = info.get("apparatus", {})
        self.artifacts = info.get("artifacts", {})
        self.environment = info.get("environment", {})
        logger.info(f"Identity built: uuid {self.uuid} for {self.role} at {self.address}")
        self.load_env(env)
        
    def load_env(self, env):
        if env:
            self.environment = self._env.info()
            logger.info(f"Identity environment info loaded/extracted")
        else:
            logger.info(f"Identity environment imported")
        
    def validate(self, roles):
        if self.uuid and self.role and self.address:
            if self.role in roles:
                return True
            else:
                logger.info(f"Role {self.role} not allowed for identity - "
                            f"accepts only {roles}")
        else:
            logger.info(f"Mandatory fields not provided for Identity"
                        f"uuid {self.uuid} and/or role {self.role} and/or address {self.address}")       
        return False

    def get(self, param):
        value = getattr(self, param, None)
        return value

    def set(self, param, value):
        if hasattr(self, param):
            field = getattr(self, param)
            
            if type(field) is dict:                
                field.update(value)
            else:
                setattr(self, param, value)
            return True
        
        return False

    def profile(self, filter_fields=None):
        info = {}
        
        if filter_fields:
            fields = filter_fields
        else:
            fields = ["uuid", "role", "address", 
                      "environment", "apparatus", "artifacts"]
        
        for k, v in self.__dict__.items():
            if k in fields:
                info[k] = v
       
        return info

    def update(self, info):
        fields = ["uuid", "role", "address",
                  "environment", "apparatus", "artifacts"]

        for field in fields:
            info_value = info.get(field, None)
            if info_value:
                self.set(field, info_value)


class Peers:
    def __init__(self, allowed_roles=[]):
        self.peers = {}
        self.allowed_roles = allowed_roles

    def add(self, info):
        uuid = info.get("uuid")
        address = info.get("address")
        peer_key = (uuid,address)

        logger.info(f"Adding peer (uuid,address) {peer_key}")
        
        if peer_key not in self.peers:
            peer = Identity(info)

            if peer.validate(self.allowed_roles):
                self.peers[peer_key] = peer
                logger.info(f'Peer added: uuid {uuid} role {peer.get("role")}')
                return True
            else:
                logger.info(f'Peer not added: uuid {uuid} role {peer.get("role")}')

        else:
            logger.info(f'Peer not added: already existing peer (uuid,address) {peer_key}')
            peer = self.peers[peer_key]
            peer.update(info)
            logger.info(f'Peer existent info updated: uuid {uuid} role {peer.get("role")}')

        return False

    def clear(self):
        self.peers.clear()
        logger.info(f"Peers deleted/cleared")
       
    def del_peer(self, peer):
        uuid = peer.get('uuid')

        if uuid in self.peers:
            del self.peers[uuid]
            logger.info(f"Peer {uuid} deleted")
        else:
            logger.info(f"Peer {uuid} not existent/deleted")

    def get_by(self, field, value, alls=False):
        rels = []

        for _, peer in self.peers.items():
            if peer.get(field):
                if peer.get(field) == value:
                    if alls:
                        rels.append(peer)
                    else:
                        return peer
        if alls:
            return rels
        else:
            return None


class Status:
    def __init__(self, info):
        self.identity = Identity(info, env=True)
        self.peers = Peers()
        self.allowed_roles = []
        self.cfg_roles(info)
        
    def cfg_roles(self, info):
        role = info.get("role")
        
        if role == "agent" or role == "monitor":       
            allowed_roles = ["manager"]
        elif role == "manager":
            allowed_roles = ["player", "agent", "monitor"]
        elif role == "player":
            allowed_roles = ["manager"]
        else:
            logger.info(f"Status allowed roles empty, "
                        f"unknown identity role {role}")

            allowed_roles = []

        self.allowed_roles = allowed_roles
        self.peers.allowed_roles = allowed_roles
        logger.info(f"Status configured: allowed contact roles: {allowed_roles}")

    def profile(self, filter_fields=None):
        profile = self.identity.profile(filter_fields)
        return profile

    def update(self, field, values):
        info  = {
            field: values,
        }
        self.identity.update(info)

    def _apparatus(self, names, contacts_profiles):
        apparatus = {}
        for name in names:
            if name in contacts_profiles:
                profiles = contacts_profiles[name]
                if profiles:
                    apparatus[name] = profiles
        return apparatus

    def update_identity(self, contacts_profiles):
        identity_role = self.identity.get("role")
        apparatus = {}
        
        if identity_role == "agent" or identity_role == "monitor":
            pass

        elif identity_role == "manager":
            names = ["agents", "monitors"]           
            apparatus = self._apparatus(names, contacts_profiles)

        elif identity_role == "player":
            names = ["managers"]           
            apparatus = self._apparatus(names, contacts_profiles)
            
        else:
            pass

        if apparatus:
            logger.info(f'Updating identity apparatus')
            logger.debug(f"{apparatus}")
            self.update("apparatus", apparatus)

    def update_status(self, roles):
        logger.info(f"Updating status with peer roles {roles}")
        feats = {}
                
        for role in roles:
            peers = self.peers.get_by("role", role, alls=True)

            if peers:
                feat_name = role + 's'
                feats[feat_name] = []

                for peer in peers:
                    peer_profile = peer.profile()
                    feats[feat_name].append(peer_profile)
        if feats:
            self.update_identity(feats)

    def add_peer(self, info):
        ack = self.peers.add(info)

        if ack:
            role = info.get('role')
            self.update_status([role])           

    def get_peers(self, field, types, alls):
        info = {}
        logger.info(f"Get all ({alls}) peers by {field} with value {types}")
        peers = self.peers.get_by(field, types, alls=alls)
        
        for peer in peers:
            uuid = peer.get("uuid")
            info[uuid] = peer        
        
        return info

    def allows(self, contacts):
        logger.info(f"Filtering contacts allowed by roles for {self.identity.get('role')}")
        allowed = []

        if contacts:
            for contact in contacts:
                role, _ = contact.split("/")
                if role in self.allowed_roles:
                    allowed.append(contact)
                else:
                    logger.info(f"Contact role {role} not allowed for {self.identity.get('role')}")

        return allowed
