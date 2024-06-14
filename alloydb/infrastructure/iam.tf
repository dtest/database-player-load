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

# Cloud Run IAM account
resource "google_service_account" "run-sa" {
  account_id    = "cloud-run-demo"
  display_name  = "Service account to manage Cloud Run"
  project       = var.gcp_project

  depends_on = [google_project_service.service_api]
}

resource "google_service_account" "gke-sa" {
  account_id    = "gke-cluster-account"
  display_name  = "Service account to manage GKE Autopilot cluster"
  project       = var.gcp_project

  depends_on = [google_project_service.service_api]
}

resource "google_service_account" "alloydb" {
  account_id   = var.alloydb_sa
  display_name = "Custom SA for VM Instance"

  depends_on = [google_project_service.service_api]
}

resource "google_project_iam_member" "project" {
  for_each = toset([
    "roles/iap.tunnelResourceAccessor",
    "roles/compute.instanceAdmin.v1",
    "roles/iam.serviceAccountUser",
    "roles/alloydb.client",
    "roles/serviceusage.serviceUsageConsumer"
  ])
  role  = each.value
  project = var.gcp_project

  member = "serviceAccount:${google_service_account.alloydb.email}"

  depends_on = [google_service_account.alloydb]
}

resource "google_project_iam_member" "run-identity-binding" {
  project       = var.gcp_project
  for_each = toset([
    "roles/run.invoker",
    "roles/alloydb.client",
    "roles/secretmanager.secretAccessor"
  ])
  role   = each.key

  member = "serviceAccount:${google_service_account.run-sa.email}"

  depends_on = [google_service_account.run-sa]
}

# GKE Cluster
resource "google_project_iam_binding" "gke-identity-binding" {
  project       = var.gcp_project
  for_each = toset([
    "roles/container.nodeServiceAccount",
    "roles/run.invoker"
  ])
  role = each.key

  members = [
     "serviceAccount:${google_service_account.gke-sa.email}",
  ]

  depends_on = [google_project_service.service_api, google_service_account.gke-sa]
}
