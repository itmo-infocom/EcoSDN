This is a module to enable the usage of multipaths in a network.

It is assumed that the paths are known.
Also, the idea is to have 1 default path which is used to transfer any traffic.
But to install BBCP traffic (or other kind of traffic) on to different paths, based on its TCP source port.

Requirement:
- BBCP tool to transfer huge files at line rate [https://www.slac.stanford.edu/~abh/bbcp/](https://www.slac.stanford.edu/~abh/bbcp/)
- ryu's ofctl_rest.py to install flows via REST

</br>

To try the module.
Run mininet:
```bash
# sudo python multipath_network.py
```

Run the module:
```bash
# sudo python ~/ryu/ryu/app/ofctl_rest.py multipath_network.py
```

Testing:
start xterm on h1 and h2
```bash
> xterm h1 h2
```

On h1's xterm
```bash
> bbcp -P 2 -s 4 file_to_transfer mininet@10.0.0.2:/home/mininet/destination
```

It is possible to check by looking at the flow statistics on the switch.
Or by looking at the bbcp transfer rate, when the number of paths is changed.


