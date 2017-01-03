'''
Implements the targetcli base UI node.

This file is part of targetcli.
Copyright (c) 2011-2013 by Datera, Inc

Licensed under the Apache License, Version 2.0 (the "License"); you may
not use this file except in compliance with the License. You may obtain
a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations
under the License.
'''

import six

from configshell_fb import ConfigNode, ExecutionError

class UINode(ConfigNode):
    '''
    oVirt Engine basic UI node.
    '''
    def __init__(self, name, parent=None, shell=None):
        ConfigNode.__init__(self, name, parent, shell)
        self.define_config_group_param(
            'global', 'auto_activate', 'bool',
            'If true, automatically activate objects upon creation.')
        self.define_config_group_param(
            'global', 'auto_cd_after_create', 'bool',
            'If true, changes current path to newly created objects.')
        self.define_config_group_param(
            'global', 'auto_save_on_exit', 'bool',
            'If true, saves configuration on exit.')
        self.define_config_group_param(
            'global', 'username', 'string',
            'Username to use to connect to oVirt Engine.')
        self._api = None
        self._ip = None

    def get_api(self):
        return self._api

    def is_connected(self):
        return (self._api is not None)

    def new_node(self, new_node):
        '''
        Used to honor global 'auto_cd_after_create'.
        Either returns None if the global is False, or the new_node if the
        global is True. In both cases, set the @last bookmark to last_node.
        '''
        self.shell.prefs['bookmarks']['last'] = new_node.path
        self.shell.prefs.save()
        if self.shell.prefs['auto_cd_after_create']:
            self.shell.log.info("Entering new node %s" % new_node.path)
            # Piggy backs on cd instead of just returning new_node,
            # so we update navigation history.
            return self.ui_command_cd(new_node.path)
        else:
            return None

    def refresh(self):
        '''
        Refreshes and updates the objects tree from the current path.
        '''
        for child in self.children:
            child.refresh()

    def ui_command_refresh(self):
        '''
        Refreshes and updates the objects tree from the current path.
        '''
        self.refresh()

    def ui_command_status(self):
        '''
        Displays the current node's status summary.

        SEE ALSO
        ========
        B{ls}
        '''
        description, is_healthy = self.summary()
        self.shell.log.info("Status for %s: %s" % (self.path, description))

    def ui_setgroup_global(self, parameter, value):
        ConfigNode.ui_setgroup_global(self, parameter, value)
        self.get_root().refresh()

    def ui_type_yesno(self, value=None, enum=False, reverse=False):
        '''
        UI parameter type helper for "Yes" and "No" boolean values.
        '''
        if reverse:
            if value is not None:
                return value
            else:
                return 'n/a'
        type_enum = ('Yes', 'No')
        syntax = '|'.join(type_enum)
        if value is None:
            if enum:
                return type_enum
            else:
                return syntax
        elif value in type_enum:
            return value
        else:
            raise ValueError("Syntax error, '%s' is not %s."
                             % (value, syntax))


