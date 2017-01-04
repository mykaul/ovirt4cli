'''
Implements the targetcli backstores related UI.

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

import glob
import os
import re
import stat
import time

import ovirtsdk4 as sdk
import ovirtsdk4.types as types

from configshell_fb import ExecutionError

from .ui_node import UINode

def human_to_bytes(hsize, kilo=1024):
    '''
    This function converts human-readable amounts of bytes to bytes.
    It understands the following units :
        - I{B} or no unit present for Bytes
        - I{k}, I{K}, I{kB}, I{KB} for kB (kilobytes)
        - I{m}, I{M}, I{mB}, I{MB} for MB (megabytes)
        - I{g}, I{G}, I{gB}, I{GB} for GB (gigabytes)
        - I{t}, I{T}, I{tB}, I{TB} for TB (terabytes)

    Note: The definition of I{kilo} defaults to 1kB = 1024Bytes.
    Strictly speaking, those should not be called I{kB} but I{kiB}.
    You can override that with the optional kilo parameter.

    @param hsize: The human-readable version of the Bytes amount to convert
    @type hsize: string or int
    @param kilo: Optional base for the kilo prefix
    @type kilo: int
    @return: An int representing the human-readable string converted to bytes
    '''
    size = hsize.replace('i', '')
    size = size.lower()
    if not re.match("^[0-9]+[k|m|g|t]?[b]?$", size):
        raise RTSLibError("Cannot interpret size, wrong format: %s" % hsize)

    size = size.rstrip('ib')

    units = ['k', 'm', 'g', 't']
    try:
        power = units.index(size[-1]) + 1
    except ValueError:
        power = 0
        size = int(size)
    else:
        size = int(size[:-1])

    return size * (int(kilo) ** power)

def bytes_to_human(size):
    kilo = 1024.0

    # don't use decimal for bytes
    if size < kilo:
        return "%d bytes" % size
    size /= kilo

    for x in ['KiB', 'MiB', 'GiB', 'TiB', 'PiB']:
        if size < kilo:
            return "%3.1f%s" % (size, x)
        size /= kilo

def complete_path(path, stat_fn):
    filtered = []
    for entry in glob.glob(path + '*'):
        st = os.stat(entry)
        if stat.S_ISDIR(st.st_mode):
            filtered.append(entry + '/')
        elif stat_fn(st.st_mode):
            filtered.append(entry)

    # Put directories at the end
    return sorted(filtered,
                  key=lambda s: '~'+s if s.endswith('/') else s)

class UIData_centers(UINode):
    """
    The data centers container UI.
    """
    def __init__(self, parent, api):
        UINode.__init__(self, 'Datacenters', parent)
        self._dcs_service = api.system_service().data_centers_service()
        self.refresh()

    def refresh(self):
        self._children = set([])
        dcs = self._dcs_service.list()
        if dcs is not None:
            for dc in dcs:
                UIData_center(self, dc, dc.name)

    def summary(self):
        dcs = self._dcs_service.list()
        return 'Data Centers: %d' % len(dcs), None

    def ui_command_create(self, name, description=None, local=False):
        dc = self._dcs_service.add(
            types.DataCenter(
                name=name,
                description=description if description is not None else '',
                local=local,
            ),
        )
        self.refresh()

    def ui_command_delete(self, name):
        filter = 'name=%s' % name
        try:
            dc = self._dcs_service.list(search=filter)[0]
        except:
            self.shell.log.info('Data center %s not found. Check spelling' % name)
            return

        dc_service = self._dcs_service.data_center_service(dc.id)
        dc_service.remove()
        self.refresh()


class UIData_center(UINode):
    """
    A single data center object UI.
    """
    def __init__(self, parent, data_center, name):
        UINode.__init__(self, name, parent)
        self._data_center = data_center
        self._parent = parent
        self.refresh()

    def refresh(self):
        self._children = set([])

    def summary(self):
        return 'Data Center: %s' % self._data_center.name, None

    def ui_command_delete(self):
        self._parent.ui_command_delete(self._data_center.name)


class UIClusters(UINode):
    """
    A clusters UI.
    """
    def __init__(self, parent, api):
        UINode.__init__(self, 'Clusters', parent)
        self._clusters_service = api.system_service().clusters_service()
        self.refresh()

    def refresh(self):
        self._children = set([])
        clusters = self._clusters_service.list()
        if clusters is not None:
            for cluster in clusters:
                UICluster(self, cluster, cluster.name)

    def summary(self):
        clusters = self._clusters_service.list()
        return 'Clusters: %d' % len(clusters), None


class UICluster(UINode):
    """
    A single cluster UI
    """
    def __init__(self, parent, cluster, name):
        UINode.__init__(self, name, parent)
        self._cluster = cluster
        self.refresh()

    def refresh(self):
        self._children = set([])

    def summary(self):
        cpu = self._cluster.cpu
        return 'Cluster:%s' % cpu.type, None


class UIStorage_domains(UINode):
    """
    A Storage Domains UI.
    """
    def __init__(self, parent, api):
        UINode.__init__(self, 'Storagedomains', parent)
        self._sds_service = api.system_service().storage_domains_service()
        self.refresh()

    def refresh(self):
        self._children = set([])
        sds = self._sds_service.list()
        if sds is not None:
            for sd in sds:
                UIStorage_domain(self, sd, sd.name)

    def summary(self):
        sds = self._sds_service.list()
        return 'Storage Domains: %d' % len(sds), None


class UIStorage_domain(UINode):
    """
    A single storage domain UI object.
    """
    def __init__(self, parent, sd, name):
        UINode.__init__(self, name, parent)
        self._sd = sd
        self._parent = parent
        self.refresh()

    def refresh(self):
        self._children = set([])

    def summary(self):
        return 'type: %s, status: %s' % (self._sd.type, self._sd.status), None


class UIHosts(UINode):
    """
    A Hosts objects UI.
    """
    def __init__(self, parent, api):
        UINode.__init__(self, 'Hosts', parent)
        self._hosts_service = api.system_service().hosts_service()
        self.refresh()

    def refresh(self):
        self._children = set([])
        hosts = self._hosts_service.list()
        if hosts is not None:
            for host in hosts:
                UIHost(self, host, host.name)

    def summary(self):
        hosts = self._hosts_service.list()
        if hosts is None:
            return 'no hosts', None
        up = 0
        for host in hosts:
            if host.status == types.HostStatus.UP:
                up += 1
        return '%d hosts (%d UP)' % (len(hosts), up), None


    def ui_command_create(self, name, address, password, cluster, description=None):
        host = self._hosts_service.add(
            types.Host(
                name=name,
                description=description if description is not None else '',
                address=address,
                root_password=password,
                cluster=types.Cluster(
                    name=cluster,
                ),
            ),
        )
        # Wait till the host is up:
        host_service = self._hosts_service.host_service(host.id)
        start_time = time.time()
        timeout = 15 * 60
        elpased = False
        while not elapsed:
            time.sleep(5)
            host = host_service.get()
            if host.status == types.HostStatus.UP or host.status == types.HostStatus.NonOperational:
                break
            if (time.time() - self.start_time) > timeout:
                elapsed = True
                break

        if host.status == types.HostStatus.UP:
            self.shell.log.info("Host was successfully added.")
            self.refresh()
            return

        if elapsed or host.status != types.HostStatus.UP:
            self.shell.log.info("Host was not added properly. Status: %s" % host.status)

    def ui_command_delete(self, name):
        filter = 'name=%s' % name
        try:
            host = self._hosts_service.list(search=filter)[0]
        except:
            self.shell.log.info('Host %s not found. Check spelling.' % name)
            return

        host_service = self._hosts_service.host_service(host.id)
        if host.status != types.HostStatus.MAINTENANCE:
            self.shell.log.info('Host is not in Maintenance. Deactivate it first.')
            return

        host_service.remove()
        self.refresh()

    def ui_command_deactivate(self, name):
        filter = 'name=%s' % name
        try:
            host = self._hosts_service.list(search=filter)[0]
        except:
            self.shell.log.info('Host %s not found. Check spelling' % name)
            return

        host_service = self._hosts_service.host_service(host.id)
        if host.status != types.HostStatus.MAINTENANCE:
            host_service.deactivate()
            self.refresh()

    def ui_command_activate(self, name):
        filter = 'name=%s' % name
        try:
            host = self._hosts_service.list(search=filter)[0]
        except:
            self.shell.log.info('Host %s not found. Check spelling' % name)
            return

        host_service = self._hosts_service.host_service(host.id)
        if host.status != types.HostStatus.UP:
            host_service.activate()
            self.refresh()


class UIHost(UINode):
    """
    A single host object UI.
    """
    def __init__(self, parent, host, name):
        UINode.__init__(self, name, parent)
        self._host = host
        self._parent = parent
        self.refresh()

    def refresh(self):
        self._children = set([])

    def summary(self):
        status = self._host.status
        if status == types.HostStatus.UP:
            state = ' [UP]'
        elif status == types.HostStatus.MAINTENANCE:
            state = ' [Maint.]'
        else:
            state = ''
        return 'Address: %s%s' % (self._host.address, state), None

    def ui_command_deactivate(self):
        self._parent.ui_command_deactivate(self._host.name)
        self.refresh()

    def ui_command_activate(self):
        self._parent.ui_command_activate(self._host.name)
        self.refresh()


class UIVMs(UINode):
    """
    A VMs objects UI.
    """
    def __init__(self, parent, api):
        UINode.__init__(self, 'VMs', parent)
        self._vms_service = api.system_service().vms_service()
        self.refresh()

    def refresh(self):
        self._children = set([])
        vms = self._vms_service.list()
        # for vm in vms:
        #    UIVM(self, vm)

    def summary(self):
        vms = self._vms_service.list()
        num_vms = len(vms)

        return 'Virtual Machines: %d' % num_vms, None

class UIVM(UINode):
    """
    A single VM object UI.
    """
    def __init__(self, parent, vm):
        UINode.__init__(self, 'Virtual machine', parent)
        self._vm = vm
        self.refresh()

    def refresh(self):
        self._children = set([])

    def summary(self):
        return '%s:%s' % (self._vm.name, self._vm.id), None

class UITemplates(UINode):
    """
    A Templates UI.
    """
    def __init__(self, parent, api):
        UINode.__init__(self, 'Templates', parent)
        self._templates_service = api.system_service().templates_service()
        self.refresh()

    def refresh(self):
        self._children = set([])
        templates = self._templates_service.list()
        for template in templates:
            UITemplate(self, template, template.name)

    def summary(self):
        templates = self._templates_service.list()
        return 'Templates: %d' % len(templates), None


class UITemplate(UINode):
    """
    A single template object UI.
    """
    def __init__(self, parent, template, name):
        UINode.__init__(self, name, parent)
        self._template = template
        self.refresh()

    def refresh(self):
        self._children = set([])

    def summary(self):
        return '%s' % self._template.name, None
