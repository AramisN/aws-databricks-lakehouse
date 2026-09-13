# Provisioned mode means the shard count is the throughput ceiling, on
# purpose (ADR-0009). Left as a variable rather than hardcoded, because
# going from 1 shard to 2 and watching the resharding is part of the
# exercise.
variable "shard_count" {
  description = "Number of shards on the trip_events stream."
  type        = number
  default     = 2
}
