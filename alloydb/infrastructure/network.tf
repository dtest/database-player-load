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

# TODO: Change to google vpc module
resource "google_compute_network" "default" {
  name = var.network_name
  auto_create_subnetworks = false
  depends_on = [google_project_service.service_api]
}

resource "google_compute_global_address" "private_ip_alloc" {
  name          = "alloydb-private-ip"
  address_type  = "INTERNAL"
  purpose       = "VPC_PEERING"
  prefix_length = 16
  network       = google_compute_network.default.id
  depends_on = [google_compute_network.default]
}

resource "google_service_networking_connection" "vpc_connection" {
  network                 = google_compute_network.default.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_alloc.name]
  depends_on = [google_project_service.service_api, google_compute_network.default, google_compute_global_address.private_ip_alloc]
}

# resource "google_vpc_access_connector" "connector" {
#   name          = "alloydb-serverless"
#   ip_cidr_range = "10.8.0.0/28"
#   network       = google_compute_network.default.name
#   region        = var.gcp_region
#   min_instances = 2
#   max_instances = 10
#   max_throughput = 1000
# }

resource "google_compute_firewall" "allow_icmp" {
  name    = "allow-icmp"
  network = google_compute_network.default.name

  allow {
    protocol = "icmp"
  }

  source_ranges = ["0.0.0.0/0"]

  depends_on = [google_project_service.service_api, google_compute_network.default]
}

resource "google_compute_firewall" "allow_ssh" {
  name    = "alloy-icmp"
  network = google_compute_network.default.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"]

  depends_on = [google_project_service.service_api, google_compute_network.default]
}

resource "google_compute_subnetwork" "default" {
  name          = "test-subnetwork"
  ip_cidr_range = "10.2.0.0/16"
  region        = "us-central1"
  network       = google_compute_network.default.id
  depends_on = [google_project_service.service_api, google_compute_network.default]
}
