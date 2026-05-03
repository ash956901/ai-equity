provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = "ai-equity"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
