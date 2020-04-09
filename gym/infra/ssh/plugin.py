import os
import re
import logging
import paramiko
import traceback
from scp import SCPClient, SCPException


from gym.infra.base import Plugin


logger = logging.getLogger(__name__)


class Parser:
    def __init__(self):
        self.scenario = {}
        self.deploy = {}

    def parse_nodes(self):
        nodes = self.scenario.get("nodes", {})
        deploy_nodes = self.deploy.setdefault("nodes", {})

        for node_id, node in nodes.items():
            lifecycle = node.get("lifecycle")
            
            node_info = {
                "configure": lifecycle.get("configure", {}),
                "start": lifecycle.get("start", {}),
                "stop": lifecycle.get("stop", {})
            }
            
            deploy_nodes.update( {node_id: node_info} )

        logger.debug(f"Parsed nodes {self.deploy}")

    def parse(self, scenario):
        self.scenario = scenario
        self.parse_nodes()
        return self.deploy


class SSHProxy:
    def __init__(self):
        self._cfg = None
        self._client = None

    def cfg(self, cfg):
        logger.debug(f"SSHProxy cfg set: {cfg}")
        self._cfg = cfg

    def _connect(self):
        connect_flag = True
        try:
            self._client = paramiko.SSHClient()
            # self._client.load_system_host_keys()
            self._client.set_missing_host_key_policy(paramiko.WarningPolicy())
            
            self._client.connect(
                hostname=self._cfg.get("address").get("value"), 
                port=self._cfg.get("port").get("value"),
                username=self._cfg.get("user").get("value"),
                password=self._cfg.get("password").get("value"),
                look_for_keys=False,
                timeout=60,
            )      
        
        except Exception as e:
            logger.debug(f"ssh connect exception: {e.__class__}, {e}")
            traceback.print_exc()
            
            try:
                self._client.close()
            except:
                pass
            finally:
                connect_flag = False
                self._client = None
        
        finally:
            return connect_flag

    def execute_command(self, command):
        """Execute a command on the remote host."""

        self.ssh_output = None
        result_flag = True
        result = ""

        try:
            if self._connect():                
                logger.info("Executing command --> {}".format(command))
                _, stdout, stderr = self._client.exec_command(command, timeout=60)
                self.ssh_output = stdout.read()
                self.ssh_error = stderr.read()
                
                if self.ssh_error:
                    logger.info(f"Problem occurred while running command: error {self.ssh_error}")
                    result_flag = False
                    result = self.ssh_error
                else:    
                    logger.info(f"Command execution completed successfully: output {self.ssh_output}")
                    result = self.ssh_output
                
                self._client.close()
            else:
                print("Could not establish SSH connection")
                result_flag = False   
        
        except paramiko.SSHException:
            logger.info(f"Failed to execute the commands {command}")
            self._client.close()
            result_flag = False    
 
        return result_flag, result

    def upload_file(self, local_filepath, remote_filepath):
        """This method uploads a local file to a remote server"""
        
        result_flag = True
        if self._connect():
            try:
            
                self.scp = SCPClient(self._client.get_transport())
                
                self.scp.put(local_filepath,
                            recursive=True,
                            remote_path=remote_filepath)
                
                self._client.close()
    
            except Exception as e:
                logger.info(f"Unable to upload the file {local_filepath}"
                            f" to the remote server - exception {e}")
                
                result_flag = False
                self._client.close()
        else:
            logger.info("Could not establish SSH connection")
            result_flag = False  
    
        return result_flag


class Environment:
    def __init__(self):
        self.proxy = SSHProxy()
        self._ssh_cfg = {}
        self._config = {}

    def _get_mng_host_ip(self, node_id):
        logger.info(f"Get management ip address from node {node_id}")

        cfg = self._ssh_cfg.get(node_id, None)
        if not cfg:
            cfg = self._get_ssh_cfg(node_id)            
        
        if cfg:
            self.proxy.cfg(cfg)

        intf = 'eth0'
        command = "ifconfig {} 2>/dev/null".format(intf)
        ack, config = self.proxy.execute_command(command)
        
        if ack: 
            if not config:
                logger.info(f"Error: {intf} does not exist!")
            else:
                ips = re.findall( r'\d+\.\d+\.\d+\.\d+', config.decode("utf-8") )
                if ips:
                    logger.info(f"Node {node_id} intf ips {ips}")
                    ips_dict = {'ip': ips[0], 'broadcast': ips[1], 'mask': ips[2]}
                    return ips_dict
                else:
                    logger.info(f"Node {node_id} has no intf ips {ips}")
    
        else:
            logger.info(f"Could not get node {node_id} intf ips")

        return None

    def _format_workflow(self, node_id, workflow):
        logger.info(f"Formating workflow for {node_id}")

        node_info = self._get_mng_host_ip(node_id)

        implementations = workflow.get("implementation")
        parameters = workflow.get("parameters")
        fmt_kwargs = {}
        
        entrypoints = []

        if parameters:
            kwargs = { param.get("input"):param.get("value") 
                        for param in parameters.values() }
            
            for k,v in kwargs.items():
                args = v.split(":")
                call = args[0]
   
                if call == "get_attrib":
                    attrib = args[1]
   
                    if attrib == "ip":
                        node_attrib = node_info.get(attrib, None)
                        if node_attrib:
                            fmt_kwargs[k] = node_attrib
                else:
                    fmt_kwargs[k] = v
   
            for implementation in implementations:
                entrypoint = implementation.format(**fmt_kwargs)
                entrypoints.append(entrypoint)
        else:
            entrypoints = implementations
            
        return entrypoint

    def _get_ssh_cfg(self, node_id):
        try:
            cfg = self._config.get("nodes").get(node_id).get("configure").get("parameters")
        except Exception as e:
            logger.info(f"Could not locate node {node_id} ssh configuration in workflows - {e}")
            cfg = {}
        finally:
            self._ssh_cfg.setdefault(node_id, cfg)
            return cfg

    def _is_gym_configure_map(self, step):
        gym_maps = ["ssh-copy:gym", "ssh-install:gym"]
        ack = True if step in gym_maps else False
        return ack

    def _filepath(self, filename):
        filepath = os.path.join(
            os.path.abspath(os.path.curdir), 
            filename)
        return filepath

    def _gym_configure_map(self, step):
        local_filepath = self._filepath("files/gym.tar.xz")
        
        steps_map = {
            "ssh-copy:gym": {
                "type": "push",
                "local": local_filepath,
                "remote": "/home/gym/"
            },
            "ssh-install:gym": {
                "type": "cmd",
                "cmd": "cd /home/gym/ && tar xf gym.tar.xz && "
                       "cd gym && sudo python3.7 setup.py install"
            }
        }
        
        step_map = steps_map.get(step, None)
        return step_map               

    def _configure(self, node_id, workflow):
        cfg = self._ssh_cfg.setdefault(node_id, workflow.get("parameters"))
        
        if cfg:
            self.proxy.cfg(cfg)
            steps = workflow.get("implementation", [])
            
            for step in steps:
                
                if self._is_gym_configure_map(step):
                    step_map = self._gym_configure_map(step)

                    if step_map.get("type") == "push":
                        local_path = step_map.get("local")
                        remote_path = step_map.get("remote")
                        logger.info(f"SSH configure: push file local in {node_id} "
                                    f"{local_path} to remote {remote_path}")

                        ack = self.proxy.upload_file(local_path, remote_path)
                        logger.info(f"SSH configure: push file ran {ack}")

                    elif step_map.get("type") == "cmd":
                        command = step_map.get("cmd")
                        logger.info(f"SSH configure: run command "
                                    f"{command} remotely in {node_id}")
                        
                        ack, _ = self.proxy.execute_command(command)
                        logger.info(f"SSH configure: command ran {ack}")

                    else:
                        raise Exception(f"Uknown ssh step type - {step_map} -"
                                        f"in configure workflow")

                else:
                    #TODO: create syntax for other types of ssh step implementation commands
                    raise Exception(f"Uknown ssh configure step - {step} -"
                                    f"in configure workflow")           
        else:
            return False       

    def _start(self, node_id, workflow):
        acks = []
        
        cfg = self._ssh_cfg.get(node_id, None)
        if not cfg:
            cfg = self._get_ssh_cfg(node_id)            
        
        if cfg:
            self.proxy.cfg(cfg)
            commands = self._format_workflow(node_id, workflow)

            for command in commands:                
                logger.info(f"SSH start: run command "
                            f"{command} remotely in {node_id}")
                
                ack, _ = self.proxy.execute_command(command)
                logger.info(f"SSH start: command ran {ack}")

                acks.append(ack)
            
            all_acks = all(acks)
            return all_acks

        else:
            return False

    def _stop(self, node_id, workflow):
        acks = []
        cfg = self._ssh_cfg.get(node_id, None)
        
        if not cfg:
            cfg = self._get_ssh_cfg(node_id)            
        
        if cfg:
            self.proxy.cfg(cfg)
            commands = self._format_workflow(node_id, workflow)

            for command in commands:                
                logger.info(f"SSH stop: run command "
                            f"{command} remotely in {node_id}")
                
                ack = self.proxy.execute_command(command)
                logger.info(f"SSH stop: command ran {ack}")
                acks.append(ack)

            all_acks = all(acks)
            return all_acks
        
        else:
            return False

    def _nodes_info(self):
        info = {}

        for node_id in self._config.get("nodes"):
            node_ips = self._get_mng_host_ip(node_id)
            info.setdefault(node_id, node_ips)

        return info

    def start(self, config):
        acks = []
        self._config = config 

        for node_id, workflows in config.get("nodes").items():

            configure = workflows.get("configure", {})
            if configure:
                self._configure(node_id, configure)


            start = workflows.get("start", {})
            if start:
                ack = self._start(node_id, start)
                acks.append(ack)
        
        if all(acks):
            info = self._nodes_info()
            return True, info

        else:
            return False, {}

    def stop(self, config):
        acks = []
        for node_id, workflows in config.get("nodes").items():
            stop = workflows.get("stop", {})

            if stop:
                ack = self._stop(node_id, stop)
                acks.append(ack)
        
        if all(acks):
            info = self._nodes_info()
            return True, info

        else:
            return False, {}


class SSHPlugin(Plugin):
    def __init__(self):
        Plugin.__init__(self)
        self.parser = Parser()
        self.env = Environment()

    async def start(self, scenario):
        ack, info = False, {}
        deploy = self.parser.parse(scenario)
        ack, info = self.env.start(deploy)
        return ack, info

    async def stop(self, scenario):
        ack, info = False, {}
        deploy = self.parser.parse(scenario)
        ack, info = self.env.stop(deploy)
        return ack, info