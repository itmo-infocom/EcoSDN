"""
1. setup queues with different rates:
queue 1: 10 M 
queue 2: 1 M 

2. read utilization on every port, if utilization on that port is less than 10%, then install flows matching to that mac dest to be outputted first
to the queue number 1 or 2 (not sure which one, goota read the paper)
"""

from operator import attrgetter

import qos_simple_switch_13
import custom_event
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib import hub

#import urllib
#import urllib2
import requests
import json
import ast


class MyPort:
	def __init__(self):
		self.rx_bytes=0
		self.tx_bytes=0
		self.utilization = 0
		self.portConfig = 0
		self.connectedMac=None
		self.rateConfig=0  #rate config = 0 means it's not using queue
		self.qos_id="-1"


class AdaptiveLinkRate(qos_simple_switch_13.SimpleSwitch13):

	_EVENTS =  [custom_event.NewHostEvent]

	def __init__(self, *args, **kwargs):
		super(AdaptiveLinkRate, self).__init__(*args, **kwargs)
		self.datapaths = {}
        
        #self.rx_bytes = [0,0]
        #self.tx_bytes = [0,0]
        #self.utilization= [0.0,0.0]
        #self.portsConfig = [0,0]

		self.monitoring_time = 5;
		self.linkBandwidth = 100*1000000.0
        #self.hosts={}
		self.ports=[]
		for i in range(1,10):
			self.ports.append(MyPort())

	@set_ev_cls(ofp_event.EventOFPStateChange,[MAIN_DISPATCHER, DEAD_DISPATCHER])
	def _state_change_handler(self, ev):
		if ev.state == MAIN_DISPATCHER:
			self.installQueueSettings()
			#self.noBroadcastOnPort(2)
			#self.installBalancingRoutes()

	def installQueueSettings(self):
		#set switch address, only for switch 1
		url = 'http://localhost:8080/v1.0/conf/switches/0000000000000001/unix_socket'
		payload="/tmp/s1"
		response = requests.put(url,data=json.dumps(payload))
		self.logger.info(response.text)

		#set queue settings on the switch 1, on port 1 only
		url = 'http://localhost:8080/qos/queue/0000000000000001'
		payload = {"port_name": "1", "queues": [{"id": "1", "min_rate":"50"}]}
		response = requests.post(url,data=json.dumps(payload))
		self.logger.info(response.text)


	@set_ev_cls(custom_event.NewHostEvent)
	def newHostConnected(self,ev):
		#self.hosts = ev.hosts
		self.ports[ev.port].connectedMac = ev.macAddr
		self.logger.info(ev.macAddr)
		self.logger.info(ev.port)
		

	@set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
	def _port_stats_reply_handler(self, ev):
		body = ev.msg.body
		self.logger.info('datapath         port     '
		                 'rx-pkts  rx-bytes rx-error '
		                 'tx-pkts  tx-bytes tx-error')
		self.logger.info('---------------- -------- '
		                 '-------- -------- -------- '
		                 '-------- -------- --------')

		for stat in sorted(body, key=attrgetter('port_no')):
			if stat.port_no != 0xfffffffe:
				if hasattr(self.ports[stat.port_no],'rx_bytes'):
					self.logger.info('%016x %8x %8d %8d %8d %8d %8d %8d', 
				                         ev.msg.datapath.id, stat.port_no,
				                         stat.rx_packets, stat.rx_bytes, stat.rx_errors,
				                         stat.tx_packets, stat.tx_bytes, stat.tx_errors)
					#calculate utilization on this port
					deltatraffic= (stat.rx_bytes - self.ports[stat.port_no].rx_bytes) + (stat.tx_bytes - self.ports[stat.port_no].tx_bytes)
					self.ports[stat.port_no].utilization = deltatraffic * 8 * 100 / (self.monitoring_time * self.linkBandwidth)
					self.logger.info('\nutilization port %d: %f', stat.port_no, self.ports[stat.port_no].utilization )
					self.ports[stat.port_no].tx_bytes = stat.tx_bytes
					self.ports[stat.port_no].rx_bytes = stat.rx_bytes


					if (self.ports[stat.port_no].utilization <= 10) and (self.ports[stat.port_no].connectedMac != None) and (self.ports[stat.port_no].rateConfig == 0):
						#install flows to the queue
						self.logger.info("installing queue flows")
						#url = 'http://localhost:8080/stats/flowentry/add'
						url = 'http://localhost:8080/qos/rules/0000000000000001'
					   	payload = {"match": {"dl_dst": self.ports[stat.port_no].connectedMac,"dl_type":"ARP" }, "actions":{"queue": "1"}}
						response = requests.post(url,data=json.dumps(payload))
						self.logger.info(response.text)
						self.ports[stat.port_no].rateConfig = 1
						#getting qos_id
						data = response.json()
						self.ports[stat.port_no].qos_id = self.logger.info(data[0]["command_result"][0]["details"].split("=")[1])

						
					elif (self.ports[stat.port_no].utilization > 10) or (self.ports[stat.port_no].rateConfig == 1):
						self.logger.info("deinstalling queue flows")
						url = 'http://localhost:8080/qos/rules/0000000000000001'
						payload = {"qos_id" :self.ports[stat.port_no].qos_id }
						response = requests.delete(url,data=json.dumps(payload))
						self.logger.info(response.text)



