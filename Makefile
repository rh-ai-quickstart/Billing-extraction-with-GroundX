# Billing extraction with GroundX by EyeLevel - Makefile
# This Makefile simplifies deployment and management of the billing extraction environment

# Configuration Variables
NAMESPACE ?= eyelevel
RELEASE_NAME ?= groundx
CHART_DIR ?= helm/groundx
OCP_VALUES_FILE ?= values-openshift.yaml
K8S_VALUES_FILE ?= values-k8s.yaml
TIMEOUT ?= 10m

# Detect if we're on OpenShift or Kubernetes
KUBECTL := $(shell command -v oc 2> /dev/null)
ifndef KUBECTL
	KUBECTL := kubectl
	PLATFORM := kubernetes
else
    KUBECTL := oc
	PLATFORM := openshift
endif

.PHONY: help
help: ## Display this help message
	@echo "Billing extraction with GroundX by EyeLevel - Makefile Commands"
	@echo "================================================"
	@echo ""
	@echo "Detected Platform: $(PLATFORM)"
	@echo "Using CLI: $(KUBECTL)"
	@echo ""
	@echo "Configuration:"
	@echo "  NAMESPACE=$(NAMESPACE)"
	@echo "  OCP_VALUES_FILE=$(VALUES_FILE)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Usage:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Helm repo management

.PHONY: add-helm-repos
add-helm-repos: 
    echo "Adding groundx helm repo"
	helm repo add groundx https://registry.groundx.ai/helm

    echo "Adding groundx percona repo"
    helm repo add percona https://percona.github.io/percona-helm-charts/

    echo "Adding groundx minio repo"
    helm repo add minio-operator https://operator.min.io/

    helm repo update

##@ Namespace Management

.PHONY: create-namespace
create-namespace: add-helm-repos
	@echo "Creating namespace: $(NAMESPACE)"
	@$(KUBECTL) create namespace $(NAMESPACE) || echo "Namespace $(NAMESPACE) already exists"

.PHONY: delete-namespace
delete-namespace: ## Delete the namespace (WARNING: This will delete all resources in the namespace)
	@echo "WARNING: This will delete namespace $(NAMESPACE) and all its resources!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(KUBECTL) delete namespace $(NAMESPACE); \
		echo "Namespace $(NAMESPACE) deleted"; \
	else \
		echo "Cancelled"; \
	fi

##@ Helm Chart Management

.PHONY: clean-install
clean-install: uninstall install ## Clean install the billing extraction demo environment

.PHONY: install
install: install-groundx ## Install the fraud-detection Helm chart
	echo "Installation complete!"

.PHONY: install-groundx
install-groundx: install-strimzi-kafka
	echo "Installing Groundx secret"
    helm upgrade --install groundx-secret groundx/groundx-secret \
        -f values/values.groundx.secret.yaml \
        -n $(NAMESPACE)
    sleep 1

    echo "Installing Groundx"
	helm upgrade --install groundx groundx/groundx \
        -f values/values.groundx.yaml 
        -n $(NAMESPACE)
	sleep 5

.PHONY: install-strimzi-kafka
install-strimzi-kafka: install-minio
	echo "Installing Strimzi Kafka operator"
    helm upgrade --install stream-operator oci://quay.io/strimzi-helm/strimzi-kafka-operator \
        -f values/values.strimzi.operator.yaml \
        -n $(NAMESPACE)
	sleep 5

	echo "Installing Strimzi Kafka cluster"
    helm upgrade --install stream-cluster groundx/groundx-strimzi-kafka-cluster \
        -f values/values.strimzi.cluster.yaml \
        -n $(NAMESPACE)
	sleep 5

.PHONY: install-minio
install-minio: install-db-cluster
    echo "Setting permissions of minio-operator and minio-tenant accounts"
    oc adm policy add-scc-to-user anyuid -z minio-operator -n $project
    oc adm policy add-scc-to-user anyuid -z minio-tenant-sa -n $project

	echo "Installing Minio operator"
    helm upgrade --install minio-operator minio-operator/operator \
        -f values/values.minio.operator.yaml \
        -n $(NAMESPACE)
	sleep 5

	echo "Installing Minio cluster"
    helm upgrade --install minio-cluster minio-operator/tenant \
        -f values/values.minio.tenant.yaml \
        -n $(NAMESPACE)
	sleep 5

    @if [ "$(PLATFORM)" = "openshift" ]; then \
		echo "Creating a route for Minio" \
        oc expose svc/minio -n $(NAMESPACE) \
	else \
		echo "Routes are only available on OpenShift"; \
	fi

.PHONY: install-db-cluster
install-db-cluster: create-groundx-storageclass
	echo "Installing Percona for MySQL database operator"
    helm upgrade --install db-operator percona/pxc-operator \
        -f values/values.percona.operator.yaml \
        -n $(NAMESPACE)
	sleep 5

	echo "Installing Percona for MySQL database cluster"
    helm upgrade --install db-cluster percona/pxc-db \
        -f values/values.percona.cluster.yaml \
        -n $(NAMESPACE)
	sleep 5

##@ Cluster Preparation

.PHONY: create-groundx-storageclass
create-groundx-storageclass: label-nodes
	echo "Creating a new storage class in the namespace"
	helm upgrade --install groundx-storageclass groundx/groundx-storageclass -n $(NAMESPACE)
	sleep 5

.PHONY: label-nodes
label-nodes: create-namespace
	echo "Labeling worker nodes"
	oc label node -l node-role.kubernetes.io/worker node=eyelevel-node
	echo ""
	oc get nodes -L node
	echo ""


.PHONY: uninstall 
uninstall:
	@echo "Uninstalling $(RELEASE_NAME) from namespace $(NAMESPACE)..."
	# This will delete the release and the namespace becuase there is persistent volume claims in the namespace
	@helm uninstall $(RELEASE_NAME) --namespace $(NAMESPACE) || echo "Release $(RELEASE_NAME) not found"
	@oc delete namespace $(NAMESPACE) || echo "Namespace $(NAMESPACE) not found so skipping deletion"
	@echo "Uninstall complete!"


##@ Status and Information
.PHONY: get-pods
get-pods: ## Get all pods in the namespace
	@$(KUBECTL) get pods -n $(NAMESPACE)

.PHONY: get-all
get-all: ## Get all resources in the namespace
	@$(KUBECTL) get all -n $(NAMESPACE)

.PHONY: describe
describe: ## Describe all resources in the namespace
	@$(KUBECTL) describe all -n $(NAMESPACE)

##@ Logs and Debugging

.PHONY: logs-groundx
logs-lakefs: ## Show GroundX logs
	@$(KUBECTL) logs -n $(NAMESPACE) -l app.kubernetes.io/component=groundx --tail=100 -f

.PHONY: logs-minio
logs-minio: ## Show MinIO logs
	@$(KUBECTL) logs -n $(NAMESPACE) -l app.kubernetes.io/component=minio --tail=100 -f

.PHONY: logs-cache
logs-minio: ## Show cache (Redis) logs
	@$(KUBECTL) logs -n $(NAMESPACE) -l app.kubernetes.io/component=cache --tail=100 -f

.PHONY: logs-kafka
logs-minio: ## Show Kafka logs
	@$(KUBECTL) logs -n $(NAMESPACE) -l app.kubernetes.io/component=kafka --tail=100 -f

.PHONY: logs-percona
logs-percona: ## Show Percona for MySQL logs
	@$(KUBECTL) logs -n $(NAMESPACE) -l app.kubernetes.io/component=percona --tail=100 -f

.PHONY: logs-notebook
logs-notebook: ## Show Jupyter notebook logs
	@$(KUBECTL) logs -n $(NAMESPACE) -l app.kubernetes.io/component=notebook --tail=100 -f

##@ Access and URLs

.PHONY: get-routes
get-routes: ## Get OpenShift routes (OpenShift only)
	@if [ "$(PLATFORM)" = "openshift" ]; then \
		$(KUBECTL) get routes -n $(NAMESPACE); \
	else \
		echo "Routes are only available on OpenShift"; \
	fi

.PHONY: get-services
get-services: ## Get all services
	@$(KUBECTL) get services -n $(NAMESPACE)

.PHONY: clean
clean: uninstall ## Uninstall the chart (alias for uninstall)

.PHONY: clean-all
clean-all: uninstall delete-namespace ## Uninstall the chart and delete the namespace
	@echo "Complete cleanup finished!"
