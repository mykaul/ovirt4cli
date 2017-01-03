#!/usr/bin/python2
'''
Starts the oVirtCLI shell.

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

from __future__ import print_function

from os import getuid
from ovirtcli import UIRoot
from configshell_fb import ConfigShell, ExecutionError
import sys
from ovirtcli import __version__ as ovirtcli_version

err = sys.stderr

class oVirtCLI(ConfigShell):
    default_prefs = {'color_path': 'magenta',
                     'color_command': 'cyan',
                     'color_parameter': 'magenta',
                     'color_keyword': 'cyan',
                     'completions_in_columns': True,
                     'logfile': None,
                     'loglevel_console': 'info',
                     'loglevel_file': 'debug9',
                     'color_mode': True,
                     'prompt_length': 30,
                     'tree_max_depth': 0,
                     'tree_status_mode': True,
                     'tree_round_nodes': True,
                     'tree_show_root': True,
                     'auto_cd_after_create': False,
                     'auto_save_on_exit': True,
                    }

def usage():
    print("Usage: %s [--version|--help|CMD]" % sys.argv[0], file=err)
    print("  --version\t\tPrint version", file=err)
    print("  --help\t\tPrint this information", file=err)
    print("  CMD\t\t\tRun ovirtcli shell command and exit", file=err)
    print("  <nothing>\t\tEnter configuration shell", file=err)
    sys.exit(-1)

def version():
    print("%s version %s" % (sys.argv[0], ovirtcli_version), file=err)
    sys.exit(-1)

def main():
    '''
    Start the oVirtcli shell.
    '''
    shell = oVirtCLI('~/.ovirtcli')

    try:
        root_node = UIRoot(shell)
        root_node.refresh()
    except Exception as error:
        shell.con.display(shell.con.render_text(str(error), 'red'))
        sys.exit(-1)

    if len(sys.argv) > 1:
        if sys.argv[1] in ("--help", "-h"):
            usage()

        if sys.argv[1] in ("--version", "-v"):
            version()

        try:
            shell.run_cmdline(" ".join(sys.argv[1:]))
        except Exception as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
        sys.exit(0)

    shell.con.display("oVirtcli shell version %s\n"
                      "For help on commands, type 'help'.\n"
                      % ovirtcli_version)
    while not shell._exit:
        try:
            shell.run_interactive()
        except Exception as msg:
            shell.log.error(str(msg))

    root_node.ui_command_disconnect()
    if shell.prefs['auto_save_on_exit']:
        shell.log.info("Global pref auto_save_on_exit=true")
        root_node.ui_command_saveconfig()


if __name__ == "__main__":
    main()
