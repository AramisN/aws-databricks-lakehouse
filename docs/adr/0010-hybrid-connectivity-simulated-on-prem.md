# ADR-0010: A simulated on-prem VPC reached over a Site-to-Site VPN

Status: Proposed
Date: 2026-09-14

## What I'm deciding

Where the OLTP database lives once it stops being a container on my laptop, and
how AWS reaches it. Phase 4 moves the ride-hailing Postgres behind a network
boundary so DMS has to cross something real to read it.

## The call

I build a second VPC in the same account that stands in for a company
datacenter. It holds two things, a Postgres server and a small EC2 instance
running libreswan, the open-source IPsec software that plays the part of the
firewall a real site would have. That instance carries an Elastic IP and acts as
the customer gateway. The lakehouse VPC from Phase 1 gets a virtual private
gateway, and an AWS Site-to-Site VPN connects the two. DMS runs in a private
subnet on the lakehouse side and reads Postgres across the tunnel.

Both VPCs are mine, so this is AWS pretending to be a datacenter. The pretending
stops at the edge though. The IPsec negotiation is real, the routing is real,
the security groups are real, and so is every way it can fail. That is the part
I want to practice.

Routing starts static. I set the on-prem address range on the VPN connection and
let route propagation put it into the private route table. The alternative is
BGP, the routing protocol where the two ends announce their ranges to each other
and reroute on their own when a tunnel drops. That is what a real site runs, and
I'd rather get traffic flowing first and add it after than debug encryption and
routing at the same time.

I'm using a virtual private gateway rather than a Transit Gateway. A TGW is the
right answer once there are several VPCs or several sites to join, and it bills
per attachment per hour on top of the VPN itself. There is one VPC and one site
here, so the VGW does the same job for nothing.

## Alternatives I turned down

**My laptop as the on-prem side.** This was the first idea and it doesn't work.
A Site-to-Site VPN needs a customer gateway with a fixed public IP that can
terminate IPsec, and a home connection gives me neither. The address changes and
it sits behind NAT. Depending on the ISP it may be behind carrier NAT as well,
which breaks IPsec outright. Worse for a public repo, none of it can go in
Terraform. Nobody reading this could reproduce it.

**No VPN at all, with Postgres in the lakehouse VPC.** Cheaper, simpler, and I'd
learn nothing. Half the reason this phase exists is that hybrid connectivity is
where real migrations spend their time.

**VPC peering between the two VPCs.** This is the first thing most people would
reach for and it's the worst fit. Peering hands you a network path and nothing
else, so there is no IPsec to negotiate, no customer gateway, no routes to
agree, no reduced packet size to trip over, and no tunnel that can drop. It also
isn't a thing that exists in the scenario I'm imitating, since peering only ever
joins two VPCs and never a VPC to a company datacenter. It removes the subject
of the phase rather than solving it.

**A virtual firewall appliance instead of libreswan.** VyOS, pfSense or OPNsense
are open-source router and firewall operating systems that run as a virtual
machine, and FortiGate is the commercial equivalent. Any of them would bundle
IPsec and routing into one box, which is closer to what actually sits in a
datacenter rack. That would save running two pieces of software to imitate one
appliance. Two things pushed me off it. The commercial images bill by the hour
or need a licence, and the free builds usually mean building the image myself
first. The bigger reason is that libreswan's whole configuration is a text file
that gets committed, so anyone reading this repo sees exactly what was set. An
appliance keeps its configuration inside itself, usually clicked into a web
interface. The repo would show nothing. For a repo whose point is being
readable, that beats the extra realism.

**strongSwan instead of libreswan.** Same job, same architecture, different
implementation. Nothing about the design changes either way, so this came down
to picking one.

**BGP from the start rather than later.** libreswan only builds the tunnel, so
BGP would mean running FRR, an open-source routing suite, alongside it. That is
more moving parts to get wrong on the first attempt. It stays on the list as the
next thing to add once the tunnel is carrying traffic.

## Hybrid DNS

DMS will point at an IP address first. Once replication works, I add a Route 53
Resolver outbound endpoint and a forwarding rule so the AWS side resolves the
Postgres hostname from a DNS server running on the on-prem instance. Only the
outbound direction is needed, since nothing on the on-prem side has to resolve
AWS names.

That goes in its own Terraform stack and its own session, deliberately. A name
that won't resolve and a tunnel that won't come up produce the same DMS error,
and I don't want to guess which one I'm looking at.

## Cost

The VPN connection is about $0.05 an hour whenever it exists, whether traffic
flows or not. That's roughly $36 a month if I forget it. The on-prem instance
and its Elastic IP add a couple of cents an hour. A Resolver endpoint is $0.125
per network interface per hour with a minimum of two interfaces, so $0.25 an
hour, about $6 a day, or near $180 a month left running. That last one is the
dangerous number in this phase and the reason DNS lives in a separate stack that
is easy to destroy on its own.

A working session with everything up is a couple of dollars. A forgotten stack
trips the 20 euro alarm in under two days. So this phase keeps to teardown-first
like the streaming one, with its own state file so destroying it can't touch the
foundation.

Sizing is not free either. The scale runs later in this phase put tens of
millions of rows through Postgres, which needs a real disk and more than a
t3.micro to generate in reasonable time. That instance gets sized for the run
and destroyed after, rather than left at a default that quietly fails at volume.

## Security and governance

No keys in the repo, same as everywhere else. The IPsec pre-shared key is
generated outside git and passed in, never committed. Postgres listens only to
the on-prem VPC and accepts connections from the lakehouse range across the
tunnel, with no public port open to the internet on either side. The DMS
instance sits in private subnets with no public address, and reaches S3 through
the gateway endpoint that already exists from Phase 1. So its traffic to the
lake never leaves the AWS network.

Everything is tagged like the rest, and both stacks encrypt at rest with the
existing KMS keys.

## What I'm giving up

Both ends being in AWS means the tunnel runs over the AWS backbone instead of
the open internet, so it will behave better than a real site-to-site link. I
won't see the packet loss or the jitter a real datacenter link has.

A single customer gateway means only one of the two tunnels AWS gives me gets
used. Real setups run both for failover, and I'm not building the redundancy
just to watch it sit idle.

Static routes instead of BGP means I skip route advertisement and failover
behaviour, which is a real gap. I'd rather note it honestly than claim it.

## What would flip this

- Getting hold of a genuinely separate network, a static IP at home or a second
  cloud account, which would make the on-prem side less of a simulation.
- Needing a Direct Connect story instead, though at this budget that isn't
  happening.
- The tunnel turning into a time sink with nothing to learn from it. If a week
  goes by fighting IPsec without progress, I fall back to Postgres on EC2 in the
  lakehouse VPC, record that I did, and move on to the CDC work that actually
  feeds the lake.
