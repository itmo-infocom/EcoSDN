# REST API
#
############# ARP Handler ##############
#
# GET /arp_handler?ip=  Get MAC address of specified host ip, with data: host_ip
#

import logging
import json
from webob import Response
import time

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.controller import dpset
from ryu.app.wsgi import ControllerBase, WSGIApplication, route

from ryu.ofproto import ofproto_v1_0, ofproto_v1_3
from ryu.lib import dpid as dpid_lib
import proxy_arp


class ProxyARPRestApi(app_manager.RyuApp):
	OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION,ofproto_v1_3.OFP_VERSION]

	_CONTEXTS = {
			'dpset': dpset.DPSet,
			'wsgi': WSGIApplication,
			'proxy_arp': proxy_arp.ProxyARP
			}

	def __init__(self, *args, **kwargs):
		super(ProxyARPRestApi, self).__init__(*args, **kwargs)
		dpset = kwargs['dpset']
		wsgi = kwargs['wsgi']
		proxy_arp = kwargs['proxy_arp']
		proxy_arp.dpset = dpset

		self.data = {}
		self.data['dpset'] = dpset
		self.data['waiters'] = {}
		self.data['proxy_arp'] = proxy_arp

		wsgi.register(ProxyARPController, self.data)


class ProxyARPController(ControllerBase):
	def __init__(self, req, link, data, **config):
		super(ProxyARPController, self).__init__(req, link, data, **config)
		self.proxy_arp = data['proxy_arp']
		self.dpset = data['dpset']

	#GET /arp_handler
	@route('alr', '/v1.0/proxy_arp/{ipAddr}', methods=['GET'])
	def get_alr_status(self, req,ipAddr,**kwargs):
		macAddr = self.proxy_arp.getMac(ipAddr) 
		if not(macAddr ==None):
			msg = {'mac_addr': macAddr}
		else:	
			msg = {'mac_addr': "not found"}
		return Response(status=200,content_type='application/json',
			body=json.dumps(msg))

	#PUT /arp_handler
	@route('alr', '/v1.0/proxy_arp', methods=['PUT'])
	def setStatus(self, req,**kwargs):
		try:
			rest = json.loads(req.body) if req.body else {}
		except SyntaxError:
			ProxyARPController._LOGGER.debug('invalid syntax %s', req.body)
			return Response(status=400)

		enabled = rest.get("enabled")
		msg = {"status_change":"fail"}
		if enabled.lower() == "true":
			self.proxy_arp.setStatus(True)
			msg = {"status_change":"success"}
		else:
			self.proxy_arp.setStatus(False)
			msg = {"status_change":"success"}

		return Response(status=200,content_type='application/json',
			body=json.dumps(msg))





	



