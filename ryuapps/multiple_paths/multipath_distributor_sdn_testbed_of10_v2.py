from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib import hub
from ryu.controller import dpset

from ryu.lib.packet import tcp
from ryu.lib.packet import ipv4
from ryu.lib.packet import vlan
from ryu.lib.packet import ethernet
from ryu.lib.packet import packet
from ryu.ofproto import ether
from ryu.ofproto import inet
from ryu.ofproto import ofproto_v1_0

from ryu.lib.ip import ipv4_to_bin

import requests
import json
import ast
import struct

class MultiPathDistributor(app_manager.RyuApp):
	#OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]
	_CONTEXTS = {
		'dpset':dpset.DPSet,
	}
	def __init__(self, *args, **kwargs):
		super(MultiPathDistributor, self).__init__(*args, **kwargs)
		self.datapaths = {}
		self.dpids=[1152966113386660480,1152966113386676544,1152966113385875392,1152966113386367424]
		self.routesNode1toNode2 = [  {1152966113386660480:"3,15", 1152966113386367424:"15,4"},
								 # {1152966113386660480:"3,13", 1152966113385875392:"13,15",1152966113386367424:"14,4"},
								 #  {1152966113386660480:"3,14",1152966113386676544:"14,15",1152966113386367424:"13,4"},
								   {1152966113386660480:"3,16",1152966113386367424:"16,4"}
								   ]
		self.flowCounts=0 #for round-robin purpose
		self.ipNode1 = "10.10.2.14"
		self.ipNode2 = "10.10.2.129"
		self.dpset = kwargs['dpset']
		self.appPort = 5031
		
	
	@set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
	def _state_change_handler(self, ev):
		if ev.state == MAIN_DISPATCHER:
			
			#self.installDefaultHPFlow()
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
			     	     #{"type":"STRIP_VLAN"},
                                     {"type":"GOTO_TABLE",
                                     "table_id": 200}
                                  ]
                                }
			response = requests.post(url,data=json.dumps(payload))
			self.logger.info(response.text)
			

	def installDefaultFlow(self):
		url = "http://localhost:8080/stats/flowentry/modify"

		#route_dict = self.routesNode1toNode2[3]
		#route_dict = {1152966113386660480:"3,16",1152966113386367424:"16,4"}
		route_dict = {1152966113386660480:"3,13", 1152966113385875392:"13,15",1152966113386367424:"14,4"}
		for switch_dpid in route_dict.keys():
			inputport =  int(route_dict[switch_dpid].split(",")[0])
			outputport = int(route_dict[switch_dpid].split(",")[1])
			
			#default
			payload = {
			          "dpid": switch_dpid,
			          "table_id": 0,
			          "priority": 2,
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
			          "table_id": 0,
			          "priority": 2,
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
		
			
		payload = {
			          "dpid": 1152966113386660480,
			          "table_id": 0,
			          "priority": 15,
			          "match": {
			            "dl_type": 0x800,
			             "nw_proto": 6,
			             "tp_dst": self.appPort
			                },
			          "actions":[ 
				
			             {"type":"OUTPUT",
			             "port": ofproto_v1_0.OFPP_CONTROLLER
			             },
				    
	
			          ]
			        }
		response = requests.post(url,data=json.dumps(payload))
		self.logger.info(response.text)
			
	
	def add_flow(self, datapath, priority, match, actions):
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser

		#inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                #                             actions)]

		mod = parser.OFPFlowMod(datapath=datapath,match=match, cookie=0,
                                command=ofproto.OFPFC_ADD,priority=priority,flags=ofproto.OFPFF_SEND_FLOW_REM, actions=actions)
		datapath.send_msg(mod)

	
	def installFlowN(self,n,ipSrc,ipDst,tcpSrc,tcpDst,dlSrc,dlDst):

		ipSrc = struct.unpack('!I', ipv4_to_bin(ipSrc))[0]
		ipDst = struct.unpack('!I', ipv4_to_bin(ipDst))[0]
		url = "http://localhost:8080/stats/flowentry/modify"
		route_dict = self.routesNode1toNode2[n]
		for switch_dpid in route_dict.keys():
			inputport =  int(route_dict[switch_dpid].split(",")[0])
			outputport = int(route_dict[switch_dpid].split(",")[1])
			
			datapath = self.dpset.get(switch_dpid)
			parser = datapath.ofproto_parser
			match = parser.OFPMatch(nw_src=ipSrc,dl_type=2048,nw_dst=ipDst,nw_proto=6,tp_src=int(tcpSrc),tp_dst=int(tcpDst))
			actions = [parser.OFPActionOutput(outputport)]
			self.add_flow(datapath,500,match,actions)		
				

			match = parser.OFPMatch(nw_src=ipDst,dl_type=2048,nw_dst=ipSrc,nw_proto=6,tp_src=int(tcpDst),tp_dst=int(tcpSrc))
			actions = [parser.OFPActionOutput(inputport)]
			self.add_flow(datapath,500,match,actions)		

		


	def _send_packet(self, datapath, port, pkt):
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser
		pkt.serialize()
		self.logger.info("packet-out %s" % (pkt,))
		data = pkt.data
		actions = [parser.OFPActionOutput(port=port)]
		out = parser.OFPPacketOut(datapath=datapath,
                                  buffer_id=ofproto.OFP_NO_BUFFER,
                                  in_port=ofproto.OFPP_CONTROLLER,
                                  actions=actions,
                                  data=data)
		datapath.send_msg(out)


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

		dlSrc = eth.src
		dlDst = eth.dst
		
		print "\nNew packet-in"
		print "dpid %d"%(datapath.id)
		print "eth.ethertype %04x" %(eth.ethertype)
		print "eth contents: "
		print eth

		if not(datapath.id==1152966113386660480):
			return

		#print vlan packet info
		print "vlan info"
		pkt_vlan = pkt.get_protocols(vlan.vlan)[0]
		print "vlan id: %d"%(pkt_vlan.vid)
		print "vlan ethertype: %04x"%(pkt_vlan.ethertype)
		print "\n"

		if eth.ethertype == ether.ETH_TYPE_IP or eth.ethertype == ether.ETH_TYPE_8021Q :
		#if eth.ethertype == ether.ETH_TYPE_IP:
			#print "vlan tagged packet received"
			if (pkt.get_protocols(ipv4.ipv4)):
				ip = pkt.get_protocols(ipv4.ipv4)[0]
				srcIP = ip.src
				dstIP = ip.dst
				
				self.logger.info("packet in dpid:%s srcIP:%s dstIP:%s in_port:%s", datapath.id, srcIP, dstIP, msg.in_port)
				if (srcIP ==self.ipNode1 and dstIP == self.ipNode2):

					print "ip proto: %d"%(ip.proto)

					if (ip.proto == inet.IPPROTO_TCP):
						tcp_pkt = pkt.get_protocols(tcp.tcp)[0]
						srcTCP = tcp_pkt.src_port
						dstTCP = tcp_pkt.dst_port

						print "a tcp packet is received, tcpSrc:%d , tcpDst:%d\n"%(srcTCP,dstTCP)
						
					

						#bbcp flows
						if (dstTCP == self.appPort):
							#self,n,ipSrc,ipDst,tcpSrc,tcpDst
							whichFlow = self.flowCounts % len(self.routesNode1toNode2)
							self.installFlowN(whichFlow,srcIP,dstIP,srcTCP,dstTCP,dlSrc,dlDst)
							self.flowCounts = self.flowCounts + 1
							self.logger.info("number of bbcp flows: %d",self.flowCounts)
							self.logger.info("last bbcp flow  is installed to path %d",whichFlow)
							
							#new_pkt = packet.Packet()
							#new_pkt.add_protocol(eth)
							#new_pkt.add_protocol(ip)
							#new_pkt.add_protocol(tcp_pkt)
							#self._send_packet(datapath,15,new_pkt)



		#dst = eth.dst
		#src = eth.src

		#dpid = datapath.id
		#self.mac_to_port.setdefault(dpid, {})

		#self.logger.info("packet in %s %s %s %s", dpid, src, dst, msg.in_port)

		




