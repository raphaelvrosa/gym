import os
import json
import logging
import asyncio

logger = logging.getLogger(__name__)


class Loader:
    def __init__(self):
        self._files = []

    def files(self, folder=None, prefix=None, suffix=None, full_path=False):
        self._load(folder, prefix, suffix, full_path)
        logger.debug(f'Loaded files: {self._files}')
        return self._files

    def _get(self, root, file, full_path):
        p = os.path.join(root, file)
        if full_path:
            file_path = os.path.abspath(p)
            self._files.append(file_path)
        else:
            self._files.append(file)

    def _load(self, folder=None, prefix=None, suffix=None, full_path=False):
        logger.debug(f'Loading files in folder {folder} -\
                        prefix {prefix} and suffix {suffix} - full path {full_path}')
        for root, _, files in os.walk(folder):
            for f in files:
                if f.startswith(prefix):
                    if suffix:
                        if f.endswith(suffix):
                            self._get(root, f, full_path)
                    else:
                        self._get(root, f, full_path)
            break
     

class Handler:

    def parse(self, call):
        cmd = ['/usr/bin/python3.7']

        if type(call) is list:
            fields = [str(c) for c in call]
        else:
            fields = call.split(' ')
                
        cmd.extend(fields)
        cmd_str = ' '.join(cmd)
        return cmd_str
   
    async def call(self, cmd):
        out = {}
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)

            stdout, stderr = await proc.communicate()

            out = {
                "stdout": stdout, 
                "stderr": stderr,
            }
        
        except OSError as excpt:
            logger.debug(f'Could not call cmd {cmd} - exception {excpt}')
            
            out = {
                "stdout": None, 
                "stderr": proc.exception(),
            }

        finally:
            return out

    async def build(self, calls):
        aws = []
        for call in calls.values():
            cmd = self.parse(call)
            aw = self.call(cmd)
            aws.append(aw)

        return aws

    async def run(self, calls):
        results = {}

        aws = await self.build(calls)
        tasks = await asyncio.gather(*aws, return_exceptions=True)

        calls_ids = list(calls.keys())
        counter = 0

        for aw in tasks:
            uid = calls_ids[counter]

            if isinstance(aw, Exception):
                logger.debug(f'Could not run call {calls[uid]} - exception {aw}')
            else:
                results[uid] = aw
            
            counter += 1

        return results

    async def run_serial(self, calls):
        outputs = {}
        
        for uuid, call in calls.items():
            cmd = self.parse(call)
            logger.debug(f'Running {cmd}')
            output =  await self.call(cmd)
            outputs[uuid] = output
        
        return outputs


class Tools:
    def __init__(self):
        self.loader = Loader()
        self.handler = Handler()
        self._cfg = {}
        self._files = {}
        self._info = {}
        
    def cfg(self, config):
        keys = ["folder", "prefix", "suffix", "full_path"]
        if all([True if k in config else False for k in keys]):
            self._cfg = config
            return True
        return False
            
    async def load(self):
        files = self.loader.files(**self._cfg)

        calls = {key: [files[key], '--info'] for key in range(len(files))}
        outputs = await self.handler.run_serial(calls)
            
        for uuid, out in outputs.items():
            stdout = out.get("stdout", None)
            
            if stdout:                             
                info = json.loads(stdout)
                self._files[info['id']] = files[uuid]
                self._info[info['id']] = info
            else:
                expt = out.get("stderr", {})
                logger.debug(f'Could not get info from {files[uuid]} - exception {expt}')
        
        logger.debug(f'Info obtained from tools: {self._info}')

    def info(self):
        return self._info

    def _build_calls(self, actions):
        calls = {}

        for uid,action in actions.items():
            act_id = action.get("id")

            if act_id in self._files:
                act_args = action.get("args")

                call_file = self._files.get(act_id)
                call_args = [ "--" + key + " " + str(value) for key,value in act_args.items() ]

                call = [call_file]
                call.extend(call_args)

                calls[uid] = call
        return calls

    def _parse_stdout(self, uid, stdout):
        out = {}

        try:
            out = json.loads(stdout)
        except Exception as e:
            logger.info(f"Could not parse tool {uid} stdout - exception {e}")
        else:
            metrics = {}
            for metric in out.get("metrics"):
                name = metric.get("name")
                metrics[name] = metric
            
            out["id"] = uid
            out["metrics"] = metrics
        
        finally:
            return out

    def _build_outputs(self, results):
        outputs = {}
        
        for uid,result in results.items():
            stdout = result.get("stdout")
            
            if stdout:                             
                out = self._parse_stdout(uid, stdout)
                outputs[uid] = out

            else:
                expt = result.get("stderr")
                logger.debug(f'Could not run instruction {uid} - exception {expt}')
        
        logger.debug(f'Instructions outputs: {outputs}')
        return outputs

    async def handle(self, actions):   
        logger.info("Handling actions")
        calls = self._build_calls(actions)
        logger.info(f"Calls for: {calls}")
        results = await self.handler.run(calls)
        outputs = self._build_outputs(results)
        logger.info(f"Outputs: {outputs}")
        return outputs
        


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.DEBUG)

    tools = Tools()
    tools_cfg = {
            "folder": "/home/raphael/play/gym/gym/agent/probers",
            "prefix": 'prober_',
            "suffix": 'py',
            "full_path": True,
    }
    if tools.cfg(tools_cfg):
        asyncio.run(tools.load())
        
    actions = {
        1: {
            'id': 2,
            'args': {
                'packets': 3,
                'target': '8.8.8.8',
            }
        },
        2: {
            'id': 2,
            'args': {
                'packets': 2,
                'target': '1.1.1.1',
            }
        }
    }

    asyncio.run(tools.handle(actions))
    