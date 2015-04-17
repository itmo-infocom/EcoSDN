from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib import hub

from ryu.lib.packet import tcp
from ryu.lib.packet import ipv4
from ryu.lib.packet import vlan
from ryu.lib.packet import ethernet
from ryu.lib.packet import packet
from ryu.ofproto import ether
from ryu.ofproto import inet
from ryu.ofproto import ofproto_v1_3

import requests
import json
import ast

class MultiPathDistributor(app_manager.RyuApp):
	OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
	def __init__(self, *args, **kwargs):
		super(MultiPathDistributor, self).__init__(*args, **kwargs)
		self.datapaths = {}
		self.dpids=[1152966113386660480,1152966113386676544,1152966113385875392,1152966113386367424]
		self.routesNode1toNode2 = [{1152966113386660480:"3,15", 1152966113386367424:"15,4"},
								   {1152966113386660480:"3,14", 1152966113385875392:"14,15",1152966113386367424:"13,4"},
								   {1152966113386660480:"3,13",1152966113386676544:"13,15",1152966113386367424:"14,4"},
								   {1152966113386660480:"3,16",1152966113386367424:"16,4"}
								   ]
		self.flowCounts=0 #for round-robin purpose
		self.ipNode1 = "10.10.2.14"
		self.ipNode2 = "10.10.2.129"
	
	@set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
	def _state_change_handler(self, ev):
		if ev.state == MAIN_DISPATCHER:
			self.installDefaultHPFlow()
			self.installDefaultFlow()

	def installDefaultHPFlow(self):
		url = "http://localhost:8080/stats/flowentry/add" 
		for switch_dpid in self.dpids:
			payload = {
                                  "dpid": switch_dpid,
                                  "table_id": 100,
                                  "priority": 0,
                                  "match": {
                                     
                                        },
                                  "actions":[
                                     {"type":"GOTO_TABLE",
                                     "table_id": 200}
                                  ]
                                }
			response = requests.post(url,data=json.dumps(payload))
			self.logger.info(response.text)
			

	def installDefaultFlow(self):
		url = "http://localhost:8080/stats/flowentry/add"
		route_dict = self.routesNode1toNode2[0]
		for switch_dpid in route_dict.keys():
			inputport =  int(route_dict[switch_dpid].split(",")[0])
			outputport = int(route_dict[switch_dpid].split(",")[1])
			
			#default
			payload = {
			          "dpid": switch_dpid,
			          "table_id": 100,
			          "priority": 1,
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
			payload = {
			          "dpid": switch_dpid,
			          "table_id": 100,
			          "priority": 1,
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
		        "dpid": 1152966113386660480,
			"table_id":100,
			"priority":3,
			"match":{
				"dl_type": 0x800,
				"ip_proto":6,
				"tcp_dst": 5031,
				"ipv4_src":self.ipNode1,
				"ipv4_dst":self.ipNode2
			},
			"actions":[
				{
					"type":"GOTO_TABLE",
					"table_id":200		
				}
			]

		}
		response = requests.post(url,data=json.dumps(payload))
		self.logger.info(response.text)


		payload = {
			          "dpid": 1152966113386660480,
			          "table_id": 200,
			          "priority": 15,
			          "match": {
			             "dl_type": 0x0800,
			             "nw_proto": 6,
			             "tp_dst": 5031
			                },
			          "actions":[ 
			             {"type":"OUTPUT",
			             "port": ofproto_v1_3.OFPP_CONTROLLER
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
			          "dpid": switch_dpid,
			          "table_id": 100,
			          "priority": 30,
			          "match": {
			             "ipv4_src": ipSrc,				  
			             "eth_type": 0x800,
			             "ipv4_dst": ipDst,
			             "tcp_src": tcpSrc, 
			             "ip_proto": 6,
			             "tcp_dst": tcpDst,
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
			          "dpid": switch_dpid,
			          "table_id": 100,
			          "priority": 30,
			          "match": {				    
			             "ipv4_dst": ipSrc,
			             "eth_type": 0x800,
			             "ipv4_src": ipDst,
			             "tcp_dst": tcpSrc, 
			             "ip_proto": 6,
			             "tcp_src": tcpDst,
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
		
		print eth.ethertype

		if eth.ethertype == ether.ETH_TYPE_8021Q:
			ip = pkt.get_protocols(ipv4.ipv4)[0]
			srcIP = ip.src
			dstIP = ip.dst

			self.logger.info("packet in %s %s %s %s", datapath.id, srcIP, dstIP, msg.match['in_port'])
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

		#self.logger.info("packet in %s %s %s %s", dpid, src, dst, msg.in_port)

		




