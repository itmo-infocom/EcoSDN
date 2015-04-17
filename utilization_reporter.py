import logging
import json
from webob import Response

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.controller import dpset
from ryu.app.wsgi import ControllerBase, WSGIApplication
from ryu.lib import hub

import utilization_event
from operator import attrgetter

from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ipv4
from ryu.lib.packet import arp
from ryu.ofproto import ether
from ryu.ofproto import ofproto_v1_0, ofproto_v1_3
from ryu.lib import dpid as dpid_lib

import MyPorts

class MyPort:
	def __init__(self,port_no):
		self.port_no = port_no
		self.rx_bytes=0
		self.tx_bytes=0
		self.utilization = 0
		self.bandwidth = 100*1000000.0 #100Mbps , need a way to get the real value for the bandwidth

		self.alr_enabled= False
		self.bwArray=[10*1000000.0,100*1000000.0]
		self.threshold=0
		#self.portConfig = 0
		#self.connectedMac=None
		#self.rateConfig=0  #rate config = 0 means it's not using queue
		#self.qos_id="-1"

	def __repr__(self):
		return "port %d util %d"%(self.port_no,self.utilization)

class UtilizationReporter(app_manager.RyuApp):
	OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
	_EVENTS =  [utilization_event.UtilizationEvent]

	def __init__(self, *args,**kwargs):
		super(UtilizationReporter,self).__init__(*args,**kwargs)

		self.datapaths = {}
		self.monitor_thread = hub.spawn(self._monitor)
		self.monitoring_time = 5; #send request stats every 5 seconds

		self.portUtils={}

	@set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
	def _state_change_handler(self, ev):
		datapath = ev.datapath
        
		if ev.state == MAIN_DISPATCHER:
			if not datapath.id in self.datapaths:
				self.logger.debug('register datapath: %016x', datapath.id)
				self.datapaths[datapath.id] = datapath
				self.portUtils[datapath.id] = []
				for i in range(0,20):
					self.portUtils[datapath.id].append(MyPort(i))
					
					#for testing
					if i==1:
						self.portUtils[datapath.id][i].alr_enabled = True
						self.portUtils[datapath.id][i].bwArray = [10*1000000.0 ,100*1000000.0 ]
						self.portUtils[datapath.id][i].threshold = 10


				MyPorts.portUtils = self.portUtils

		elif ev.state == DEAD_DISPATCHER:
			if datapath.id in self.datapaths:
				self.logger.debug('unregister datapath: %016x', datapath.id)
				del self.datapaths[datapath.id]
				del self.portUtils[datapath.id]

	def _monitor(self):
	    while True:
			for dp in self.datapaths.values():
				#request stats to all DP, this is not good
				self._request_stats(dp)
			hub.sleep(self.monitoring_time)

	def _request_stats(self, datapath):
		self.logger.debug('send stats request: %016x', datapath.id)
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser

		#request port stats
		print datapath.id
		req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
		datapath.send_msg(req)

	@set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
	def _port_stats_reply_handler(self, ev):
		body = ev.msg.body
		datapath = ev.msg.datapath
		
		self.logger.info('datapath         port     '
		                 'rx-pkts  rx-bytes rx-error '
		                 'tx-pkts  tx-bytes tx-error')
		self.logger.info('---------------- -------- '
		                 '-------- -------- -------- '
		                 '-------- -------- --------')

		utils={datapath.id:[]}
		for stat in sorted(body, key=attrgetter('port_no')):
			if stat.port_no != 0xfffffffe:
				if hasattr(self.portUtils[datapath.id][stat.port_no],'rx_bytes'):
					self.logger.info('%016x %8x %8d %8d %8d %8d %8d %8d', 
				                         ev.msg.datapath.id, stat.port_no,
				                         stat.rx_packets, stat.rx_bytes, stat.rx_errors,
				                         stat.tx_packets, stat.tx_bytes, stat.tx_errors)
					#calculate utilization on this port
					deltatraffic= (stat.rx_bytes - self.portUtils[datapath.id][stat.port_no].rx_bytes) + (stat.tx_bytes - self.portUtils[datapath.id][stat.port_no].tx_bytes)
					self.portUtils[datapath.id][stat.port_no].utilization = deltatraffic * 8 * 100 / (self.monitoring_time * self.portUtils[datapath.id][stat.port_no].bandwidth)
					self.logger.info('\nutilization port %d: %f', stat.port_no, self.portUtils[datapath.id][stat.port_no].utilization )
					self.portUtils[datapath.id][stat.port_no].tx_bytes = stat.tx_bytes
					self.portUtils[datapath.id][stat.port_no].rx_bytes = stat.rx_bytes

					utils[datapath.id].append({stat.port_no:self.portUtils[datapath.id][stat.port_no].utilization})

		#generate the utilization event
		self.send_event_to_observers(utilization_event.UtilizationEvent(utils))
		#print utils
		MyPorts.portUtils = self.portUtils


