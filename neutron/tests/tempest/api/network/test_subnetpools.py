# Copyright 2015 Hewlett-Packard Development Company, L.P.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import copy

from tempest_lib.common.utils import data_utils

from neutron.tests.tempest.api.network import base
from neutron.tests.api.contrib import clients
from neutron.tests.tempest import config
from neutron.tests.tempest import test

CONF = config.CONF
SUBNETPOOL_NAME = 'smoke-subnetpool'
SUBNET_NAME = 'smoke-subnet'


class SubnetPoolsTest(base.BaseNetworkTest):

    min_prefixlen = '28'
    max_prefixlen = '31'
    ip_version = 4
    subnet_cidr = u'10.11.12.0/31'
    new_prefix = u'10.11.15.0/24'
    larger_prefix = u'10.11.0.0/16'

    """
    Tests the following operations in the Neutron API using the REST client for
    Neutron:

        create a subnetpool for a tenant
        list tenant's subnetpools
        show a tenant subnetpool details
        subnetpool update
        delete a subnetpool

        All subnetpool tests are run once with ipv4 and once with ipv6.

    v2.0 of the Neutron API is assumed.

    """

    @classmethod
    def resource_setup(cls):
        super(SubnetPoolsTest, cls).resource_setup()
        prefixes = [u'10.11.12.0/24']
        cls._subnetpool_data = {'subnetpool': {'min_prefixlen': '29',
                                               'prefixes': prefixes}}
        try:
            creds = cls.isolated_creds.get_admin_creds()
            cls.os_adm = clients.Manager(credentials=creds)
        except NotImplementedError:
            msg = ("Missing Administrative Network API credentials "
                   "in configuration.")
            raise cls.skipException(msg)
        cls.admin_client = cls.os_adm.network_client

    def _create_subnetpool(self, client, pool_values=None):
        name = data_utils.rand_name(SUBNETPOOL_NAME)
        subnetpool_data = copy.deepcopy(self._subnetpool_data)
        if pool_values:
            subnetpool_data['subnetpool'].update(pool_values)
        subnetpool_data['subnetpool']['name'] = name
        body = client.create_subnetpool(subnetpool_data)
        created_subnetpool = body['subnetpool']
        subnetpool_id = created_subnetpool['id']
        return name, subnetpool_id

    def _new_subnetpool_attributes(self):
        new_name = data_utils.rand_name(SUBNETPOOL_NAME)
        subnetpool_data = {'subnetpool': {'name': new_name,
                                          'min_prefixlen': self.min_prefixlen,
                                          'max_prefixlen': self.max_prefixlen}}
        return subnetpool_data

    def _check_equality_updated_subnetpool(self, expected_values,
                                           updated_pool):
        self.assertEqual(expected_values['name'],
                         updated_pool['name'])
        self.assertEqual(expected_values['min_prefixlen'],
                         updated_pool['min_prefixlen'])
        self.assertEqual(expected_values['max_prefixlen'],
                         updated_pool['max_prefixlen'])
        # expected_values may not contains all subnetpool values
        if 'prefixes' in expected_values:
            self.assertEqual(expected_values['prefixes'],
                             updated_pool['prefixes'])

    @test.attr(type='smoke')
    @test.idempotent_id('6e1781ec-b45b-4042-aebe-f485c022996e')
    def test_create_list_subnetpool(self):
        name, pool_id = self._create_subnetpool(self.client)
        body = self.client.list_subnetpools()
        subnetpools = body['subnetpools']
        self.addCleanup(self.client.delete_subnetpool, pool_id)
        self.assertIn(pool_id, [sp['id'] for sp in subnetpools],
                      "Created subnetpool id should be in the list")
        self.assertIn(name, [sp['name'] for sp in subnetpools],
                      "Created subnetpool name should be in the list")

    @test.attr(type='smoke')
    @test.idempotent_id('741d08c2-1e3f-42be-99c7-0ea93c5b728c')
    def test_get_subnetpool(self):
        name, pool_id = self._create_subnetpool(self.client)
        self.addCleanup(self.client.delete_subnetpool, pool_id)
        prefixlen = self._subnetpool_data['subnetpool']['min_prefixlen']
        body = self.client.get_subnetpool(pool_id)
        subnetpool = body['subnetpool']
        self.assertEqual(name, subnetpool['name'])
        self.assertEqual(pool_id, subnetpool['id'])
        self.assertEqual(prefixlen, subnetpool['min_prefixlen'])
        self.assertEqual(prefixlen, subnetpool['default_prefixlen'])
        self.assertFalse(subnetpool['shared'])

    @test.attr(type='smoke')
    @test.idempotent_id('764f1b93-1c4a-4513-9e7b-6c2fc5e9270c')
    def test_tenant_update_subnetpool(self):
        name, pool_id = self._create_subnetpool(self.client)
        subnetpool_data = self._new_subnetpool_attributes()
        self.client.update_subnetpool(pool_id, subnetpool_data)

        body = self.client.get_subnetpool(pool_id)
        subnetpool = body['subnetpool']
        self.addCleanup(self.client.delete_subnetpool, pool_id)
        self._check_equality_updated_subnetpool(subnetpool_data['subnetpool'],
                                                subnetpool)
        self.assertFalse(subnetpool['shared'])

    @test.attr(type='smoke')
    @test.idempotent_id('4b496082-c992-4319-90be-d4a7ce646290')
    def test_update_subnetpool_prefixes_append(self):
        # We can append new prefixes to subnetpool
        name, pool_id = self._create_subnetpool(self.client)
        old_prefixes = self._subnetpool_data['subnetpool']['prefixes']
        new_prefixes = old_prefixes[:]
        new_prefixes.append(self.new_prefix)
        subnetpool_data = {'subnetpool': {'prefixes': new_prefixes}}
        self.addCleanup(self.client.delete_subnetpool, pool_id)
        self.client.update_subnetpool(pool_id, subnetpool_data)
        body = self.client.get_subnetpool(pool_id)
        prefixes = body['subnetpool']['prefixes']
        self.assertIn(self.new_prefix, prefixes)
        self.assertIn(old_prefixes[0], prefixes)

    @test.attr(type='smoke')
    @test.idempotent_id('2cae5d6a-9d32-42d8-8067-f13970ae13bb')
    def test_update_subnetpool_prefixes_extend(self):
        # We can extend current subnetpool prefixes
        name, pool_id = self._create_subnetpool(self.client)
        old_prefixes = self._subnetpool_data['subnetpool']['prefixes']
        subnetpool_data = {'subnetpool': {'prefixes': [self.larger_prefix]}}
        self.addCleanup(self.client.delete_subnetpool, pool_id)
        self.client.update_subnetpool(pool_id, subnetpool_data)
        body = self.client.get_subnetpool(pool_id)
        prefixes = body['subnetpool']['prefixes']
        self.assertIn(self.larger_prefix, prefixes)
        self.assertNotIn(old_prefixes[0], prefixes)

    @test.attr(type='smoke')
    @test.idempotent_id('d70c6c35-913b-4f24-909f-14cd0d29b2d2')
    def test_admin_create_shared_subnetpool(self):
        pool_values = {'shared': 'True'}
        name, pool_id = self._create_subnetpool(self.admin_client,
                                                pool_values)
        # Shared subnetpool can be retrieved by tenant user.
        body = self.client.get_subnetpool(pool_id)
        self.addCleanup(self.admin_client.delete_subnetpool, pool_id)
        subnetpool = body['subnetpool']
        self.assertEqual(name, subnetpool['name'])
        self.assertTrue(subnetpool['shared'])


class SubnetPoolsTestV6(SubnetPoolsTest):

    min_prefixlen = '48'
    max_prefixlen = '64'
    ip_version = 6
    subnet_cidr = '2001:db8:3::/64'
    new_prefix = u'2001:db8:5::/64'
    larger_prefix = u'2001:db8::/32'

    @classmethod
    def resource_setup(cls):
        super(SubnetPoolsTestV6, cls).resource_setup()
        min_prefixlen = '64'
        prefixes = [u'2001:db8:3::/48']
        cls._subnetpool_data = {'subnetpool': {'min_prefixlen': min_prefixlen,
                                               'prefixes': prefixes}}
