# Architecture


## Description
So far, PyRP is built around independent services. Currently, communication between services is via FastAPI REST APIs.  This will
likely change to a message bus in the future.  The intent is that the Control Plane itself is one service, while each
protocol implementation will be a separate service.  The Control Plane service will be responsible for ingestion of config
and coordinating the exchange of routes between the various protocol services.

## Redistribution
Redistribution working like so, configured on a per-protocol basis:  

*RI: Redistribute-In*  
*RO: Redistribute-Out*
```mermaid
graph TD
    A[Control Plane]
    B[RP-SLA]
    A -->|RI| B
    B -->|RO| A
    
    C[RIPv1]
    A -->|RI| C
    C -->|RO| A
    
    D[RIPv2]
    A -->|RI| D
    D -->|RO| A
    
    E[BGP]
    E -->|RO| A
    A -->|RI| E
```

That is the flow between processes.  Within these processes, typically we have several core components:
* A central "instance" class that manages the state for this instance.  It creates and manages all required RIBs,
    and is responsible for coordinating the exchange of routes between them and the outside world, etc.
* One or more RIBs, which are responsible for storing routes of various types.  Each RIB stores route entries of a specific
    type, with the protocol instance being responsible for any needed translation
  * RIB entries, which are the actual routes.  These are stored in the RIBs.
* An API interface responsible for exposing the instance to the outside world.  Currently, these are all FastAPI apps, .
    but this will likely change to a message bus in the future.
  * All interaction and configuration is through this interface


### graph of service components
*Control Plane Service*
```mermaid
graph LR
    U[User]
    CP-I[Control Plane Instance]
    CP-API[Control Plane API]
    SLA-API[RP-SLA API, etc]
    CP-RIB[Control Plane Routing Table]
    CP-RE[Control Plane Routing Table Entry]
    U -->|REST| CP-API
    CP-API -->|instantiates| CP-I
    CP-I -->|REST| SLA-API
    CP-I -->|instantiates| CP-RIB 
    CP-RIB -->|stores| CP-RE
```

Services for RP-SLA, RIPv1, etc follow a similar model

## Instances
All services are currently built around the assumption of multiple instances for a given service.  There might be real 
need for this in the future, but currently it's simply a clean way to manage state especially in testing where a given component
might be edited and restarted at any point.  The assumption is that after any work you tell the CP to build a new instance from config,
which triggers the rest. Old, existing state remains, but doesn't get in the way.

## Config handling

Notably config is not passed from the control plane to other services directly.  Instead, each instance (including the control plane itself)
ingests its own config from a given file.  The format of the config file is TOML.  When the CP is instantiating other services, it passes
the path to the config file to the service, which then ingests its own config from that file.  Currently we keep all config in a single TOML file, but 
there's no reason we couldn't split it up into multiple files in the future.

The exception to this is the config in `config.toml` in the project root.  This is the config that specifies which ports each service should
listen on, and is currently statically configured.  Any change to these would need to also be reflected in eventual docker config, etc. 


## Protocol Service Details
as an example, take the RP-SLA protocol:  
 *RP-SLA Service*
```mermaid
graph LR
    CP-I[Control Plane Instance]
    SLA-I[RP-SLA Instance]
    SLA-API[RP-SLA API]
    SLA-RIB[RP-SLA RIB]
    SLA-RE[RP-SLA RIB Entry]
    CP-I -->|REST| SLA-API
    SLA-API -->|instantiates| SLA-I
    SLA-I -->|Instantiates| SLA-RIB
    SLA-RIB -->|stores| SLA-RE
```

The API is primarily meant to be used by the control plane, but could be used by users directly, especially for testing.
Low level operations like "importing a single route" can be exposed, but they should be used only for testing.
Instead, higher level operations like "redistribute-in" should be used, which would apply all the necessary business logic 
of the protocol itself (e.g. any necessary translations, filtering, etc).

Similarly, RIBs themselves typically have simple fundamental operations like add/remove import/export, etc.  But the protocol instance 
itself should use higher level operations like "redistribute-in", "redistribute-out", etc to apply the necessary business logic.

## Adding a new operation
When adding a new operation, (e.g. "show routes in the rp-sla rib"), these are the general steps:
```mermaid
graph TD
    subgraph one [Control Plane Service]
    U[User]
    CP-API[Control Plane API]
    CP-I[Control Plane Instance]
    SLA-API-Client[RP-SLA API Client]
    end
    subgraph two [RP-SLA Service]
    SLA-API[RP-SLA API]
    SLA-I[RP-SLA Instance]
    SLA-RIB[RP-SLA RIB]
    SLA-RE[RP-SLA RIB Entry]
    end
    U -.->|REST| CP-API
    CP-API -.->|instantiates| CP-I
    CP-I -.->|calls| SLA-API-Client
    SLA-API-Client -.->|REST| SLA-API
    SLA-API -.->|instantiates| SLA-I
    SLA-I -.->|Instantiates| SLA-RIB
    SLA-RIB -.->|stores| SLA-RE
    EDIT --> |add endpoint|CP-API
    EDIT --> |add method|CP-I
    EDIT --> |add method|SLA-API-Client
    EDIT --> |add endpoint|SLA-API
    EDIT --> |add method|SLA-I
    EDIT --> |add method|SLA-RIB
```
