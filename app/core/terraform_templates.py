import os
import shutil
from typing import Dict, List, Optional, Any
import json

from app.logging.context import get_logger

logger = get_logger("terraform.templates", metadata={"component": "terraform.templates"})


class ModuleTemplate:
    """Base class for Terraform module templates"""
    
    def __init__(self, name: str, description: str, category: str, provider: str):
        """
        Initialize a module template
        
        Args:
            name: Template name
            description: Template description
            category: Module category (e.g., compute, storage)
            provider: Cloud provider (e.g., aws, azure)
        """
        self.name = name
        self.description = description
        self.category = category
        self.provider = provider
        
    def get_files(self) -> Dict[str, str]:
        """
        Get template files content
        
        Returns:
            Dict[str, str]: Mapping of filenames to content
        """
        raise NotImplementedError("Subclasses must implement get_files")
        
    def get_variables(self) -> List[Dict[str, Any]]:
        """
        Get template variables
        
        Returns:
            List[Dict[str, Any]]: List of variable definitions
        """
        raise NotImplementedError("Subclasses must implement get_variables")
        
    def get_outputs(self) -> List[Dict[str, Any]]:
        """
        Get template outputs
        
        Returns:
            List[Dict[str, Any]]: List of output definitions
        """
        raise NotImplementedError("Subclasses must implement get_outputs")


class AWSS3BucketTemplate(ModuleTemplate):
    """Template for AWS S3 bucket"""
    
    def __init__(self):
        super().__init__(
            name="s3_bucket",
            description="AWS S3 bucket with configurable properties",
            category="storage",
            provider="aws"
        )
        
    def get_files(self) -> Dict[str, str]:
        return {
            "main.tf": """# AWS S3 bucket with configurable properties
# Provides a secure S3 bucket with encryption, versioning, and access controls

terraform {
  required_version = ">= 1.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0.0"
    }
  }
}

resource "aws_s3_bucket" "this" {
  bucket = var.bucket_name
  
  tags = merge(
    var.tags,
    {
      Name = var.bucket_name
    }
  )
}

resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id
  
  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Suspended"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "this" {
  bucket = aws_s3_bucket.this.id

  block_public_acls       = var.block_public_access
  block_public_policy     = var.block_public_access
  ignore_public_acls      = var.block_public_access
  restrict_public_buckets = var.block_public_access
}
""",
            "variables.tf": """variable "bucket_name" {
  description = "Name of the S3 bucket"
  type        = string
}

variable "enable_versioning" {
  description = "Enable versioning for the bucket"
  type        = bool
  default     = true
}

variable "block_public_access" {
  description = "Block all public access to the bucket"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
""",
            "outputs.tf": """output "bucket_id" {
  description = "The ID of the S3 bucket"
  value       = aws_s3_bucket.this.id
}

output "bucket_arn" {
  description = "The ARN of the S3 bucket"
  value       = aws_s3_bucket.this.arn
}

output "bucket_domain_name" {
  description = "The domain name of the S3 bucket"
  value       = aws_s3_bucket.this.bucket_domain_name
}
""",
            "README.md": """# AWS S3 Bucket Module

This module creates an AWS S3 bucket with the following features:
- Server-side encryption using AES256
- Optional versioning
- Public access blocking
- Customizable tags

## Usage

```hcl
module "s3_bucket" {
  source = "./modules/aws/storage/s3_bucket"
  
  bucket_name       = "my-unique-bucket-name"
  enable_versioning = true
  block_public_access = true
  
  tags = {
    Environment = "Production"
    Owner       = "DevOps Team"
  }
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| bucket_name | Name of the S3 bucket | `string` | n/a | yes |
| enable_versioning | Enable versioning for the bucket | `bool` | `true` | no |
| block_public_access | Block all public access to the bucket | `bool` | `true` | no |
| tags | Tags to apply to all resources | `map(string)` | `{}` | no |

## Outputs

| Name | Description |
|------|-------------|
| bucket_id | The ID of the S3 bucket |
| bucket_arn | The ARN of the S3 bucket |
| bucket_domain_name | The domain name of the S3 bucket |
"""
        }
        
    def get_variables(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "bucket_name",
                "description": "Name of the S3 bucket",
                "type": "string",
                "required": True
            },
            {
                "name": "enable_versioning",
                "description": "Enable versioning for the bucket",
                "type": "bool",
                "default": "true",
                "required": False
            },
            {
                "name": "block_public_access",
                "description": "Block all public access to the bucket",
                "type": "bool",
                "default": "true",
                "required": False
            },
            {
                "name": "tags",
                "description": "Tags to apply to all resources",
                "type": "map(string)",
                "default": "{}",
                "required": False
            }
        ]
        
    def get_outputs(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "bucket_id",
                "description": "The ID of the S3 bucket"
            },
            {
                "name": "bucket_arn",
                "description": "The ARN of the S3 bucket"
            },
            {
                "name": "bucket_domain_name",
                "description": "The domain name of the S3 bucket"
            }
        ]


class AWSLambdaFunctionTemplate(ModuleTemplate):
    """Template for AWS Lambda function"""
    
    def __init__(self):
        super().__init__(
            name="lambda_function",
            description="AWS Lambda function with IAM role and CloudWatch logging",
            category="compute",
            provider="aws"
        )
        
    def get_files(self) -> Dict[str, str]:
        return {
            "main.tf": """# AWS Lambda function with IAM role and CloudWatch logging
# Creates a Lambda function with proper IAM permissions and logging

terraform {
  required_version = ">= 1.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0.0"
    }
  }
}

resource "aws_iam_role" "lambda_role" {
  name = "${var.function_name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = var.log_retention_days
}

resource "aws_lambda_function" "this" {
  function_name    = var.function_name
  role             = aws_iam_role.lambda_role.arn
  handler          = var.handler
  runtime          = var.runtime
  filename         = var.filename
  source_code_hash = filebase64sha256(var.filename)
  timeout          = var.timeout
  memory_size      = var.memory_size
  
  environment {
    variables = var.environment_variables
  }
  
  tags = var.tags
  
  depends_on = [
    aws_cloudwatch_log_group.lambda_logs
  ]
}
""",
            "variables.tf": """variable "function_name" {
  description = "The name of the Lambda function"
  type        = string
}

variable "handler" {
  description = "The Lambda function handler"
  type        = string
}

variable "runtime" {
  description = "The Lambda function runtime"
  type        = string
  default     = "nodejs18.x"
}

variable "filename" {
  description = "Path to the Lambda deployment package"
  type        = string
}

variable "timeout" {
  description = "Function execution timeout in seconds"
  type        = number
  default     = 30
}

variable "memory_size" {
  description = "Function memory allocation in MB"
  type        = number
  default     = 128
}

variable "environment_variables" {
  description = "Environment variables for the Lambda function"
  type        = map(string)
  default     = {}
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 14
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
""",
            "outputs.tf": """output "function_name" {
  description = "The name of the Lambda function"
  value       = aws_lambda_function.this.function_name
}

output "function_arn" {
  description = "The ARN of the Lambda function"
  value       = aws_lambda_function.this.arn
}

output "invoke_arn" {
  description = "The invoke ARN of the Lambda function"
  value       = aws_lambda_function.this.invoke_arn
}

output "role_arn" {
  description = "The ARN of the IAM role created for the Lambda function"
  value       = aws_iam_role.lambda_role.arn
}
""",
            "README.md": """# AWS Lambda Function Module

This module creates an AWS Lambda function with the following features:
- IAM role with basic execution permissions
- CloudWatch log group with configurable retention
- Environment variables support
- Configurable timeout and memory allocation

## Usage

```hcl
module "lambda_function" {
  source = "./modules/aws/compute/lambda_function"
  
  function_name = "my-function"
  handler       = "index.handler"
  runtime       = "nodejs18.x"
  filename      = "./function.zip"
  
  environment_variables = {
    NODE_ENV = "production"
  }
  
  tags = {
    Environment = "Production"
    Owner       = "DevOps Team"
  }
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| function_name | The name of the Lambda function | `string` | n/a | yes |
| handler | The Lambda function handler | `string` | n/a | yes |
| runtime | The Lambda function runtime | `string` | `"nodejs18.x"` | no |
| filename | Path to the Lambda deployment package | `string` | n/a | yes |
| timeout | Function execution timeout in seconds | `number` | `30` | no |
| memory_size | Function memory allocation in MB | `number` | `128` | no |
| environment_variables | Environment variables for the Lambda function | `map(string)` | `{}` | no |
| log_retention_days | CloudWatch log retention in days | `number` | `14` | no |
| tags | Tags to apply to all resources | `map(string)` | `{}` | no |

## Outputs

| Name | Description |
|------|-------------|
| function_name | The name of the Lambda function |
| function_arn | The ARN of the Lambda function |
| invoke_arn | The invoke ARN of the Lambda function |
| role_arn | The ARN of the IAM role created for the Lambda function |
"""
        }
        
    def get_variables(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "function_name",
                "description": "The name of the Lambda function",
                "type": "string",
                "required": True
            },
            {
                "name": "handler",
                "description": "The Lambda function handler",
                "type": "string",
                "required": True
            },
            {
                "name": "runtime",
                "description": "The Lambda function runtime",
                "type": "string",
                "default": "nodejs18.x",
                "required": False
            },
            {
                "name": "filename",
                "description": "Path to the Lambda deployment package",
                "type": "string",
                "required": True
            },
            {
                "name": "timeout",
                "description": "Function execution timeout in seconds",
                "type": "number",
                "default": "30",
                "required": False
            },
            {
                "name": "memory_size",
                "description": "Function memory allocation in MB",
                "type": "number",
                "default": "128",
                "required": False
            },
            {
                "name": "environment_variables",
                "description": "Environment variables for the Lambda function",
                "type": "map(string)",
                "default": "{}",
                "required": False
            },
            {
                "name": "log_retention_days",
                "description": "CloudWatch log retention in days",
                "type": "number",
                "default": "14",
                "required": False
            },
            {
                "name": "tags",
                "description": "Tags to apply to all resources",
                "type": "map(string)",
                "default": "{}",
                "required": False
            }
        ]
        
    def get_outputs(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "function_name",
                "description": "The name of the Lambda function"
            },
            {
                "name": "function_arn",
                "description": "The ARN of the Lambda function"
            },
            {
                "name": "invoke_arn",
                "description": "The invoke ARN of the Lambda function"
            },
            {
                "name": "role_arn",
                "description": "The ARN of the IAM role created for the Lambda function"
            }
        ]


class AzureStorageAccountTemplate(ModuleTemplate):
    """Template for Azure Storage Account"""
    
    def __init__(self):
        super().__init__(
            name="storage_account",
            description="Azure Storage Account with configurable access and encryption",
            category="storage",
            provider="azure"
        )
        
    def get_files(self) -> Dict[str, str]:
        return {
            "main.tf": """# Azure Storage Account with configurable access and encryption
# Creates a secure storage account with proper access controls

terraform {
  required_version = ">= 1.0.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.0.0"
    }
  }
}

resource "azurerm_storage_account" "this" {
  name                     = var.storage_account_name
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = var.account_tier
  account_replication_type = var.replication_type
  
  min_tls_version                 = "TLS1_2"
  enable_https_traffic_only       = true
  allow_nested_items_to_be_public = var.allow_public_access
  
  blob_properties {
    delete_retention_policy {
      days = var.blob_retention_days
    }
  }
  
  tags = var.tags
}

resource "azurerm_storage_account_network_rules" "this" {
  count = var.enable_network_rules ? 1 : 0
  
  storage_account_id = azurerm_storage_account.this.id
  default_action     = "Deny"
  bypass             = ["AzureServices"]
  ip_rules           = var.allowed_ip_addresses
}
""",
            "variables.tf": """variable "storage_account_name" {
  description = "Name of the storage account"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region for the storage account"
  type        = string
}

variable "account_tier" {
  description = "Storage account tier (Standard or Premium)"
  type        = string
  default     = "Standard"
}

variable "replication_type" {
  description = "Storage account replication type (LRS, GRS, RAGRS, ZRS)"
  type        = string
  default     = "LRS"
}

variable "allow_public_access" {
  description = "Allow public access to storage objects"
  type        = bool
  default     = false
}

variable "blob_retention_days" {
  description = "Blob retention policy in days"
  type        = number
  default     = 7
}

variable "enable_network_rules" {
  description = "Enable network rules to restrict access"
  type        = bool
  default     = false
}

variable "allowed_ip_addresses" {
  description = "List of IP addresses to allow access"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
""",
            "outputs.tf": """output "storage_account_id" {
  description = "The ID of the storage account"
  value       = azurerm_storage_account.this.id
}

output "storage_account_name" {
  description = "The name of the storage account"
  value       = azurerm_storage_account.this.name
}

output "primary_blob_endpoint" {
  description = "The primary blob endpoint URL"
  value       = azurerm_storage_account.this.primary_blob_endpoint
}

output "primary_access_key" {
  description = "The primary access key for the storage account"
  value       = azurerm_storage_account.this.primary_access_key
  sensitive   = true
}
""",
            "README.md": """# Azure Storage Account Module

This module creates an Azure Storage Account with the following features:
- TLS 1.2 enforcement
- HTTPS traffic only
- Optional public access control
- Optional network rules for IP restriction
- Blob retention policy

## Usage

```hcl
module "storage_account" {
  source = "./modules/azure/storage/storage_account"
  
  storage_account_name = "mystorageaccount"
  resource_group_name  = "my-resource-group"
  location             = "eastus"
  
  enable_network_rules  = true
  allowed_ip_addresses  = ["203.0.113.0/24"]
  
  tags = {
    Environment = "Production"
    Owner       = "DevOps Team"
  }
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| storage_account_name | Name of the storage account | `string` | n/a | yes |
| resource_group_name | Name of the resource group | `string` | n/a | yes |
| location | Azure region for the storage account | `string` | n/a | yes |
| account_tier | Storage account tier (Standard or Premium) | `string` | `"Standard"` | no |
| replication_type | Storage account replication type (LRS, GRS, RAGRS, ZRS) | `string` | `"LRS"` | no |
| allow_public_access | Allow public access to storage objects | `bool` | `false` | no |
| blob_retention_days | Blob retention policy in days | `number` | `7` | no |
| enable_network_rules | Enable network rules to restrict access | `bool` | `false` | no |
| allowed_ip_addresses | List of IP addresses to allow access | `list(string)` | `[]` | no |
| tags | Tags to apply to all resources | `map(string)` | `{}` | no |

## Outputs

| Name | Description |
|------|-------------|
| storage_account_id | The ID of the storage account |
| storage_account_name | The name of the storage account |
| primary_blob_endpoint | The primary blob endpoint URL |
| primary_access_key | The primary access key for the storage account (sensitive) |
"""
        }
        
    def get_variables(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "storage_account_name",
                "description": "Name of the storage account",
                "type": "string",
                "required": True
            },
            {
                "name": "resource_group_name",
                "description": "Name of the resource group",
                "type": "string", 
                "required": True
            },
            {
                "name": "location",
                "description": "Azure region for the storage account",
                "type": "string",
                "required": True
            },
            {
                "name": "account_tier",
                "description": "Storage account tier (Standard or Premium)",
                "type": "string",
                "default": "Standard",
                "required": False
            },
            {
                "name": "replication_type",
                "description": "Storage account replication type (LRS, GRS, RAGRS, ZRS)",
                "type": "string",
                "default": "LRS",
                "required": False
            },
            {
                "name": "tags",
                "description": "Tags to apply to all resources",
                "type": "map(string)",
                "default": "{}",
                "required": False
            }
        ]
        
    def get_outputs(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "storage_account_id",
                "description": "The ID of the storage account"
            },
            {
                "name": "storage_account_name",
                "description": "The name of the storage account"
            },
            {
                "name": "primary_blob_endpoint",
                "description": "The primary blob endpoint URL"
            },
            {
                "name": "primary_access_key",
                "description": "The primary access key for the storage account",
                "sensitive": True
            }
        ]


class TemplateManager:
    """Manages Terraform module templates"""
    
    def __init__(self, terraform_dir: str):
        """
        Initialize the template manager
        
        Args:
            terraform_dir: Base directory containing Terraform modules
        """
        self.terraform_dir = terraform_dir
        self.logger = get_logger("terraform.templates")
        
        # Register available templates
        self.templates = {
            "aws/storage/s3_bucket": AWSS3BucketTemplate(),
            "aws/compute/lambda_function": AWSLambdaFunctionTemplate(),
            "azure/storage/storage_account": AzureStorageAccountTemplate(),
        }
        
    def get_available_templates(self) -> List[Dict[str, Any]]:
        """
        Get a list of available templates
        
        Returns:
            List[Dict[str, Any]]: List of template metadata
        """
        return [
            {
                "id": template_id,
                "name": template.name,
                "description": template.description,
                "category": template.category,
                "provider": template.provider
            }
            for template_id, template in self.templates.items()
        ]
    
    def get_template_details(self, template_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a template
        
        Args:
            template_id: Template identifier
            
        Returns:
            Dict[str, Any]: Template details
        """
        if template_id not in self.templates:
            raise ValueError(f"Template {template_id} not found")
            
        template = self.templates[template_id]
        return {
            "id": template_id,
            "name": template.name,
            "description": template.description,
            "category": template.category,
            "provider": template.provider,
            "variables": template.get_variables(),
            "outputs": template.get_outputs()
        }
    
    def create_module_from_template(
        self, 
        template_id: str, 
        target_path: str,
        variables: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Create a new module from a template
        
        Args:
            template_id: Template identifier
            target_path: Target path for the new module (relative to terraform_dir)
            variables: Template variables to replace
            
        Returns:
            str: Path to the created module
        """
        if template_id not in self.templates:
            raise ValueError(f"Template {template_id} not found")
            
        template = self.templates[template_id]
        
        # Create the target directory
        target_dir = os.path.join(self.terraform_dir, target_path)
        if os.path.exists(target_dir):
            raise ValueError(f"Target directory {target_path} already exists")
            
        os.makedirs(target_dir, exist_ok=True)
        
        # Get template files
        files = template.get_files()
        
        # Create each file
        for filename, content in files.items():
            # Simple variable replacement
            if variables:
                for var_name, var_value in variables.items():
                    content = content.replace(f"${{var.{var_name}}}", var_value)
                    
            with open(os.path.join(target_dir, filename), "w") as f:
                f.write(content)
        
        self.logger.info(f"Created module from template {template_id} at {target_path}")
        return target_path 