<p align="center">
<img src="/static/images/PyRP.png">
</p>
<h1 align="center">(Python Routing Project)</h1>

## Description

PyRP ("perp") is a python implementation of a routing control plane from the ground up. The goal is to 
implement at least one genuine existing routing protocol well enough to be able to exchange routes with real routers
more or less transparently.  Ideally I'd like to be able to "round-trip" a routes from a real router through PyRP and 
back to another real router. The protocols I'm currently considering for this are: 

* Various RIP versions 
* BGP

PyRP is NOT really ever intended to forward any real packets.  It has just enough of a forwarding plane to be able to interact with the rest of the network.

PyRP is also NOT intended to offer any new ideas about routing protocols.  I don't have ANY ideas in that regard.

PyRP does include at least one toy "new protocol", and might include more in the future.  These are just to stand-in for 
real protocols while scaffolding the rest of the control plane. 

## Installation
idk

## Architecture

PyRP is built around independent services. Currently, communication between services is via FastAPI REST APIs.  This will
likely change to a message bus in the future.  The intent is that the Control Plane itself is one service, while each 
protocol implementation will be a separate service.  The Control Plane service will be responsible for ingestion of config 
and coordinating the exchange of routes between the various protocol services.

## Usage
Notably the rp_sla service requires root access.  This is required to send and receive ICMP packets.  Don't run this anywhere
that sounds like a bad idea.

Currently you start each service in a separate terminal or process: 
```bash
# Start the control plane on port 5010 (per config.toml)
❯ pipenv shell
Launching subshell in virtual environment...

routing_protocol_o-vkX6418L ❯ python /home/wrgeo/projects/routing_protocol_o/api_control_plane.py 
```
```bash
# Start the rp_sla service on port 5023 (per config.toml)
❯ pipenv shell
Launching subshell in virtual environment...

routing_protocol_o-vkX6418L ❯ pythonSudo.sh /home/wrgeo/projects/routing_protocol_o/api_rp_sla.py  
```

Once they're both launched, you tell the control-plane to ingest config via a POST to 
http://localhost:5010/instances/new_from_config?filename=tests/files/main.toml
which nets an instance id in response:
```json
{
    "instance_id": "84wPluBR"
}
```

This will instantiate the control plane.  Given the config, it will also reach out to the rp_sla service and instantiate that as well.
From there you can interact with either of them via their respective APIs.  For now you're best looking at the routes defined in
`api_control_plane.py` and `api_rp_sla.py` to see what's available.

## PyRP Monitor
There is a simple cli tool for interacting with the control plane.
```bash
❯ pipenv run python cli.py 
```
![PyRP Monitor](./demo.gif)

The best "demo" workflow that exists now is: 

POST to `instances/new_from_config` with `filename` query parameter. Get the CP Instance ID.  
GET to `instances` or `instances/{instance_id}` to inspect it as-configured (note any configured static routes, but not details for rp_sla)  
POST to `instances/{instance_id}/rp_sla/evaluate_routes` to trigger rp_sla's evaluation of routes.   
GET to `instances/{instance_id}/routes` to see the current CP RIB (won't include rp_sla yet)  
POST to `instances/{instance_id}/routes/rib/refresh` to trigger the CP to refresh its RIB from the rp_sla service  
GET to `instances/{instance_id}/routes` to see the current CP RIB (should include rp_sla routes now)  
Depending on config, the RIB may hold multiple candidate routes for any given prefix.  
GET to `instances/{instance_id}/best_routes` to see the best route for each prefix in the RIB.


## WSL Networking
in order to give these services direct access to the network, we need to do some extra work in WSL.  This is because WSL 
is NAT'd by default, and thus interferes with several protocols.  To get around this, we need to do the following:
* disable any existing bridge interfaces
  * this means just unchecking the ipv4 stack in the windows network adapter properties
* open hyper-v virtual switch manager, be sure to use 'as Administrator'
  * sometimes it doesn't work, and you just have to close and re-open :shrug:
  * find the switch for WSL and update its settings to bridge with your external network.  
    * probably need to 'allow management operating system to share this network adapter'
    * apply, ok, etc.
* `sudo ip addr flush dev eth0`
* `sudo dhclient`