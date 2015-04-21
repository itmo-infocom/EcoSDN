import paramiko
import sys
import select
import re

def connect(host = '10.10.10.13', user = 'root', secret = '123456', port = 22):

	client = paramiko.SSHClient()
	client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	client.connect(hostname=host, username=user, password=secret, port=port)

	chan = client.invoke_shell()
	chan.settimeout(0.0)

	sw_rd(chan)
	chan.send('\n')
	sw_rd(chan)
	#chan.send('show version\n')
	#sw_rd(chan)

	return client, chan


def sw_rd(chan):
	out = ''
	r, w, e = select.select([chan, sys.stdin], [], [])

	if chan in r:
		try:
			x = chan.recv(1024)
			if len(x) == 0:
				return x
			out += x
		except socket.timeout:
			pass

	return out


#to set bandwidth-min output
def set_bw(chan, port=20, bw='50 50 0 0 0 0 0 0'): 
	import types

	out = []
	if type(port) == types.StringType:
		port = int(port)
	if type(bw) == types.ListType or type(bw) == types.TupleType:
		bw = reduce (lambda x, y: str(x) + ' ' + str(y), bw)

	chan.send('config\n')
	out.append(sw_rd(chan))
	chan.send('int %d bandwidth-min output %s\n' % (port, bw))
	out.append(sw_rd(chan))

	return out

#to get bandwidth-min output
def get_bw(chan, port=20):
	out = []
	chan.send('show bandwidth output %d\n' % port)
	out.append(sw_rd(chan))
	out.append(sw_rd(chan))

	return out


#to set port speed
def set_speed(chan,port=20,speed=1000):
	import types

	out = []
	if type(port) == types.StringType:
		port = int(port)
	if type(speed) == types.StringType:
		speed = int(speed)

	chan.send('config\n')
	out.append(sw_rd(chan))
	chan.send('int %d speed-duplex auto-%d\n' % (port,speed))
	out.append(sw_rd(chan))
	out.append(sw_rd(chan))

	return out

def get_speed(chan,port=20):
	import types

	out = []
	if type(port) == types.StringType:
		port = int(port)

	chan.send('show int brief %d\n' % port)
	out.append(sw_rd(chan))
	out.append(sw_rd(chan))
	#out.append(sw_rd(chan))
	#out.append(sw_rd(chan))
	
	for entry in out:
		temp = re.findall('\d+FDx',entry)
		if temp:
			return temp[0]

	return out

def enableDisablePort(chan,status,port=20):
	import types
	out = []
	if type(port) == types.StringType:
		port = int(port)

	chan.send('config\n')
	out.append(sw_rd(chan))
	if status == 0:
		chan.send("int %d disable\n" % (port))
		print "port %d is disabled" % (port)
	else:
		chan.send("int %d enable\n" % (port))
		print "port %d is enabled" % (port)		
	out.append(sw_rd(chan))

	return out

	





