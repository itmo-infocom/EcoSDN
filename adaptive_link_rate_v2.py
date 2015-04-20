import logging
import json
from webob import Response


from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.controller import dpset
from ryu.app.wsgi import ControllerBase, WSGIApplication

from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ipv4
from ryu.lib.packet import arp
from ryu.ofproto import ether
from ryu.ofproto import ofproto_v1_0, ofproto_v1_3
from ryu.lib import dpid as dpid_lib

import utilization_event
import MyPorts
import HP3600.cli

class AdaptiveLinkRate(app_manager.RyuApp):
	OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
	_EVENTS =  [utilization_event.UtilizationEvent]

	def __init__(self, *args,**kwargs):
		super(AdaptiveLinkRate,self).__init__(*args,**kwargs)


	

	"""
	def activateALR(dpid,port,bwArray,threshold):
		
		MyPorts.portUtils[dpid][port].alr_enabled = True
		MyPorts.portUtils[dpid][port].threshold = threshold
		MyPorts.portUtils[dpid][port].bwArray = bwArray


	def disableALR(dpid,port):
		MyPorts.portUtils[dpid][port].alr_enabled = False
	"""

	def set_alr_status(self,switchid,portid,enabled,threshold,bwArray):
		MyPorts.portUtils[switchid][portid].alr_enabled = enabled
		MyPorts.portUtils[switchid][portid].threshold = threshold
		if not(bwArray ==None):
			MyPorts.portUtils[switchid][portid].bwArray = bwArray
		return True

	def getstatus(self,switchid,portid):
		return MyPorts.portUtils[switchid][portid].alr_enabled

	def setPortSpeed(self,ip,portToConfigure,speed):
		client,chan = HP3600.cli.connect(host=ip)
		out = set_speed(chan,portToConfigure,speed)
		print out

		chan.close()
		client.close()

	def getPortSpeed(self,ip,portToConfigure,speed):
		client,chan = HP3600.cli.connect(host=ip)
		out = get_speed(chan,portToConfigure)
		print out

		chan.close()
		client.close()

	@set_ev_cls(utilization_event.UtilizationEvent)
	def UtilizationEventHandler(self,ev):
		for dpid,ports in MyPorts.portUtils.iteritems():
			for myPort in ports:
				if myPort.alr_enabled:
					if myPort.utilization < myPort.threshold and myPort.bandwidth > myPort.bwArray[0]:
							# need to lower down the bw
							self.switchBandwidth(dpid,myPort.port_no,myPort.bwArray[0])
					elif myPort.utilization > myPort.threshold and myPort.bandwidth < myPort.bwArray[1]:
							# "need to up the bw"
							self.switchBandwidth(dpid,myPort.port_no,myPort.bwArray[1])

	def switchBandwidth(self,dpid,port,bw):
		#need to implement for the HP switch
		print "todo: switch port %d to %f"%(port,bw)




		

