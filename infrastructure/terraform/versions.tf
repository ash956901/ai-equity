terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Remote state. Create the bucket + DynamoDB lock table out-of-band first
  # (see README.md) — Terraform won't bootstrap its own state backend.
  backend "s3" {
    # bucket         = "ai-equity-tfstate"
    # key            = "prod/terraform.tfstate"
    # region         = "ap-south-1"
    # dynamodb_table = "ai-equity-tflock"
    # encrypt        = true
  }
}
