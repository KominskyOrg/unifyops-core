provider "aws" {
  region = var.region
}

data "aws_availability_zones" "available" {}

locals {
  name   = var.name
  region = var.region

  vpc_cidr = var.vpc_cidr
  azs      = slice(data.aws_availability_zones.available.names, 0, 3)

  tags = var.tags
}

################################################################################
# EC2 Module
################################################################################

# Create placement group if enabled
resource "aws_placement_group" "this" {
  count    = var.create_placement_group ? 1 : 0
  name     = var.placement_group_name != null ? var.placement_group_name : "${var.name}-placement-group"
  strategy = var.placement_group_strategy
}

# Create KMS key if not provided and EBS encryption is enabled
resource "aws_kms_key" "this" {
  count       = var.kms_key_id == null && try(var.ebs_block_device[0].encrypted, false) ? 1 : 0
  description = "KMS key for EBS encryption"
  tags        = local.tags
}

module "ec2_complete" {
  source = "git::https://github.com/terraform-aws-modules/terraform-aws-ec2.git//modules/instance?ref=v5.1.0"

  name = var.name

  ami                    = var.ami_id
  instance_type          = var.instance_type
  availability_zone      = var.availability_zone != null ? var.availability_zone : element(local.azs, 0)
  subnet_id              = var.subnet_id
  vpc_security_group_ids = var.security_group_ids
  placement_group        = var.create_placement_group ? aws_placement_group.this[0].id : null
  create_eip             = var.create_eip
  disable_api_stop       = var.disable_api_stop

  create_iam_instance_profile = var.create_iam_instance_profile
  iam_role_description        = var.iam_role_description
  iam_role_policies           = var.iam_role_policies

  # only one of these can be enabled at a time
  hibernation             = var.hibernation
  enclave_options_enabled = var.enclave_options_enabled

  user_data_base64            = base64encode(var.user_data)
  user_data_replace_on_change = var.user_data_replace_on_change

  cpu_options = {
    core_count       = var.cpu_core_count
    threads_per_core = var.cpu_threads_per_core
  }
  enable_volume_tags = var.enable_volume_tags
  root_block_device  = var.root_block_device

  ebs_block_device = var.ebs_block_device != null ? var.ebs_block_device : [
    {
      device_name = var.default_ebs_device_name
      volume_type = var.default_ebs_volume_type
      volume_size = var.default_ebs_volume_size
      throughput  = var.default_ebs_throughput
      encrypted   = var.default_ebs_encrypted
      kms_key_id  = var.kms_key_id != null ? var.kms_key_id : try(aws_kms_key.this[0].arn, null)
      tags        = var.default_ebs_tags
    }
  ]

  tags = local.tags
}

# Output the instance ID and public IP
output "instance_id" {
  value = module.ec2_complete.id
}

output "public_ip" {
  value = module.ec2_complete.public_ip
}

output "public_dns" {
  value = module.ec2_complete.public_dns
}
