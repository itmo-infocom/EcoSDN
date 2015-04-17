###Saving Energy in redundank links
This modules gives a sample on a network which uses both links in a redundant connection, or uses only 1 link when the utilization in the network is low.

Python modules needed: requests
<br>
To install: ```$ pip install requests ```

<br>
#####Run mininet:
```bash
$ sudo python redundantlinks.py
```

<br>
#####Run the modules:
```bash
$ ryu-manager ofctl_rest.py host_tracker.py port_stats_reporter.py redundant_saving.py  
```

<br>
#####Testing:
open xterm on h1 and h4 for example.
```bash
mininet> xterm h1 h4
```
then on h1:
```bash
$ iperf -s -u -p 9999 -i 1
```

on h4: with duration of 60 seconds
```bash
$ iperf -c 10.0.0.1 -u -p 9999 -b 10M -t 60 
```

During this test, utilization will reach 100%. This results in link 2 to be activated, and some flows will be routed through it. It can be checked by seeing at the flow stats. Some will output port of 2.

After the test, link 2 will disabled, as the utilization becomes very less. Also can be checked via the flow stats.
