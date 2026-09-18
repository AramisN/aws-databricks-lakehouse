output "stream_name" {
  description = "Name of the Kinesis stream the producer sends trip events to."
  value       = aws_kinesis_stream.trip_events.name
}

output "stream_arn" {
  description = "ARN of the Kinesis stream."
  value       = aws_kinesis_stream.trip_events.arn
}

output "region" {
  description = "AWS region the stream runs in, so the producer knows where to send."
  value       = data.aws_region.current.region
}

output "producer_role_arn" {
  description = "ARN of the scoped producer role. Not assumed by the generator during the exercise, it documents the production pattern."
  value       = aws_iam_role.producer.arn
}
