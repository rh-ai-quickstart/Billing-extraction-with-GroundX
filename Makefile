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
	@echo "  RELEASE_NAME=$(RELEASE_NAME)"
	@echo "  VALUES_FILE=$(VALUES_FILE)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Usage:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Namespace Management

.PHONY: create-namespace
create-namespace: ## Create the namespace for fraud-detection
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
install: create-namespace ## Install the fraud-detection Helm chart
	@echo "Installing $(RELEASE_NAME) in namespace $(NAMESPACE)..."
	@if [ "$(PLATFORM)" = "openshift" ]; then \
		echo "Using OpenShift values..."; \
		helm install $(RELEASE_NAME) $(CHART_DIR) \
			--namespace $(NAMESPACE) \
			--values $(CHART_DIR)/$(OCP_VALUES_FILE) \
			--wait \
			--timeout $(TIMEOUT); \
	else \
		echo "Using default Kubernetes values..."; \
		helm install $(RELEASE_NAME) $(CHART_DIR) \
			--namespace $(NAMESPACE) \
			--values $(CHART_DIR)/$(K8S_VALUES_FILE) \
			--wait \
			--timeout $(TIMEOUT); \
	fi
	@echo "Installation complete!"

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
logs-minio: ## Show Percona for MySQL logs
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
