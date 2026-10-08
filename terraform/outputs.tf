output "s3_bucket_name" {
  description = "Name of document storage S3 bucket"
  value       = aws_s3_bucket.documents.id
}

output "rds_endpoint" {
  description = "Connection endpoint for PostgreSQL RDS"
  value       = aws_db_instance.postgres.endpoint
}

output "elasticache_configuration_endpoint" {
  description = "Redis configuration endpoint"
  value       = aws_elasticache_replication_group.redis.configuration_endpoint_address
}

output "msk_bootstrap_brokers_tls" {
  description = "TLS connection string for Kafka MSK bootstrap brokers"
  value       = aws_msk_cluster.kafka.bootstrap_brokers_tls
}
