import logging
import platform as pl
import psutil as ps


logger = logging.getLogger(__name__)


class Environment:
    def __init__(self):
        self._info = self._node()

    def info(self):
        return self._info

    def _get_node_info(self):
        info = {}
        system, node, release, version, _, processor = pl.uname()
        info["system"] = system
        info["host"] = node
        info["release"] = release
        info["version"] = version
        info["processor"] = processor
        return info

    def _get_node_cpu(self):
        cpu = {}
        cpu["logical"] = ps.cpu_count(logical=True)
        cpu["cores"] = ps.cpu_count(logical=False)
        return cpu

    def _get_node_mem(self):
        mem = {}
        mem["pyshical"] = ps.virtual_memory().total
        mem["swap"] = ps.swap_memory().total
        return mem

    def _get_node_storage(self):
        total = ps.disk_usage("/").total
        percent = ps.disk_usage("/").percent

        storage = {
            "total": total,
            "percent": percent,
        }
        return storage

    def _get_node_net(self):
        net = {}
        addrs = ps.net_if_addrs()

        for face in addrs:
            face_addrs = [addr for addr in addrs[face] if addr.family == 2]

            if face_addrs:
                face_addr = face_addrs.pop()
                net[face] = face_addr.address

        return net

    def _get_node_resources(self):
        resources = {}
        resources["cpu"] = self._get_node_cpu()
        resources["memory"] = self._get_node_mem()
        resources["disk"] = self._get_node_storage()
        resources["network"] = self._get_node_net()
        return resources

    def _node(self):
        """Extracts environment info using psutil
        containing details of host system/platform/release
        and resources (cpu, mem, disk, net)
        It is the only/main interface for this class
        that puts all the info in a single dict

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
        logger.info(
            f"Identity built: uuid {self.uuid} for {self.role} at {self.address}"
        )
        self.load_env(env)

    def load_env(self, env):
        """Load environment information using Environment class
        only if env True
        Only used for Apps running to extract system features
        The case env=False happens when Peers class adds a contact
        via exchange of info provided by other peer

        Arguments:
            env {bool} -- Loads or not environment features
        """
        if env:
            self.environment = self._env.info()
            logger.info(f"Identity environment info loaded/extracted")
        else:
            logger.info(f"Identity environment imported")

    def validate(self, roles):
        """Validates if info provided for identity is valid
        and identity role is among list of roles

        Arguments:
            roles {list} -- Set of roles in which self.role must be
            contained

        Returns:
            bool -- True if uuid, role, address are provided
            and role sits inside set of roles listed
        """
        if self.uuid and self.role and self.address:
            if self.role in roles:
                return True
            else:
                logger.info(
                    f"Role {self.role} not allowed for identity - "
                    f"accepts only {roles}"
                )
        else:
            logger.info(
                f"Mandatory fields not provided for Identity"
                f"uuid {self.uuid} and/or role {self.role} and/or address {self.address}"
            )
        return False

    def get(self, param):
        """Gets a param inside the class fields

        Arguments:
            param {string} -- A class field param

        Returns:
            [type] -- A value of a class field named by param
            that can be: None, string, list or dict
        """
        value = getattr(self, param, None)
        return value

    def set(self, param, value):
        """Sets a value for a class param field
        if param type is a dict, the dict is updated

        Arguments:
            param {string} -- Name of the class param
            value {[type]} -- Value of the class param

        Returns:
            bool -- True if field exists and was set
            False otherwise
        """
        if hasattr(self, param):
            field = getattr(self, param)

            if type(field) is dict:
                field.update(value)
            else:
                setattr(self, param, value)
            return True

        return False

    def profile(self, filter_fields=None):
        """Returns the identity profile
        i.e., all the main fields of an identity
        if filter_fields defined only provide the 
        list of fields in filter_fields

        profile() is used to feed the Info messages
        when a peer exchanges info messages with another peer

        Keyword Arguments:
            filter_fields {list} -- List of fields to be inside
            the identity profile (default: {None})

        Returns:
            dict -- Info of the indentity containing
            all the fields (possibly filtered)
        """
        info = {}

        if filter_fields:
            fields = filter_fields
        else:
            fields = [
                "uuid",
                "role",
                "address",
                "environment",
                "apparatus",
                "artifacts",
            ]

        for k, v in self.__dict__.items():
            if k in fields:
                info[k] = v

        return info

    def update(self, info):
        """Updates the identity attributes according to the
        info provided

        Arguments:
            info {dict} -- Set of information that might
            update the identity attributes
            Must contain one or all the fields listed below
        """
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
        """Adds a peer to peers dict indexed by its 
        (uuid,address), uses info to create Identity for
        peer and validate it
        i.e., each peer is an instance of Identity class
        If peer key (uuid, address) already exist in self.peers
        database, then updates the peer (Identity) info

        Arguments:
            info {dict} -- Set of fields needed to instantiate
            and validate an Identity for a peer to be added 

        Returns:
            bool -- True if peer was added, False if it was not added
            or if it was updated
        """
        uuid = info.get("uuid")
        address = info.get("address")
        peer_key = (uuid, address)

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
            logger.info(
                f"Peer not added: already existing peer (uuid,address) {peer_key}"
            )
            peer = self.peers[peer_key]
            peer.update(info)
            logger.info(
                f'Peer existent info updated: uuid {uuid} role {peer.get("role")}'
            )

        return False

    def clear(self):
        """Clear the peers database
        containing all the peers Identity instances
        """
        self.peers.clear()
        logger.info(f"Peers deleted/cleared")

    def del_peer(self, peer):
        """Deletes a peer Identity from the peers
        database

        Arguments:
            peer {Identity} -- The peer dict or Identity
            to be deleted

        Returns:
            bool -- True if peer was deleted, False otherwise
        """

        uuid = peer.get("uuid")
        address = peer.get("uuid")
        peer_index = (uuid, address)

        if peer_index in self.peers:
            del self.peers[peer_index]
            logger.info(f"Peer {peer_index} deleted")
            return True
        else:
            logger.info(f"Peer {peer_index} not existent/deleted")
            return False

    def get_by(self, field, value, alls=False):
        """Gets one (or all the) peer(s) that match
        a specific field==value

        Arguments:
            field {string} -- An Identity field name
            value {[type]} -- The value that to be looked into
            (matched) the peer field name

        Keyword Arguments:
            alls {bool} -- If all peers matching the field==value must be 
            returned in a list (default: {False})

        Returns:
            [type] -- A list (of peers) | peer | None type
        """
        filtered_peers = [
            peer for peer in self.peers.items() if peer.get(field) == value
        ]
        if alls:
            return filtered_peers
        else:
            try:
                peer = filtered_peers.pop()
            except IndexError:
                peer = None
            finally:
                return peer


class Status(Identity):
    def __init__(self, info):
        Identity.__init__(self, info, env=True)
        self.peers = Peers()
        self.allowed_roles = []
        self.cfg_roles()

    def cfg_roles(self):
        """Set the allowed roles of peers that
        a Peer is allowed to have in its contacts
        For instance, an Agent can only communicate with
        a Manager component
        """
        role = self.role

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

    def update_apparatus(self, peer):
        """Updates Identity apparatus with peer profile
        Only updates apparatus if role is manager or player

        Arguments:
            peer {Identity} -- The identity of peer that will 
            have its profile included in the apparatus of the 
            Status Identity
        """
        role = self.role
        if role == "player" or role == "manager":
            
            peer_role = peer.get("role")
            peers = [peer.profile() for peer in self.peers.get_by("role", peer_role, alls=True)]
            
            apparatus_roles = peer_role + "s"
            apparatus = {
                apparatus_roles: peers
            }
            
            logger.info(f"Updating identity apparatus")
            logger.debug(f"{apparatus}")
            self.set("apparatus", apparatus)

    def add_peer(self, info):
        """Adds a peer Identity using info
        and updates status Identity apparatus

        Arguments:
            info {dict} -- Set of fields/values that
            build a valid Identity
        """
        ack = self.peers.add(info)

        if ack:
            role = info.get("role")
            self.update_apparatus([role])

    def get_peers(self, field, value):
        """Gets all the peers that contain
        a specific field matching a defined value

        Arguments:
            field {string} -- Field name of peer Identity
            value {[type]} -- 

        Returns:
            dict -- All peers indexed by uuid that match field==value
        """
        info = {}
        logger.info(f"Get all peers by {field} with value {value}")
        peers = self.peers.get_by(field, value, alls=True)

        for peer in peers:
            uuid = peer.get("uuid")
            info[uuid] = peer

        return info

    def allows(self, contacts):
        """Checks and filter only allowed contacts
        based on allowed_roles that each contact
        is allowed to peer with

        Arguments:
            contacts {list} -- Set of contacts (role/ip:address)

        Returns:
            list -- Set of filtered contacts containing only 
            allowed_roles
        """
        logger.info(
            f"Filtering contacts allowed by roles for {self.get('role')}"
        )
        allowed = []

        if contacts:
            for contact in contacts:
                role, _ = contact.split("/")
                if role in self.allowed_roles:
                    allowed.append(contact)
                else:
                    logger.info(
                        f"Contact role {role} not allowed for {self.get('role')}"
                    )

        return allowed
