# REST API
#
############# Adaptive Link Rate ##############
#
# PUT /alr/{SWITCH_ID}/{PORT}   Activate ALR on PORT with data: threshold
#
# GET /alr/{SWITCH_ID}/{PORT} Get ALR status: rate, threshold
#
# DELETE /alr/{SWITCH_ID}/{PORT}    Delete ARL configuration for the switch
#
# GET /alr/speed/{SWITCH_IP}/{PORT}		Get speed of the port
# 
# PUT /alr/speed/{SWITCH_IP}/{PORT}		Set speed of the port
#
#
#
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
import adaptive_link_rate_v2

class AdaptiveLinkRateRestApi(app_manager.RyuApp):
	OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

	_CONTEXTS = {
			'dpset': dpset.DPSet,
			'wsgi': WSGIApplication,
			'adaptive_linkrate': adaptive_link_rate_v2.AdaptiveLinkRate
			}

	def __init__(self, *args, **kwargs):
		super(AdaptiveLinkRateRestApi, self).__init__(*args, **kwargs)
		dpset = kwargs['dpset']
		wsgi = kwargs['wsgi']
		adaptive_linkrate = kwargs['adaptive_linkrate']

		self.data = {}
		self.data['dpset'] = dpset
		self.data['waiters'] = {}
		self.data['adaptive_linkrate'] = adaptive_linkrate

		wsgi.register(AdaptiveLinkRateController, self.data)
		#mapper = wsgi.mapper

		#mapper.connect('hosts', '/v1.0/hosts', controller=HostTrackerController, action='get_all_hosts',
		#        conditions=dict(method=['GET']))
		#mapper.connect('hosts', '/v1.0/hosts/{dpid}', controller=HostTrackerController, action='get_hosts',
		#        conditions=dict(method=['GET']), requirements={'dpid': dpid_lib.DPID_PATTERN})


class AdaptiveLinkRateController(ControllerBase):
	def __init__(self, req, link, data, **config):
		super(AdaptiveLinkRateController, self).__init__(req, link, data, **config)
		self.adaptive_linkrate = data['adaptive_linkrate']
		self.dpset = data['dpset']

	#GET /alr/{SWITCH_ID}/{PORTID}
	@route('alr', '/v1.0/alr/{switchid}/{portid}', methods=['GET'])
	def get_alr_status(self, req,switchid,portid,**kwargs):
		result = self.adaptive_linkrate.getstatus(int(switchid),int(portid)) 
		msg = {'alr_enabled': result}
		return Response(status=200,content_type='application/json',
			body=json.dumps(msg))

	#PUT /alr/{SWITCH_ID}/{PORTID}
	@route('alr', '/v1.0/alr/{switchid}/{portid}', methods=['PUT'])
	def set_alr_status(self,req,switchid,portid,**kwargs):
		try:
			rest = json.loads(req.body) if req.body else {}
		except SyntaxError:
			AdaptiveLinkRateController._LOGGER.debug('invalid syntax %s', req.body)
			return Response(status=400)

		enabled = rest.get("enabled")
		threshold = 0
		bwArray = []
		if enabled.lower() == "true":
			enabled = True
			threshold = rest.get("threshold")
			bwArray = rest.get("bwArray")
		else:
			enabled = False
		result = self.adaptive_linkrate.set_alr_status(int(switchid),int(portid),enabled,threshold,bwArray)
		#print threshold
		#print result
		#print bwArray
		if result:
			msg = {'result': 'success'}
			return Response(status=200,content_type='application/json',
				body=json.dumps(msg))
		else:
			msg = {'result': 'failed'}
			return Response(status=404,content_type='application/json',
				body=json.dumps(msg))


	# GET /alr/speed/{SWITCH_IP}/{PORT}		Get speed of the port
	@route('alr', '/v1.0/alr/speed/{switchIP}/{port}', methods=['GET'])
	def get_speed(self, req,switchIP,port,**kwargs):
		result = self.adaptive_linkrate.getPortSpeed(switchIP,int(port)) 
		print result
		msg = {'get_speed': result}
		return Response(status=200,content_type='application/json',
			body=json.dumps(msg))

	# PUT /alr/speed/{SWITCH_IP}/{PORT}		Set speed of the port
	@route('alr', '/v1.0/alr/speed/{switchIP}/{port}', methods=['PUT'])
	def set_speed(self, req,switchIP,port,**kwargs):
		try:
			rest = json.loads(req.body) if req.body else {}
		except SyntaxError:
			AdaptiveLinkRateController._LOGGER.debug('invalid syntax %s', req.body)
			return Response(status=400)

		speed = int(rest.get("speed"))
		result = self.adaptive_linkrate.setPortSpeed(switchIP,int(port),speed)
		if result:
			msg = {'result': 'success'}
			return Response(status=200,content_type='application/json',
				body=json.dumps(msg))
	
	# PUT /alr/port/{SWITCH_IP}/{PORT}		Enable/disable port
	@route('alr', '/v1.0/alr/port/{switchIP}/{port}', methods=['PUT'])
	def enableDisablePort(self, req,switchIP,port,**kwargs):
		try:
			rest = json.loads(req.body) if req.body else {}
		except SyntaxError:
			AdaptiveLinkRateController._LOGGER.debug('invalid syntax %s', req.body)
			return Response(status=400)

		enabled = int(rest.get("enabled"))
		if enabled.lower() == "true":
			result = self.adaptive_linkrate.enableDisablePort(switchIP,int(port),1)
		else:
			result = self.adaptive_linkrate.enableDisablePort(switchIP,int(port),0)
		if result:
			msg = {'result': 'success',
					'detail': result
					}
			return Response(status=200,content_type='application/json',
				body=json.dumps(msg))