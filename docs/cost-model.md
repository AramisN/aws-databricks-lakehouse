# Cost model

Two numbers for the same architecture. What it would cost carrying real traffic,
and what I actually spent testing it. They are far apart on purpose.

## Assumed production volume

- 200,000 trips a day
- 15 minute average trip, one GPS ping every 5 seconds, so about 180 events per
  trip and 36 million events a day
- roughly 420 events a second average, 1,250 a second at peak
- about 1 million OLTP row changes a day across the six tables
- eu-central-1, on demand, no committed spend discount

Change the trip count and everything below moves with it.

## Production, per month

| Item | Sizing | USD |
|---|---|---|
| Kinesis Data Streams | 4 shards, driven by the 1,250 records a second peak, not by bytes | 45 |
| Kinesis PUT payload units | 1.1 billion units | 15 |
| Firehose | 270 GB landed | 8 |
| S3 storage | about 3 TB across raw, bronze, silver, gold after lifecycle rules | 75 |
| S3 requests | small-file behaviour is the variable here | 10 |
| DMS replication instance | dms.t3.medium, sized for 1M changes a day | 65 |
| Site-to-Site VPN | one connection, always up | 36 |
| EC2 and other | NAT, endpoints, monitoring | 40 |
| **AWS subtotal** | | **294** |
| Databricks DBUs | streaming job running continuously plus hourly merges and daily gold, about 5 DBU an hour on Premium jobs compute | 730 |
| EC2 under Databricks | the cluster itself, billed separately from DBUs | 550 |
| **Databricks subtotal** | | **1,280** |
| **Total** | | **~1,575** |

Databricks is 80 percent of it, and inside Databricks the continuously running
streaming job is most of that. Anything that cuts cost meaningfully cuts there,
not in the AWS lines.

At this volume a Direct Connect would replace the VPN and cost more, but it buys
predictable latency the VPN does not.

## Lab, what I actually spend

Nothing runs between sessions. Every stack is destroyed after use.

| Item | Per session | Note |
|---|---|---|
| Kinesis | 0.06 | 2 shards, 2 hours |
| VPN | 0.20 | 4 hours |
| EC2, on-prem side | 0.15 | one instance plus an Elastic IP |
| DMS | 0.08 | dms.t3.micro |
| Route 53 Resolver | 0.75 | only in the DNS session |
| S3 | under 1 | single-digit GB, deleted after |
| **Session total** | **under 3** | |

Standing cost between sessions is the S3 buckets and the KMS keys, under a
dollar a month.

## Where the lab differs from the sizing above

| Decision | Production | Lab | Why |
|---|---|---|---|
| Kinesis shards | 4 | 2 | 2 shards can be pushed into their limit cheaply, which is the point |
| DMS instance | t3.medium | t3.micro | fine below 10 million rows |
| VPN routing | BGP, both tunnels | static, one tunnel | failover is not what is being tested |
| Databricks | always on | not built yet | phase 5 |
| Raw retention | short, by policy | deleted with the stack | |

## Confidence

AWS storage, VPN and Kinesis shard rates come from AWS pricing pages, around 90
percent. DMS instance rates and Kinesis payload unit pricing, around 70 percent,
both taken from us-east-1 and adjusted. Databricks, around 60 percent. DBU rates
depend on tier and instance family, list rates for jobs compute on Premium sit
near $0.20 per DBU, and the EC2 underneath commonly lands between half and all
of the DBU charge again. The Databricks line is the one to check against the
calculator before quoting it anywhere.

The total is a list-price figure with no committed spend discount. A real
platform at this volume would negotiate, and spot instances under the Databricks
workers would cut the EC2 line further.
