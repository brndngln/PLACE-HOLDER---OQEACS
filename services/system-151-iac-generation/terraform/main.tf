terraform {
  required_version = ">= 1.7.0"
}

provider "null" {}

resource "null_resource" "iac_generation_scaffold" {}
