from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib import hub

from ryu.lib.packet import ipv4
from ryu.lib.packet import tcp
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.ofproto import ether
from ryu.ofproto import inet
from ryu.ofproto import ofproto_v1_0

import requests
import json
import ast

class MultiPathDistributor(app_manager.RyuApp):
	def __init__(self, *args, **kwargs):
		super(MultiPathDistributor, self).__init__(*args, **kwargs)
		self.datapaths = {}
		self.routesNode1toNode2 = [{"1":"1,5", "4":"4,5"},
								   {"1":"1,2", "2":"1,2","4":"1,5"},
								  # {"1":"1,3","3":"1,2","4":"2,5"},
								   {"1":"1,4","4":"3,5"}
								   ]
		self.flowCounts=0 #for round-robin purpose
		self.ipNode1 = "10.0.0.1"
		self.ipNode2 = "10.0.0.2"
	
	@set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
	def _state_change_handler(self, ev):
		if ev.state == MAIN_DISPATCHER:
			self.installDefaultFlow()

	def installDefaultFlow(self):
		url = "http://localhost:8080/stats/flowentry/add"
		route_dict = self.routesNode1toNode2[0]
		print route_dict
		print route_dict.keys()
		for switch_dpid in route_dict.keys():
			print int(switch_dpid)
			inputport =  int(route_dict[switch_dpid].split(",")[0])
			outputport = int(route_dict[switch_dpid].split(",")[1])
			
			#default
			payload = {
			          "dpid": int(switch_dpid),
			          "table_id": 0,
			          "priority": 10,
			          "match": {
			             "in_port" : inputport,
			                },
			          "actions":[ 
			             {"type":"OUTPUT",
			             "port": outputport}
			          ]
			        }
			response = requests.post(url,data=json.dumps(payload))
			self.logger.info(response.text)

			#install reverse flow
			print int(switch_dpid)
			payload = {
			          "dpid": int(switch_dpid),
			          "table_id": 0,
			          "priority": 10,
			          "match": {
			             "in_port":outputport,
			                },
			          "actions":[ 
			             {"type":"OUTPUT",
			             "port": inputport}
			          ]
			        }
			response = requests.post(url,data=json.dumps(payload))
			self.logger.info(response.text)

		
		#send bbcp flow firstly to controller, the one entering node 1 or node 2
		payload = {
			          "dpid": 1,
			          "table_id": 0,
			          "priority": 15,
			          "match": {
			             "dl_type": 2048,
			             "nw_proto": 6,
			             "tp_dst": 5031,
			                },
			          "actions":[ 
			             {"type":"OUTPUT",
			             "port": ofproto_v1_0.OFPP_CONTROLLER
			             }
			          ]
			        }
		response = requests.post(url,data=json.dumps(payload))
		self.logger.info(response.text)
			


	def installFlowN(self,n,ipSrc,ipDst,tcpSrc,tcpDst):
		url = "http://localhost:8080/stats/flowentry/add"
		route_dict = self.routesNode1toNode2[n]
		for switch_dpid in route_dict.keys():
			inputport =  int(route_dict[switch_dpid].split(",")[0])
			outputport = int(route_dict[switch_dpid].split(",")[1])
			payload = {
			          "dpid": int(switch_dpid),
			          "table_id": 0,
			          "priority": 32768,
			          "match": {
			             "nw_src": ipSrc,
			             "dl_type": 2048,
			             "nw_dst": ipDst,
			             "tp_src": tcpSrc, 
			             "nw_proto": 6,
			             "tp_dst": tcpDst,
			                },
			          "actions":[ 
			             {"type":"OUTPUT",
			             "port": outputport}
			          ]
			        }
			response = requests.post(url,data=json.dumps(payload))
			self.logger.info(response.text)

			#install reverse flow
			payload = {
			          "dpid": int(switch_dpid),
			          "table_id": 0,
			          "priority": 32768,
			          "match": {
			             "nw_dst": ipSrc,
			             "dl_type": 2048,
			             "nw_src": ipDst,
			             "tp_dst": tcpSrc, 
			             "nw_proto": 6,
			             "tp_src": tcpDst,
			                },
			          "actions":[ 
			             {"type":"OUTPUT",
			             "port": inputport}
			          ]
			        }
			response = requests.post(url,data=json.dumps(payload))
			self.logger.info(response.text)



	@set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
	def _packet_in_handler(self, ev):
		# If you hit this you might want to increase
	    # the "miss_send_length" of your switch
		if ev.msg.msg_len < ev.msg.total_len:
			self.logger.debug("packet truncated: only %s of %s bytes",
	                          ev.msg.msg_len, ev.msg.total_len)
		msg = ev.msg
		datapath = msg.datapath
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser

		pkt = packet.Packet(msg.data)
		eth = pkt.get_protocols(ethernet.ethernet)[0]

		if eth.ethertype == ether.ETH_TYPE_IP:
			ip = pkt.get_protocols(ipv4.ipv4)[0]
			srcIP = ip.src
			dstIP = ip.dst

			self.logger.info("packet in %s %s %s %s", datapath.id, srcIP, dstIP, msg.in_port)
			if (srcIP ==self.ipNode1 and dstIP == self.ipNode2):

				print ip.proto

				if (ip.proto == inet.IPPROTO_TCP):
					tcp_pkt = pkt.get_protocols(tcp.tcp)[0]
					srcTCP = tcp_pkt.src_port
					dstTCP = tcp_pkt.dst_port

					print "tcp packet is received"
					print srcTCP
					print dstTCP

					#bbcp flows
					if (dstTCP == 5031):
						#self,n,ipSrc,ipDst,tcpSrc,tcpDst
						whichFlow = self.flowCounts % len(self.routesNode1toNode2)
						self.installFlowN(whichFlow,srcIP,dstIP,srcTCP,dstTCP)
						self.flowCounts = self.flowCounts + 1
						self.logger.info("number of bbcp flows: %d",self.flowCounts)
						self.logger.info("last bbcp flow  is installed to path %d",whichFlow)





		dst = eth.dst
		src = eth.src

		dpid = datapath.id
		#self.mac_to_port.setdefault(dpid, {})

		self.logger.info("packet in %s %s %s %s", dpid, src, dst, msg.in_port)

		





