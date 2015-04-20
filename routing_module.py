import logging
import struct

from ryu.base import app_manager
from ryu.controller import mac_to_port
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0,ofproto_v1_3
from ryu.lib.mac import haddr_to_bin
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.ofproto import ether
from ryu.ofproto import inet
from ryu.topology.api import get_switch, get_link
from ryu.app.wsgi import ControllerBase
from ryu.topology import event, switches 
from ryu.controller import dpset

#from proxy_arp import ProxyARP
#import proxy_arp
import networkx as nx

class RoutingModule(app_manager.RyuApp):
	OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION,ofproto_v1_3.OFP_VERSION]

	_CONTEXTS = {
		'dpset': dpset.DPSet,
	}

	net=nx.DiGraph()

	def __init__(self, *args, **kwargs):
		super(RoutingModule, self).__init__(*args, **kwargs)

		if kwargs.has_key('dpset'):
			self.dpset = kwargs['dpset']

		self.topology_api_app = self
		
		self.nodes = {}
		self.links = {}



	#def add_flow(self, datapath, in_port, dst, actions):
	def add_flow(self, datapath, dst,priority,actions):
		ofproto = datapath.ofproto

		#match = datapath.ofproto_parser.OFPMatch(
		#	in_port=in_port, dl_dst=haddr_to_bin(dst))

		match = datapath.ofproto_parser.OFPMatch(
			dl_dst=haddr_to_bin(dst))

		mod = datapath.ofproto_parser.OFPFlowMod(
			datapath=datapath, match=match, cookie=0,
			command=ofproto.OFPFC_ADD, idle_timeout=0, hard_timeout=0,
			priority=priority,
			flags=ofproto.OFPFF_SEND_FLOW_REM, actions=actions)
		datapath.send_msg(mod)


	@set_ev_cls(event.EventSwitchEnter)
	def get_topology_data(self, ev):
		switch_list = get_switch(self.topology_api_app, None)   
		switches=[switch.dp.id for switch in switch_list]
		RoutingModule.net.add_nodes_from(switches)
	
		links_list = get_link(self.topology_api_app, None)
		#print links_list
		links=[(link.src.dpid,link.dst.dpid,{'port':link.src.port_no}) for link in links_list]
		#print links
		RoutingModule.net.add_edges_from(links)
		links=[(link.dst.dpid,link.src.dpid,{'port':link.dst.port_no}) for link in links_list]
		#print links
		RoutingModule.net.add_edges_from(links)
		print "**********List of links"
		print RoutingModule.net.edges()



	def installEndToEndRoute(self,path):
		
		mac_src = path[0]
		mac_dst = path[-1]

		real_path = path[1:len(path)-1]
		print real_path

		for dpid in real_path:
			next=path[path.index(dpid)+1]
			out_port=RoutingModule.net[dpid][next]['port']
			datapath = self.dpset.get(dpid)
			actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
			self.add_flow(datapath, mac_dst,1, actions)

			#install reverse flow
			next=path[path.index(dpid)-1]
			out_port=RoutingModule.net[dpid][next]['port']
			actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
			self.add_flow(datapath, mac_src,1, actions)

	@set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
	def _packet_in_handler(self, ev):
		msg = ev.msg
		datapath = msg.datapath
		ofproto = datapath.ofproto
		if ofproto.OFP_VERSION == ofproto_v1_0.OFP_VERSION:
			in_port = msg.in_port
		elif ofproto.OFP_VERSION == ofproto_v1_3.OFP_VERSION:
			in_port = msg.match["in_port"]

		pkt = packet.Packet(msg.data)

		eth = pkt.get_protocol(ethernet.ethernet)
		dst = eth.dst
		src = eth.src

		dpid = datapath.id
		
		#find the location of the dst's switch
		#dstLoc = ProxyARP.getDPIDnPort(dst)

		if eth.ethertype == ether.ETH_TYPE_IP:
			#get shortest path
			path=nx.shortest_path(RoutingModule.net,eth.src,eth.dst)
			print path
			self.installEndToEndRoute(path)








