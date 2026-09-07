# The VPC and private subnets this environment runs in.
module "network" {
  source = "../modules/network"

  name_prefix = "adl-dev"
  region      = "eu-central-1"
}
