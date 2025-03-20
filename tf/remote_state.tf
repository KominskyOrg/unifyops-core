# Remote state configuration to access infrastructure resources
data "terraform_remote_state" "infra" {
  backend = "s3"

  config = {
    bucket = "${var.org}-tfstate-bucket"
    key    = "infra/terraform_state.tfstate"
    region = var.region
  }
}
