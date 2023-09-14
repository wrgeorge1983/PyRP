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
Notably the rp_sla service requires root access.  This is required to send and receive ICMP packets.
