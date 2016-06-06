#!/usr/bin/env python

import os

# When we're running locally we don't need to do this.
if 'OPENSHIFT_PYTHON_DIR' in os.environ:
    virtenv = os.environ['OPENSHIFT_PYTHON_DIR'] + '/virtenv/'
    virtualenv = os.path.join(virtenv, 'bin/activate_this.py')
    try:
        execfile(virtualenv, dict(__file__=virtualenv))
    except IOError:
        pass

# requires: pyramid, netaddr, jinja2
import json
import sys
# hack to make sure we can load wsgi.py as a module in this class
sys.path.insert(0, os.path.dirname(__file__))

import jinja2
import netaddr
from pyramid import config
from pyramid import renderers
from pyramid import response
from pyramid import view
from wsgiref.simple_server import make_server

import validator


config_template = """# Config generated by undercloud wizard
# Use these values in undercloud.conf
[DEFAULT]
undercloud_hostname = %(hostname)s
local_interface = %(local_interface)s
local_mtu = %(local_mtu)s
network_cidr = %(network_cidr)s
masquerade_network = %(masquerade_network)s
local_ip = %(local_ip)s
network_gateway = %(network_gateway)s
undercloud_public_vip = %(undercloud_public_vip)s
undercloud_admin_vip = %(undercloud_admin_vip)s
undercloud_service_certificate = %(undercloud_service_certificate)s
dhcp_start = %(dhcp_start)s
dhcp_end = %(dhcp_end)s
inspection_iprange = %(inspection_start)s,%(inspection_end)s
# This option name is deprecated and only included for compatibility with
# OSP director 7 installs.
discovery_iprange = %(inspection_start)s,%(inspection_end)s
"""
default_basic = {'local_interface': 'eth1',
                 'network_cidr': '192.168.0.0/24',
                 'node_count': '2'}
advanced_keys = ['hostname', 'local_ip', 'dhcp_start', 'dhcp_end',
                 'inspection_start', 'inspection_end',
                 'network_gateway', 'undercloud_public_vip',
                 'undercloud_admin_vip', 'local_mtu',
                 'undercloud_service_certificate']
# NOTE(bnemec): Adding an arbitrary 10 to the node count, to allow
# for virtual ips.  This may not be accurate for some setups.
virtual_ips = 10
# local_ip, public_vip, admin_vip
undercloud_ips = 3


class GeneratorError(RuntimeError):
    pass


def err_callback(message):
    raise GeneratorError(message)


def process_request(request):
    """Return the appropriate response data for a request

    Returns a tuple of (template, params) representing the appropriate
    data to put in a response to request.
    """
    # Remove unset keys so we can use .get() to set defaults
    params = {k: v for k, v in request.params.items() if v}
    # If generating advanced values, ignore any advanced values passed in
    # as part of the request
    if 'genadv' in params:
        params = {k: v for k, v in params.items() if k not in advanced_keys}

    loader = jinja2.FileSystemLoader('templates')
    env = jinja2.Environment(loader=loader)
    if params.get('generate'):
        t = env.get_template('generate.jinja2')
    else:
        t = env.get_template('ucw.jinja2')

    values = dict(default_basic)
    values['error'] = ''
    for k, v in values.items():
        if k in params:
            values[k] = params[k]
    # Populate descriptions
    with open('opt-descriptions.json') as f:
        descriptions = json.loads(f.read())
        values.update(descriptions)
    try:
        cidr = netaddr.IPNetwork(values['network_cidr'])
        if (len(cidr) < int(values['node_count']) * 2 + virtual_ips +
                undercloud_ips + 1):
            raise GeneratorError('Insufficient addresses available in '
                                 'provisioning CIDR')
        values['hostname'] = params.get('hostname', 'undercloud.localdomain')
        values['local_ip'] = params.get('local_ip',
                                        '%s/%s' % (str(cidr[1]),
                                                   cidr.prefixlen))
        values['local_mtu'] = params.get('local_mtu', '1500')
        values['network_gateway'] = params.get('network_gateway', str(cidr[1]))
        values['undercloud_public_vip'] = params.get('undercloud_public_vip',
                                                     str(cidr[2]))
        values['undercloud_admin_vip'] = params.get('undercloud_admin_vip',
                                                    str(cidr[3]))
        # 4 to allow room for two undercloud vips
        dhcp_start = 1 + undercloud_ips
        values['dhcp_start'] = params.get('dhcp_start', str(cidr[dhcp_start]))
        dhcp_end = dhcp_start + int(values['node_count']) + virtual_ips - 1
        values['dhcp_end'] = params.get('dhcp_end', str(cidr[dhcp_end]))
        inspection_start = dhcp_end + 1
        values['inspection_start'] = params.get('inspection_start',
                                                str(cidr[inspection_start]))
        inspection_end = inspection_start + int(values['node_count']) - 1
        values['inspection_end'] = params.get('inspection_end',
                                              str(cidr[inspection_end]))
        values['masquerade_network'] = values['network_cidr']
        values['undercloud_service_certificate'] = params.get(
            'undercloud_service_certificate', '')
        values['config'] = config_template.replace('\n', '<br>') % values
        validator.validate_config(values, err_callback)
    except GeneratorError as e:
        values['error'] = str(e)
    return t, values


@view.view_config(route_name='ucw')
def ucw(request):
    template, params = process_request(request)
    return response.Response(template.render(**params))

if __name__ == '__main__':
    conf = config.Configurator()
    conf.add_route('ucw', '/')
    conf.scan()
    app = conf.make_wsgi_app()
    ip = os.environ['OPENSHIFT_PYTHON_IP']
    port = int(os.environ['OPENSHIFT_PYTHON_PORT'])
    server = make_server(ip, port, app)
    server.serve_forever()

