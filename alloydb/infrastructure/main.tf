// Copyright 2024 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//    https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0.0"
    }
  }

  required_version = ">= 1.7"
}

provider "google" {
  project = var.gcp_project
}

resource "google_project_service" "service_api" {
  for_each = toset(var.gcp_project_services)
  service  = each.value

  disable_on_destroy = false
}

data "google_project" "project" {
  depends_on = [google_project_service.service_api]
}

# data "google_client_config" "provider" {}
