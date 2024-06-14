# AlloyDB Demo

## Dependencies
- psql client on local machine
- gcloud authentication configured

## Steps to run

Deploy infrastructure with Terraform
> **NOTE:** This can take 10-15 minutes to complete

```bash
cd ./infrastructure
cp terraform.tfvars.sample terraform.tfvars

# Modify at least gcp_project in 'terraform.tfvars' file, can leave others default

terraform init
terraform plan
# Validate resource creation plan looks ok

terraform apply
# Enter 'yes' after checking creation plan looks good.
```

Create the ssh tunnel to the bastion

```bash
gcloud compute ssh alloydb-proxy \
    --tunnel-through-iap \
    --zone=us-central1-a \
    --ssh-flag="-L 5432:localhost:5432 -L 5433:localhost:5433"

# this drops you in the shell of the bastion, but also creates a tunnel on port 5432 from your local machine to bastion
# check that auth-proxy docker container is running
docker ps
docker logs alloydb-auth-proxy
```

On local machine, connect to psql:

```bash
# connect to postgres database with demo user
psql -h 127.0.0.1 -U demo -d postgres

# Validate prompt:
# postgres=>

# create database and connect to it
CREATE DATABASE demo;
\c demo
```

```bash
# Add generated players
export INSTANCE_HOST=127.0.0.1
export DB_USER="demo"
export DB_PASS="<PG_PASSWORD>"
export DB_NAME="demo"
export DB_PORT="5432"



gunicorn --bind :8080 --workers 1 --threads 8 --reload app:app

# Can re-run this file. Each time you run, it creates ~1000 players.
# NOTE: file uses Faker, so duplicates can be generated, and will be errors when inserted into AlloyDB,
#    so actual number will be less than 1000.
python create_players.py
```


Deploy app

```bash
export PROJECT_ID=$(gcloud config get-value project)
gcloud builds submit --tag gcr.io/$PROJECT_ID/alloydb-app --project $PROJECT_ID

gcloud beta run deploy alloydb-app --image gcr.io/$PROJECT_ID/alloydb-app:latest \
    --region="us-central1" \
    --service-account="cloud-run-demo@alloydb-demo-415720.iam.gserviceaccount.com" \
    --min-instances=5 --max-instances=10 \
    --update-env-vars="DB_USER=demo,DB_NAME=demo,DB_PORT=5432" \
    --set-secrets="INSTANCE_HOST=ALLOYDB_PRIMARY_IP:latest,DB_PASS=PG_PASSWORD:latest" \
    --ingress="internal" --network="alloydb-default" --subnet="test-subnetwork" --vpc-egress="private-ranges-only" \
    --no-cpu-throttling --allow-unauthenticated


gcloud secrets versions access latest --secret="PG_PASSWORD"
```


Deploy workload

```bash
locust --web-port 8090 -f load.py

export PROJECT_ID=$(gcloud config get-value project)
export MATCH_APP=$(gcloud run services describe alloydb-app --format "value(status.url)" --region=us-central1)\
export FLASK_SECRET_KEY=b'\x18\x1b4uMJ\xf5)\x92N\xe8\x12\xd9QoM\xb6p\xe6\xf5\x12\xd8\xef~'

# Deploy Locust container
gcloud builds submit --tag gcr.io/$PROJECT_ID/locust-app --project $PROJECT_ID


# Standalone on Cloud Run
gcloud run deploy locust-app --image gcr.io/$PROJECT_ID/locust-app:latest \
    --region="us-central1" \
    --service-account="cloud-run-demo@alloydb-demo-415720.iam.gserviceaccount.com" \
    --min-instances=1 --max-instances=1 \
    --port=8089 \
    --no-cpu-throttling --allow-unauthenticated

# Master/worker on GKE

## Authenticate and validate kubectl
gcloud container clusters get-credentials demo-cluster --region us-central1
kubectl get namespaces

## Deploy locust pods/services
envsubst < kubernetes-config/locust-master-controller.yaml.tpl | kubectl apply -f -
envsubst < kubernetes-config/locust-worker-controller.yaml.tpl | kubectl apply -f -
envsubst < kubernetes-config/locust-master-service.yaml.tpl | kubectl apply -f -

```
