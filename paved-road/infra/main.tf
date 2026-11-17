# Hosting for one tool on the shared platform. The environment, the database
# server and the AI gateway are shared and live in the platform repository;
# a tool brings only what is its own. Every resource carries the tool's tags,
# so the monthly cost report groups by tool and owner without guesswork.

variable "name" { type = string }
variable "owner" { type = string }
variable "tier" { type = number }
variable "data_classes" { type = list(string) }
variable "static" {
  description = "A static site (Static Web Apps, free) or an app with an API (Container Apps, scale to zero)."
  type        = bool
}
variable "platform" {
  description = "Outputs of the platform repository: resource group, environment, database server, gateway URL."
  type = object({
    resource_group_name = string
    location            = string
    environment_id      = string
    postgres_server_id  = string
    ai_gateway_url      = string
  })
}

locals {
  tags = {
    tool         = var.name
    owner        = var.owner
    tier         = tostring(var.tier)
    data_classes = join(" ", var.data_classes)
    managed_by   = "terraform"
  }
}

resource "azurerm_static_web_app" "site" {
  count               = var.static ? 1 : 0
  name                = "swa-${var.name}"
  resource_group_name = var.platform.resource_group_name
  location            = var.platform.location
  sku_tier            = "Free"
  tags                = local.tags
}

resource "azurerm_container_app" "app" {
  count                        = var.static ? 0 : 1
  name                         = "app-${var.name}"
  container_app_environment_id = var.platform.environment_id
  resource_group_name          = var.platform.resource_group_name
  revision_mode                = "Single"
  tags                         = local.tags

  template {
    min_replicas = 0
    max_replicas = var.tier == 1 ? 2 : 1
    container {
      name   = var.name
      image  = "ghcr.io/place-org/${var.name}:latest"
      cpu    = 0.25
      memory = "0.5Gi"
      env {
        name  = "AI_GATEWAY_URL"
        value = var.platform.ai_gateway_url
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
}

# Its own database on the shared server: one server to patch and back up,
# one database per tool so access stays per tool.
resource "azurerm_postgresql_flexible_server_database" "db" {
  count     = contains(var.data_classes, "public") && length(var.data_classes) == 1 ? 0 : 1
  name      = replace(var.name, "-", "_")
  server_id = var.platform.postgres_server_id
}
