terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = "GraphIntel"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# -------------------------------------------------------------
# 1. S3 Bucket for Raw Documents & Extracted Evidence
# -------------------------------------------------------------
resource "aws_s3_bucket" "documents" {
  bucket        = "graphintel-documents-${var.environment}-${var.aws_region}"
  force_destroy = false
}

resource "aws_s3_bucket_versioning" "documents_versioning" {
  bucket = aws_s3_bucket.documents.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents_crypto" {
  bucket = aws_s3_bucket.documents.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# -------------------------------------------------------------
# 2. Managed PostgreSQL (AWS RDS Multi-AZ)
# -------------------------------------------------------------
resource "aws_db_instance" "postgres" {
  identifier            = "graphintel-postgres-${var.environment}"
  engine                = "postgres"
  engine_version        = "16.2"
  instance_class        = var.db_instance_class
  allocated_storage     = 100
  max_allocated_storage = 1000
  storage_type          = "gp3"
  multi_az              = var.environment == "production" ? true : false
  db_name               = var.db_name
  username              = "graphintel_admin"
  manage_master_user_password = true

  backup_retention_period   = 30
  backup_window             = "03:00-04:00"
  maintenance_window        = "Sun:04:30-Sun:05:30"
  auto_minor_version_upgrade = true
  deletion_protection       = var.environment == "production" ? true : false
  skip_final_snapshot       = var.environment == "production" ? false : true
  final_snapshot_identifier = "graphintel-postgres-${var.environment}-final"

  publicly_accessible = false
}

# -------------------------------------------------------------
# 3. Managed Redis (AWS ElastiCache Cluster)
# -------------------------------------------------------------
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id          = "graphintel-redis-${var.environment}"
  description                   = "GraphIntel high-availability Redis cache & rate limiter"
  node_type                     = var.redis_node_type
  port                          = 6379
  parameter_group_name          = "default.redis7.cluster.on"
  automatic_failover_enabled    = true
  multi_az_enabled              = true
  num_node_groups               = 2
  replicas_per_node_group       = 1
  at_rest_encryption_enabled    = true
  transit_encryption_enabled   = true
  auto_minor_version_upgrade    = true
}

# -------------------------------------------------------------
# 4. Managed Kafka (AWS MSK Cluster) for High-Throughput Ingestion
# -------------------------------------------------------------
resource "aws_msk_cluster" "kafka" {
  cluster_name           = "graphintel-msk-${var.environment}"
  kafka_version          = "3.5.1"
  number_of_broker_nodes = 3

  broker_node_group_info {
    instance_type = "kafka.m5.large"
    client_subnets = ["subnet-01234567", "subnet-01234568", "subnet-01234569"]
    storage_info {
      ebs_storage_info {
        volume_size = 250
      }
    }
    security_groups = []
  }

  encryption_info {
    encryption_in_transit {
      client_broker = "TLS"
      in_cluster    = true
    }
  }
}
