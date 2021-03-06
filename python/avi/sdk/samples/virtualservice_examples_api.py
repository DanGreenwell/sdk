#!/usr/bin/env python
import argparse
import json
import logging
import sys

from avi.sdk.avi_api import ApiSession
from avi.sdk.utils.api_utils import ApiUtils
from avi.sdk.samples.common import get_sample_ssl_params
from requests.packages import urllib3

logger = logging.getLogger(__name__)
ch = logging.StreamHandler(sys.stdout)
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(ch)

urllib3.disable_warnings()

class VirtualServiceExample(object):
    '''
    Provides example of following operations
    1. Create basic vs
    2. Create vs with SSL objects
    3. Create vs with custom parameters like application profile
    4. Inventory API calls for virtualservice
    5. Metrics API calls for virtualservice metrics
    '''
    def __init__(self, api):
        self.api = api
        self.api_utils = ApiUtils(api)

    def create_basic_vs(self, vs_name, vip, servers=None):
        # first create pool for virtual service
        servers_obj = self.get_server_obj(servers)
        pool_name = vs_name + '-pool'
        pool_obj = self.create_pool(pool_name, servers_obj)
        pool_ref = self.api.get_obj_ref(pool_obj)

        # create virtual service dict
        services_obj = [{'port': 80, 'enable_ssl': False}]
        vs_obj = {
            'name': vs_name,
            'type': 'VS_TYPE_NORMAL',
            'ip_address': {
                'addr': vip,
                'type': 'V4'
            },
            'enabled': True,
            'services': services_obj,
            'application_profile_name': 'System-HTTP',
            'pool_ref': pool_ref
        }

        # post VS data in json format to avi api
        resp = self.api.post('virtualservice', data=json.dumps(vs_obj))
        if resp.status_code in xrange(200, 299):
            logger.debug('Virtual service created successfully %s' % vs_name)
        else:
            logger.debug('Error creating virtual service : %s' % resp.text)

    def create_ssl_vs(self, vs_name, vip, servers=None):
        # import certs.
        ssl_kc_name = vs_name + '-' + 'ssl-kc'
        ssl_key_and_cert_ref = [self.upload_ssl_certs(ssl_kc_name)]

        # turning on SSL profile
        services_obj = [{'port': 443, 'enable_ssl': True}]
        servers_obj = self.get_server_obj(servers)

        # create pool for virtual service
        pool_name = vs_name + '-pool'
        pool_obj = self.create_pool(pool_name, servers_obj)
        pool_ref = self.api.get_obj_ref(pool_obj)

        # create virtual service dict for ssl VS
        vs_obj = {
            'name': vs_name,
            'type': 'VS_TYPE_NORMAL',
            'ip_address': {
                'addr': vip,
                'type': 'V4'
            },
            'enabled': True,
            'services': services_obj,
            'ssl_key_and_certificate_refs': ssl_key_and_cert_ref,
            'ssl_profile_name': 'System-Standard',
            'application_profile_name': 'System-Secure-HTTP',
            'pool_ref': pool_ref
        }
        resp = self.api.post('virtualservice', data=json.dumps(vs_obj))
        if resp.status_code >= 200 and resp.status_code < 300:
            logger.debug('Virtual service created successfully %s' % vs_name)
        else:
            raise Exception('error %s' % str(resp))

    def create_custom_vs(self, vs_name, vip, servers=None):
        # import certs.
        ssl_kc_name = vs_name + '-' + 'ssl-kc'
        ssl_key_and_cert_ref = [self.upload_ssl_certs(ssl_kc_name)]

        # turning on SSL profile
        services_obj = [{'port': 443, 'enable_ssl': True}]

        # create custom pool with health monitors
        servers_obj = self.get_server_obj(servers)
        pool_name = vs_name + '-pool'
        pool_obj = self.create_pool(
                        pool_name, servers_obj,
                        ['System-TCP', 'System-HTTP', 'System-Ping'])
        pool_ref = self.api.get_obj_ref(pool_obj)

        # create virtual service dict for ssl VS
        vs_obj = {
            'name': vs_name,
            'type': 'VS_TYPE_NORMAL',
            'ip_address': {
                'addr': vip,
                'type': 'V4'
            },
            'enabled': True,
            'services': services_obj,
            'ssl_key_and_certificate_refs': ssl_key_and_cert_ref,
            'ssl_profile_name': 'System-Standard',
            'application_profile_name': 'System-Secure-HTTP',
            'pool_ref': pool_ref
        }
        resp = self.api.post('virtualservice', data=json.dumps(vs_obj))
        if resp.status_code >= 200 and resp.status_code < 300:
            logger.debug('Virtual service created successfully %s' % vs_name)
        else:
            logger.debug('Error creating virtual service : %s' % resp.text)

    def create_policy_vs(self, vs_name, vip, servers=None):
        '''
        This is example to create a custom vs with HTTP policies
        1. creates a rewrite policy
        '''
        # import certs.
        ssl_kc_name = vs_name + '-' + 'ssl-kc'
        ssl_key_and_cert_ref = [self.upload_ssl_certs(ssl_kc_name)]
        # turning on SSL profile
        services_obj = [{'port': 443, 'enable_ssl': True}]
        # create custom pool with health monitors
        servers_obj = self.get_server_obj(servers)
        pool_name = vs_name + '-pool'
        pool_obj = self.create_pool(
                    pool_name, servers_obj,
                    ['System-TCP', 'System-HTTP', 'System-Ping'])
        pool_ref = self.api.get_obj_ref(pool_obj)

        # create virtual service dict for ssl VS
        vs_obj = {
            'name': vs_name,
            'type': 'VS_TYPE_NORMAL',
            'ip_address': {
                'addr': vip,
                'type': 'V4'
            },
            'enabled': True,
            'services': services_obj,
            'ssl_key_and_certificate_refs': ssl_key_and_cert_ref,
            'ssl_profile_name': 'System-Standard',
            'application_profile_name': 'System-Secure-HTTP',
            'pool_ref': pool_ref
        }
        resp = self.api.post('virtualservice', data=json.dumps(vs_obj))
        if resp.status_code >= 200 and resp.status_code < 300:
            logger.debug('Virtual service created successfully %s' % vs_name)
        else:
            logger.debug('Error creating virtual service : %s' % resp.text)

    def get_inventory(self, inventory_type='virtualservice-inventory',
                      obj_uuid='', params=None):

        params = {} if not params else params
        if 'page' not in params:
            params['page'] = 1
        if 'page_size' not in params:
            params['page_size'] = 10
        inventory_path = inventory_type
        if obj_uuid:
            # this is case of inventory for a specific object
            inventory_path = inventory_path + '/' + obj_uuid
        resp = self.api.get(inventory_path, params=params)
        if resp.status_code in xrange(200, 299):
            return json.loads(resp.text)
        else:
            return 'Error in getting inventory for %s, Error :%s' % (
                                                    inventory_type, resp.text)

    def delete(self, name, entity_type):
        resp = self.api.delete_by_name(entity_type, name)
        if resp.status_code in xrange(200, 299):
            print '%s name: %s deleted successfully' % (entity_type, name)
        else:
            print 'Error in deleting virtual service :%s' % resp.text

    def get_metrics(self, name, metric_id, entity_type='virtualservice'):
        resp = self.api.get_object_by_name(entity_type, name)
        uuid = self.api.get_obj_uuid(resp)
        path = 'analytics/metrics/%s/%s/?metric_id=%s&step=300&limit=12' % (
                                                entity_type, uuid, metric_id)
        resp = self.api.get(path)
        if resp.status_code in xrange(200, 299):
            metrics_dict = json.loads(resp.text)
            logger.debug('%s', metrics_dict)
            return metrics_dict
        else:
            logger.debug('Error in getting %s metric for name : %s' % (
                        entity_type, name))

    def upload_ssl_certs(self, ssl_cert_name, ssl_cert_file_path=''):
        '''
        '''
        cert, key, _, _ = get_sample_ssl_params()
        # upload the key and cert to the controller with name ssl_cert_name
        resp = self.api_utils.import_ssl_certificate(ssl_cert_name, key, cert)
        if resp.status_code not in xrange(200, 299):
            print 'Error in uploading certs : %s' % resp.text
            exit(0)
        ssl_kc_ref = self.api.get_obj_ref(resp)
        return ssl_kc_ref

    def get_server_obj(self, servers):
        '''
        '''
        servers_obj = []
        for server in servers:
            parts = server.split(':')
            ip_addr = parts[0]
            port = parts[1] if len(parts) == 2 else 80
            servers_obj.append({
                'ip': {
                    'addr': ip_addr,
                    'type': 'V4'
                },
                'port': port
            })
        return servers_obj

    def create_pool(self, name, servers_obj, monitor_names=None,
                    lb_algorithm='LB_ALGORITHM_LEAST_CONNECTIONS'):
        health_monitors = None
        if monitor_names:
            health_monitors = []
            for monitor_name in monitor_names:
                health_monitor_tcp = self.api.get_object_by_name('healthmonitor',
                                                                 monitor_name)
                health_monitors.append(self.api.get_obj_ref(health_monitor_tcp))
        print health_monitors
        pool_name = name
        pool_obj = {
            "lb_algorithm": lb_algorithm,
            "default_server_port": 80,
            "name": pool_name,
            "servers": servers_obj,
            'health_monitor_refs': health_monitors
        }
        resp = self.api.post('pool', data=json.dumps(pool_obj))
        if resp.status_code in xrange(200, 299):
            return resp
        else:
            print 'Error in creating pool :%s' % resp.text
            exit(0)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--option',
                        choices=['create-basic-vs', 'create-ssl-vs',
                                 'create-custom-vs', 'create-policy-vs',
                                 'show-vs-inventory',
                                 'show-se-inventory', 'show-pool-inventory',
                                 'delete-vs', 'delete-pool',
                                 'show-vs-metric', 'get_se_metric',
                                 'show-pool-metric'],
                        help='',
                        default='create-basic-vs')
    parser.add_argument('-n', '--vs_name_suffix',
                        help='VirtualService Name Suffix',
                        default='vs')
    parser.add_argument(
        '-s', '--server_ips',
        help='Pool Server IPs comma separated Eg. 1.1.1.1,2.2.2.2',
        default='1.1.1.1,1.1.1.2')
    parser.add_argument('-u', '--user', help='controller user',
                        default='admin')
    parser.add_argument('-p', '--password', help='controller user password',
                        default='avi123')
    parser.add_argument('-t', '--tenant', help='tenant name',
                        default=None)
    parser.add_argument('--tenant-uuid', help='tenant uuid',
                        default=None)
    parser.add_argument('-c', '--controller_ip', help='controller ip')
    parser.add_argument('-i', '--vip', help='VIP address')

    parser.add_argument('-r', '--resource_name',
                        help='Resource Name to be deleted',
                        default='basic-vs')
    parser.add_argument('-m', '--metric_id',
                        help='Comma separated metric ids',
                        default='l4_client.avg_bandwidth')

    args = parser.parse_args()
    print 'parsed args', args
    api = ApiSession.get_session(args.controller_ip, args.user, args.password,
                 tenant=args.tenant, tenant_uuid=args.tenant_uuid)
    servers = [server.strip() for server in args.server_ips.split(',')]
    vse = VirtualServiceExample(api)

    if args.option == 'create-basic-vs':
        vip = args.vip if args.vip else '10.10.42.2'
        vs_name = 'basic-' + args.vs_name_suffix
        vse.create_basic_vs(vs_name, vip, servers)
    elif args.option == 'create-ssl-vs':
        vip = args.vip if args.vip else '10.10.42.3'
        vs_name = 'ssl-' + args.vs_name_suffix
        vse.create_ssl_vs(vs_name, vip, servers)
    elif args.option == 'create-custom-vs':
        vip = args.vip if args.vip else '10.10.42.3'
        vs_name = 'custom-' + args.vs_name_suffix
        vse.create_custom_vs(vs_name, vip, servers)
    elif args.option == 'create-policy-vs':
        vip = args.vip if args.vip else '10.10.42.3'
        vs_name = 'policy-' + args.vs_name_suffix
        vse.create_policy_vs(vs_name, vip, servers)
    elif args.option == 'show-vs-inventory':
        rsp = vse.get_inventory('virtualservice-inventory')
        print rsp
    elif args.option == 'show-pool-inventory':
        rsp = vse.get_inventory('pool-inventory')
        print rsp
    elif args.option == 'show-se-inventory':
        rsp = vse.get_inventory('serviceengine-inventory')
        print rsp
    elif args.option == 'delete-vs':
        vse.delete(args.resource_name, 'virtualservice')
    elif args.option == 'delete-pool':
        vse.delete(args.resource_name, 'pool')
    elif args.option == 'show-vs-metric':
        vse.get_metrics(args.resource_name, args.metric_id,
                        entity_type='virtualservice')
    elif args.option == 'show-se-metric':
        vse.get_metrics(args.resource_name, args.metric_id,
                        entity_type='serviceengine')
    elif args.option == 'show-pool-metric':
        vse.get_metrics(args.resource_name, args.metric_id,
                        entity_type='pool')
