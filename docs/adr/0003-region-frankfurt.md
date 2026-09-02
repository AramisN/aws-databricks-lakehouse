# ADR-0003: Frankfurt (eu-central-1) as the region

Status: Proposed
Date: 2026-09-01

## What I'm deciding

Which AWS region the whole platform runs in. One region, single account, dev only.

## The call

eu-central-1, Frankfurt.

## Why

The data model carries EU personal data, so keeping everything in an EU region is the cleanest way to hold the GDPR line on data residency. Frankfurt is the primary EU region, it has every service this project needs, and latency from here is fine. Picking one region up front keeps state and networking and buckets from sprawling across regions. That sprawl is a common mess in personal accounts, and it's easy to avoid by deciding now.

## What I'm giving up

No multi-region, so no cross-region disaster-recovery story. Fine for a dev portfolio, and a later ADR can add DR if a real case shows up. A few services are cheaper in us-east-1, but residency and simplicity win here.

## What would flip this

- Target employers are US-based and residency doesn't matter. Then us-east-1 for the widest service set and the lowest price.
- A real disaster-recovery requirement appears. Add a second region and revisit.
