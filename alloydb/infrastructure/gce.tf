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

module "gce-container" {
  source = "terraform-google-modules/container-vm/google"
  version = "~> 3.1"

  container = {
    image="gcr.io/alloydb-connectors/alloydb-auth-proxy:latest"
    port="127.0.0.1:5432:5432,127.0.0.1:5433:5433"
    name="alloydb-auth-proxy"
    args = [
      "--address",
      "0.0.0.0",
      "--port",
      "5432",
      "${module.alloy-db.primary_instance_id}",
      # "${module.alloy-db.read_instance_ids[0]}",
    ]
  }

  restart_policy = "Always"

  depends_on = [google_project_service.service_api]
}

# TODO: Don't allow external IP, and add Cloud NAT
resource "google_compute_instance" "alloydb_proxy" {
  name         = "alloydb-proxy"
  machine_type = "n1-standard-1"
  zone         = "us-central1-a"

  boot_disk {
    initialize_params {
      image = module.gce-container.source_image
    }
  }

  network_interface {
    network = google_compute_network.default.name
    subnetwork = google_compute_subnetwork.default.name

    access_config {
      // Ephemeral public IP
    }
  }

  metadata = {
    gce-container-declaration = module.gce-container.metadata_value
  }

  labels = {
    container-vm = module.gce-container.vm_container_label
  }


  service_account {
    # Google recommends custom service accounts that have cloud-platform scope and permissions granted via IAM Roles.
    email  = google_service_account.alloydb.email
    scopes = ["cloud-platform"]
  }

  depends_on = [google_project_service.service_api, google_compute_network.default,
                module.gce-container, module.alloy-db, google_service_account.alloydb]
}
