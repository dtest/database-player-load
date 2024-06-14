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

resource "random_password" "pg_password" {
  length           = 16
  special          = true
  override_special = "&*-_=+[]{}<>"
}

resource "google_secret_manager_secret" "pg-password-secret" {
  secret_id = "PG_PASSWORD"

  replication {
    auto {}
  }

  depends_on = [google_project_service.service_api]
}

resource "google_secret_manager_secret_version" "version-basic" {
  secret  = google_secret_manager_secret.pg-password-secret.id
  secret_data = random_password.pg_password.result

  depends_on = [google_secret_manager_secret.pg-password-secret]
}

module "alloy-db" {
  source               = "GoogleCloudPlatform/alloy-db/google"
  version              = "~> 2.0"
  cluster_id           = "demo"
  cluster_location     = var.gcp_region
  project_id           = var.gcp_project
  database_version     = "POSTGRES_15"
  cluster_labels       = {}
  cluster_display_name = ""
  cluster_initial_user = {
    user     = "demo",
    password = random_password.pg_password.result
  }
  network_self_link = "projects/${var.gcp_project}/global/networks/${google_compute_network.default.name}"

  automated_backup_policy = {
    location      = var.gcp_region
    backup_window = "1800s",
    enabled       = true,
    weekly_schedule = {
      days_of_week = ["FRIDAY"],
      start_times  = ["2:00:00:00", ]
    }
    quantity_based_retention_count = 1,
    time_based_retention_count     = null,
    labels = {
      test = "alloydb-cluster"
    },
  }

  primary_instance = {
    instance_id       = "primary-instance"
    instance_type     = "PRIMARY"
    machine_cpu_count = 8
    database_flags = {
      "google_columnar_engine.enabled" = "on",
      "google_columnar_engine.enable_auto_columnarization" = "on"
    }
    display_name = "alloydb-primary-instance",
  }

  read_pool_instance = [
    # {
    #   instance_id       = "read-instance-1",
    #   display_name      = "read-instance-1",
    #   instance_type     = "READ_POOL",
    #   node_count        = 1,
    #   database_flags    = {
    #     "google_columnar_engine.enabled" = "on",
    #     "google_columnar_engine.enable_auto_columnarization" = "off",
    #     "google_columnar_engine.relations" = "'demo.public.matches(player1_id, player2_id, match_result)'"
    #     # "google_columnar_engine.scan_mode" = 2
    #   },
    #   machine_cpu_count = 2,
    # }
  ]
  depends_on = [google_project_service.service_api, google_compute_network.default, google_compute_global_address.private_ip_alloc,
                google_service_networking_connection.vpc_connection, random_password.pg_password]
}

resource "google_secret_manager_secret" "alloydb-primary-secret" {
  secret_id = "ALLOYDB_PRIMARY_IP"

  replication {
    auto {}
  }

  depends_on = [google_project_service.service_api, module.alloy-db]
}

resource "google_secret_manager_secret_version" "alloydb-primary-secret-version" {
  secret  = google_secret_manager_secret.alloydb-primary-secret.id
  secret_data = module.alloy-db.primary_instance.ip_address

  depends_on = [google_secret_manager_secret.alloydb-primary-secret]
}
