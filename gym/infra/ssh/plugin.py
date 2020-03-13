import os
import logging
import paramiko
import traceback


from gym.infra.base import Plugin


logger = logging.getLogger(__name__)


class Parser:
    def __init__(self):
        self.scenario = {}
        self.deploy = {}



class Environment:

    def ssh_keys(self):
        host_keys = {}
        try:
            host_keys = paramiko.util.load_host_keys(
                os.path.expanduser("~/.ssh/known_hosts")
            )
        except IOError:
            print("*** Unable to open host keys file")
            host_keys = {}
        finally:
            return host_keys
    
    def run(self, command):
        try:
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.WarningPolicy())
            print("*** Connecting...")
            if not UseGSSAPI and not DoGSSAPIKeyExchange:
                client.connect(hostname, port, username, password)
            else:
                try:
                    client.connect(
                        hostname,
                        port,
                        username,
                        gss_auth=UseGSSAPI,
                        gss_kex=DoGSSAPIKeyExchange,
                    )
                except Exception:
                    # traceback.print_exc()
                    password = getpass.getpass(
                        "Password for %s@%s: " % (username, hostname)
                    )
                    client.connect(hostname, port, username, password)

            # chan = client.invoke_shell()
            # print(repr(client.get_transport()))
            # print("*** Here we go!\n")
            # interactive.interactive_shell(chan)
            chan.close()
            client.close()

        except Exception as e:
            print("*** Caught exception: %s: %s" % (e.__class__, e))
            traceback.print_exc()
            try:
                client.close()
            except:
                pass
            sys.exit(1)


    def send_file(self, filesrc, filedst):
        try:
            t = paramiko.Transport((hostname, Port))
            t.connect(
                hostkey,
                username,
                password,
                gss_host=socket.getfqdn(hostname),
                gss_auth=UseGSSAPI,
                gss_kex=DoGSSAPIKeyExchange,
            )
            sftp = paramiko.SFTPClient.from_transport(t)

            # dirlist on remote host
            # dirlist = sftp.listdir(".")
            # print("Dirlist: %s" % dirlist)
      
            try:
                sftp.put(filesrc, filedst)
                sftp.get(filesrc, filedst)

            except IOError:
                print("(assuming demo_sftp_folder/ already exists)")
            
            t.close()

        except Exception as e:
            print("*** Caught exception: %s: %s" % (e.__class__, e))
            traceback.print_exc()
            try:
                t.close()
            except:
                pass
            

class SSHPlugin(Plugin):
    def __init__(self):
        Plugin.__init__(self)

    async def start(self, scenario):
        ack, info = False, {}
        return ack, info

    async def stop(self, scenario):
        ack, info = False, {}
        return ack, info