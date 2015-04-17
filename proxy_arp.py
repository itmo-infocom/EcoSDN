# ported from https://github.com/mbredel/floodlight-proxyarp/blob/master/src/main/java/net/floodlightcontroller/proxyarp/ARPProxy.java
# the idea is to broadcast ARP requests to all the switches's ports which are not connected to a switch
# todo: removing old arp requests

import logging
import struct

from ryu.base import app_manager
from ryu.controller import dpset
from ryu.controller import mac_to_port
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0, ofproto_v1_3
from ryu.lib.mac import haddr_to_bin
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import arp
from ryu.ofproto import ether
from ryu.lib import dpid as dpid_lib

import time
import requests
import json
import ast

class ARPRequest(object):
	def __init__(self, sourceMACAddress,sourceIPAddress,targetMACAddress,targetIPAddress,datapath,inPort):
		super(ARPRequest, self).__init__()
		self.sourceMACAddress = sourceMACAddress
		self.sourceIPAddress  = sourceIPAddress
		self.targetMACAddress = targetMACAddress
		self.targetIPAddress = targetIPAddress
		self.datapath = datapath
		self.inPort = inPort
		self.startTime = 0

class ProxyARP(app_manager.RyuApp):
	OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION,ofproto_v1_3.OFP_VERSION]

	_CONTEXTS = {
		'dpset': dpset.DPSet,
	}

	def __init__(self, *args, **kwargs):
		super(ProxyARP, self).__init__(*args, **kwargs)
		self.ip_to_mac = {}
		self.arpRequests={}
		self.dpset = None
		self.enabled = True
		if kwargs.has_key('dpset'):
			self.dpset = kwargs['dpset']
		

	def getMac(self,ipAddress):
		#return self.ip_to_mac[dpid][ipAddress]
		macAddress = None
		for dpid,ip_macs in self.ip_to_mac.iteritems():
			for ipAddr in ip_macs:
				if ipAddr == ipAddress:
					macAddress = ip_macs[ipAddr]
					return macAddress
		return macAddress

	def setStatus(self, enabled):
		self.enabled = enabled

	@set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
	def _packet_in_handler(self, ev):
		
		if not(self.enabled):
			return

		msg = ev.msg

		datapath = msg.datapath
		dpid = datapath.id
		ofproto = datapath.ofproto
		if ofproto.OFP_VERSION == ofproto_v1_0.OFP_VERSION:
			in_port = msg.in_port
		elif ofproto.OFP_VERSION == ofproto_v1_3.OFP_VERSION:
			in_port = msg.match["in_port"]

		pkt = packet.Packet(msg.data)
		eth = pkt.get_protocols(ethernet.ethernet)[0]

		if not(eth.ethertype == ether.ETH_TYPE_ARP):
			print eth.ethertype
			return

		self.ip_to_mac.setdefault(dpid, {})

		#get the ARP packet
		arp_pkt = pkt.get_protocols(arp.arp)[0]

		#learn the ip-mac
		self.ip_to_mac[dpid][arp_pkt.src_ip] = arp_pkt.src_mac
		print "learning ip-mac: host "+arp_pkt.src_mac+ " is at %d port %d" % (dpid,in_port)

		if (arp_pkt.opcode == arp.ARP_REQUEST):
			self.handleARPRequest(arp_pkt,datapath,in_port)

		if (arp_pkt.opcode == arp.ARP_REPLY):
			self.handleARPReply(arp_pkt,datapath,in_port)
			print "preparing to send arpreply"


	def handleARPRequest(self,arp_pkt,datapath,in_port):
		dpid = datapath.id
		sourceIPAddress = arp_pkt.src_ip
		sourceMACAddress = arp_pkt.src_mac
		targetIPAddress = arp_pkt.dst_ip
		targetMACAddress = ""

		self.logger.info("Received arp request from "+sourceMACAddress)

		#check if there is ongoing ARP process for this packet
		if (self.arpRequests.has_key(targetIPAddress)):
			startTime = int(round(time.time() * 1000))
			arpRequestSet = self.arpRequests[targetIPAddress]
			for arpReq in arpRequestSet:
				arpReq.startTime = startTime


		#check if the requested host is on the table already
		if targetIPAddress in self.ip_to_mac[dpid]:
			targetMACAddress = self.ip_to_mac[dpid][targetIPAddress]
			arpRequest = ARPRequest(sourceMACAddress,sourceIPAddress,targetMACAddress,targetIPAddress,datapath,in_port)
			#send ARP reply
			self.sendARPReply(arpRequest)
		else:
			arpRequest = ARPRequest(sourceMACAddress,sourceIPAddress,None,targetIPAddress,datapath,in_port)
			#ut this request into requests list
			if not(self.arpRequests.has_key(targetIPAddress)):
				self.arpRequests[targetIPAddress]= set()
			self.arpRequests[targetIPAddress].add(arpRequest)

			#send arp request
			self.sendARPRequest(arpRequest)

	def handleARPReply(self,arp_pkt,datapath,in_port):
		dpid = datapath.id
		print dpid
		#ip addres of arp target
		targetIPAddress = arp_pkt.src_ip
		print targetIPAddress

		print self.arpRequests

		arpRequestSet = self.arpRequests.pop(targetIPAddress,None)
		print arpRequestSet

		if arpRequestSet == None:
			return

		for arpRequest in arpRequestSet:
			arpRequest.targetMACAddress = arp_pkt.src_mac
			self.sendARPReply(arpRequest)
			#may need to remove the arpRequest ?

	def sendARPRequest(self,arpRequest):
		ARP_Request = packet.Packet()
		ARP_Request.add_protocol(ethernet.ethernet(
		    ethertype=ether.ETH_TYPE_ARP,
		    dst="ff:ff:ff:ff:ff:ff",
		    src=arpRequest.sourceMACAddress))

		ARP_Request.add_protocol(arp.arp(
		    opcode=arp.ARP_REQUEST,
		    src_mac=arpRequest.sourceMACAddress,
		    src_ip=arpRequest.sourceIPAddress,
		    #dst_mac=arpRequest.targetMACAddress,
		    dst_ip=arpRequest.targetIPAddress))

		ARP_Request.serialize()


		#send ARP request to all attachment point ports of the switches
		switchesAttachmentPointPorts = self.getAllSwitchAttachmentPointPorts()
		for switchDpid in switchesAttachmentPointPorts.keys():
			print switchDpid
			portsSet = switchesAttachmentPointPorts[switchDpid]

			for aPort in portsSet:
				print arpRequest.datapath.id
				print arpRequest.inPort 
				if switchDpid == arpRequest.datapath.id and arpRequest.inPort == aPort:
					continue
				#send this arp request
				datapath = self.dpset.get(switchDpid)
				#print self.dpset.get_all()
				#print datapath
				actions = []
				actions.append(datapath.ofproto_parser.OFPActionOutput(aPort) )
				out = datapath.ofproto_parser.OFPPacketOut(
						datapath=datapath,
						buffer_id=datapath.ofproto.OFP_NO_BUFFER,
						in_port=datapath.ofproto.OFPP_CONTROLLER,
						actions=actions, data=ARP_Request.data)
				datapath.send_msg(out)
				print "arp request sent to %d at port %d" %(switchDpid,aPort)


	def sendARPReply(self,arpRequest):
		ARP_Request = packet.Packet()
		ARP_Request.add_protocol(ethernet.ethernet(
		    ethertype=ether.ETH_TYPE_ARP,
		    dst=arpRequest.sourceMACAddress,
		    src=arpRequest.targetMACAddress))

		ARP_Request.add_protocol(arp.arp(
		    opcode=arp.ARP_REPLY,
		    src_mac=arpRequest.targetMACAddress,
		    src_ip=arpRequest.targetIPAddress,
		    dst_mac=arpRequest.sourceMACAddress,
		    dst_ip=arpRequest.sourceIPAddress))

		ARP_Request.serialize()
		datapath = arpRequest.datapath
		actions = []
		actions.append(datapath.ofproto_parser.OFPActionOutput(
		        arpRequest.inPort))

		out = datapath.ofproto_parser.OFPPacketOut(
				datapath=datapath,
				buffer_id=datapath.ofproto.OFP_NO_BUFFER,
				in_port=datapath.ofproto.OFPP_CONTROLLER,
				actions=actions, data=ARP_Request.data)
		datapath.send_msg(out)
		print "ARP reply sent to %d at port %d"%(datapath.id,arpRequest.inPort)


	def getAllSwitchAttachmentPointPorts(self):
		url = "http://localhost:8080/v1.0/topology/switches"
		response = requests.get(url)
		switch_and_attachment={}
		switchArray = ast.literal_eval(response.text)
		for switch in switchArray:
			switchDpid = int(self.skipZero(switch["dpid"]))
			switch_and_attachment[switchDpid] = set() #create a set, i hope so
			
			for detail in switch["ports"]:
				portNo = int(self.skipZero(detail["port_no"]))
				switch_and_attachment[switchDpid].add(portNo)

			#check if a port is connected to a switch
			url = "http://localhost:8080/v1.0/topology/links/"+switch["dpid"]
			response = requests.get(url)
			linkArray = ast.literal_eval(response.text)
			setOfPortsToOtherSwitch = set()
			
			for aLink in linkArray:
				portNo = int(self.skipZero(aLink["src"]["port_no"]))
				setOfPortsToOtherSwitch.add(portNo)

			switch_and_attachment[switchDpid] = switch_and_attachment[switchDpid] - setOfPortsToOtherSwitch 

		return switch_and_attachment


	def skipZero(self,aString):
		index=0
		while (index < len(aString)):
			if (aString[index]!='0'):
				break
			else:
				index = index + 1
		return aString[index::]










