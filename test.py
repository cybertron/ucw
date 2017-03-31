#!/usr/bin/env python

import unittest

import mock

import app

# Make sure we always return a fresh copy of these values.  The tests
# modify the values and we don't want those to leak between tests.
def all_params():
    return {'local_interface': 'p9p1',
            'network_cidr': '10.0.0.0/24',
            'node_count': '25',
            'undercloud_hostname': 'uc-prod.tripleo.org',
            'local_ip': '10.0.0.10/24',
            'local_mtu': '9000',
            'dhcp_start': '10.0.0.20',
            'dhcp_end': '10.0.0.60',
            'inspection_start': '10.0.0.100',
            'inspection_end': '10.0.0.130',
            'network_gateway': '10.0.0.254',
            'undercloud_public_host': '10.0.0.11',
            'undercloud_admin_host': '10.0.0.12',
            'undercloud_service_certificate':
                '/etc/pki/instack-certs/undercloud.pem',
            'generate_service_certificate': 'True',
            }

class TestProcessRequest(unittest.TestCase):
    def setUp(self):
        self.mock_request = mock.Mock()
        self.mock_request.params = {}

    def _test_params(self):
        t, params = app.process_request(self.mock_request)
        self.assertEqual('templates/ucw.jinja2', t.filename)
        return params

    def _assert_overwritten_params(self, params):
        self.assertEqual('eth1', params['local_interface'])
        self.assertEqual('192.168.24.0/24', params['network_cidr'])
        self.assertEqual('2', params['node_count'])
        self.assertEqual('192.168.24.1/24', params['local_ip'])
        self.assertEqual('192.168.24.4', params['dhcp_start'])
        self.assertEqual('192.168.24.15', params['dhcp_end'])
        self.assertEqual('192.168.24.16', params['inspection_start'])
        self.assertEqual('192.168.24.17', params['inspection_end'])
        self.assertEqual('192.168.24.1', params['network_gateway'])
        self.assertEqual('192.168.24.2', params['undercloud_public_host'])
        self.assertEqual('192.168.24.3', params['undercloud_admin_host'])

    def _assert_kept_params(self, params):
        self.assertEqual('9000', params['local_mtu'])
        self.assertEqual('uc-prod.tripleo.org', params['undercloud_hostname'])
        self.assertEqual('/etc/pki/instack-certs/undercloud.pem',
                         params['undercloud_service_certificate'])
        self.assertEqual('True', params['generate_service_certificate'])

    def _assert_defaults(self, params):
        self._assert_overwritten_params(params)
        self.assertEqual('1500', params['local_mtu'])
        self.assertEqual('undercloud.localdomain',
                         params['undercloud_hostname'])
        self.assertEqual('', params['undercloud_service_certificate'])
        self.assertEqual('', params['error'])

    def test_process_request(self):
        params = self._test_params()
        self._assert_defaults(params)

    def _assert_request_params(self, params):
        for key in self.mock_request.params.keys():
            self.assertEqual(self.mock_request.params[key],
                             params[key])
        self.assertEqual('', params['error'])

    def test_basic_input(self):
        self.mock_request.params = {'local_interface': 'p9p1',
                                    'network_cidr': '10.0.0.0/24',
                                    'node_count': '25',
                                    }
        params = self._test_params()
        self._assert_request_params(params)

    def test_bogus_key_ignored(self):
        self.mock_request.params = {'foo': 'bar'}
        params = self._test_params()
        self.assertNotIn('foo', params)

    def test_advanced_input(self):
        self.mock_request.params = all_params()
        params = self._test_params()
        self._assert_request_params(params)

    def test_generate_advanced(self):
        self.mock_request.params = all_params()
        self.mock_request.params.update({'local_interface': 'eth1',
                                         'network_cidr': '192.168.24.0/24',
                                         'node_count': '2',
                                         'genadv': 'Generate Advanced',
                                         })
        params = self._test_params()
        self._assert_overwritten_params(params)
        self._assert_kept_params(params)

    def test_insufficient_ips(self):
        self.mock_request.params = {'local_interface': 'p9p1',
                                    'network_cidr': '10.0.0.0/24',
                                    'node_count': '250',
                                    }
        params = self._test_params()
        self.assertEqual('Insufficient addresses available in provisioning '
                         'CIDR', params['error'])

    def test_invalid_configuration(self):
        self.mock_request.params = all_params()
        self.mock_request.params['dhcp_start'] = '10.0.0.70'
        params = self._test_params()
        self.assertEqual('Invalid dhcp range specified, dhcp_start "%s" does '
                         'not come before dhcp_end "%s"' %
                         (params['dhcp_start'], params['dhcp_end']),
                         params['error'])

    def test_generate(self):
        self.mock_request.params = all_params()
        self.mock_request.params['generate'] = 'Generate Configuration'
        t, params = app.process_request(self.mock_request)
        self.assertEqual('templates/generate.jinja2', t.filename)

    def test_view(self):
        response = app.ucw(self.mock_request)
        self.assertIn("<td>Provisioning Interface</td> <td><input type='text' "
                      "name='local_interface' value=\"eth1\" title='Network "
                      "interface on the Undercloud that will be handling the "
                      "PXE boots and DHCP for Overcloud instances.'></td>",
                      response.body)

    def test_gen_cert(self):
        self.mock_request.params = all_params()
        self.mock_request.params['generate_service_certificate'] = 'True'
        response = app.ucw(self.mock_request)
        self.assertIn("<td>Generate SSL Certificate<sup>N</sup></td> "
                      "<td><input type='checkbox' "
                      "name='generate_service_certificate' "
                      "value='True' checked",
                      response.body)

    def test_no_gen_cert(self):
        response = app.ucw(self.mock_request)
        self.assertIn("<td>Generate SSL Certificate<sup>N</sup></td> "
                      "<td><input type='checkbox' "
                      "name='generate_service_certificate' "
                      "value='True'  title=",
                      response.body)

    def test_scheduler_attempts(self):
        self.mock_request.params = {'node_count': '20'}
        params = self._test_params()
        self.assertEqual('20', params['scheduler_max_attempts'])

    def test_scheduler_attempts_min(self):
        self.mock_request.params = {'node_count': '2'}
        params = self._test_params()
        self.assertEqual('10', params['scheduler_max_attempts'])

if __name__ == '__main__':
    unittest.main()
