""""
Implements the OVIRTcli root UI.

Licensed under the Apache License, Version 2.0 (the "License"); you may
not use this file except in compliance with the License. You may obtain
a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations
under the License.
"""

import os
import shutil
import stat
from datetime import datetime
from glob import glob

import ovirtsdk4 as sdk

from configshell_fb import ExecutionError

from .ui_ovirtcli import complete_path
from .ui_node import UINode

from .ui_ovirtcli import UIData_centers, UIClusters, UIStorage_domains, UITemplates, UIVMs, UIHosts

default_save_file = "~/ovirtlcli.json"
kept_backups = 10


class UIRoot(UINode):
    """
    The ovirtcli hierarchy root node.
    """

    def __init__(self, shell, as_admin=True):
        UINode.__init__(self, '/', shell=shell)
        self.as_admin = as_admin
        self._api = None

    def refresh(self):
        """
        Refreshes the tree of oVirt modules.
        """
        self._children = set([])

        if self._api is not None:
            UIData_centers(self, self._api)
            UIClusters(self, self._api)
            UIHosts(self, self._api)
            UIStorage_domains(self, self._api)
            UITemplates(self, self._api)
            UIVMs(self, self._api)

    def ui_command_connect(self, username, password, ip):
        """
        Connect to oVirt Engine
        :param username: the username used to connect
        :param password: the password used to connect
        :param url: the host name of the oVirt engine
        :return: None
        """

        if self._api is not None:
            self.shell.log.info("Already connected. Disconnect first")

        full_url = 'https://%s/ovirt-engine/api' % ip

        self.shell.log.info("Connecting to %s..." % ip)

        self._api = sdk.Connection(
            url=full_url,
            username=username,
            password=password,
            insecure=True,
        )

        if self._api is None:
            self.shell.log.info("Failed to create API object ")
            return False

        if not self._api.test(raise_exception=False):
            self.shell.log.info("Failed to test connection to oVirt Engine.")
        else:
            self.shell.log.info("Connected to oVirt Engine.")
            self._ip = ip
            self.refresh()

    def ui_command_disconnect(self):
        if self._api is not None:
            self._api.close()
            self._api = None
            self._ip = None
            self.shell.log.info('Disconnected from oVirt Engine.')
        else:
            self.shell.log.info('Already disconnected from oVirt Engine.')
        self.refresh()

    def ui_command_saveconfig(self, savefile=default_save_file):
        """
        Saves the current configuration to a file so that it can be restored
        on next boot.
        """

        savefile = os.path.expanduser(savefile)

        # Only save backups if saving to default location
        if savefile == default_save_file:
            backup_dir = os.path.dirname(savefile) + "/backup"
            backup_name = "saveconfig-" + \
                          datetime.now().strftime("%Y%m%d-%H:%M:%S") + ".json"
            backupfile = backup_dir + "/" + backup_name
            with ignored(IOError):
                shutil.copy(savefile, backupfile)

            # Kill excess backups
            backups = sorted(glob(os.path.dirname(savefile) + "/backup/*.json"))
            files_to_unlink = list(reversed(backups))[kept_backups:]
            for f in files_to_unlink:
                os.unlink(f)

            self.shell.log.info("Last %d configs saved in %s." % \
                                (kept_backups, backup_dir))

        # self.rtsroot.save_to_file(savefile)

        self.shell.log.info("Configuration saved to %s" % savefile)

    def ui_command_restoreconfig(self, savefile=default_save_file, clear_existing=False):
        '''
        Restores configuration from a file.
        '''
        self.assert_admin()

        savefile = os.path.expanduser(savefile)

        if not os.path.isfile(savefile):
            self.shell.log.info("Restore file %s not found" % savefile)
            return

        # errors = self.rtsroot.restore_from_file(savefile, clear_existing)

        self.refresh()

        if errors:
            raise ExecutionError("Configuration restored, %d recoverable errors:\n%s" % \
                                 (len(errors), "\n".join(errors)))

        self.shell.log.info("Configuration restored from %s" % savefile)

    def ui_complete_saveconfig(self, text, current_param):
        """
        Auto-completes the file name
        """
        if current_param != 'savefile':
            return []
        completions = complete_path(text, stat.S_ISREG)
        if len(completions) == 1 and not completions[0].endswith('/'):
            completions = [completions[0] + ' ']
        return completions

    ui_complete_restoreconfig = ui_complete_saveconfig

    def ui_command_version(self):
        """
        Displays the oVirtcli and support libraries versions.
        """
        from ovirtcli import __version__ as ovirtcli_version
        self.shell.log.info("oVirtcli version %s" % ovirtcli_version)
