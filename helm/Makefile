# Install and uninstall billing-operators and billing-workloads Helm charts
NAMESPACE ?= eyelevel
REPO_ROOT := $(abspath $(dir $(MAKEFILE_LIST))..)
HELM_OPERATORS := $(REPO_ROOT)/helm/billing-operators
HELM_WORKLOADS := $(REPO_ROOT)/helm/billing-workloads
CLEANUP_SCRIPT := $(abspath $(dir $(MAKEFILE_LIST))scripts/cleanup-namespace.sh)

# Streamlit UI image (Quay)
UI_IMAGE ?= quay.io/rh-ai-quickstart/groundx-ui:latest
UI_BUILD_PLATFORM ?= linux/amd64
UI_DOCKERFILE := $(REPO_ROOT)/Dockerfile
UI_DEPLOYMENT ?= billing-workloads-frontend

OPERATORS_SECRET := $(HELM_OPERATORS)/secret.yaml
WORKLOADS_SECRET := $(HELM_WORKLOADS)/secret.yaml

OPERATORS_HELM_FLAGS := -f $(HELM_OPERATORS)/values.yaml
ifneq (,$(wildcard $(OPERATORS_SECRET)))
OPERATORS_HELM_FLAGS += -f $(OPERATORS_SECRET)
endif

WORKLOADS_HELM_FLAGS := -f $(HELM_WORKLOADS)/values.yaml
ifneq (,$(wildcard $(WORKLOADS_SECRET)))
WORKLOADS_HELM_FLAGS += -f $(WORKLOADS_SECRET)
endif

.PHONY: install uninstall terminate cleanup \
	login-ui-quay build-ui-image push-ui-image publish-ui-image

## Build / push Streamlit UI image to Quay (podman)

login-ui-quay:
	@podman login quay.io

build-ui-image:
	@echo "Building UI image: $(UI_IMAGE) for platform $(UI_BUILD_PLATFORM)"
	@podman build --platform $(UI_BUILD_PLATFORM) -f $(UI_DOCKERFILE) -t $(UI_IMAGE) $(REPO_ROOT)

push-ui-image: build-ui-image
	@echo "Pushing UI image: $(UI_IMAGE)"
	@podman push $(UI_IMAGE)

publish-ui-image: push-ui-image
	@echo "Restarting frontend deployment so it pulls $(UI_IMAGE)"
	@oc rollout restart deployment/$(UI_DEPLOYMENT) -n $(NAMESPACE)
	@oc rollout status deployment/$(UI_DEPLOYMENT) -n $(NAMESPACE) --timeout=300s

install:
	@test -f $(WORKLOADS_SECRET) || ( \
		echo "ERROR: $(WORKLOADS_SECRET) not found."; \
		echo "  cd $(HELM_WORKLOADS) && cp secret.example.yaml secret.yaml"; \
		echo "  Edit secret.yaml with your credentials, then re-run make install."; \
		exit 1)
	oc create namespace $(NAMESPACE) --dry-run=client -o yaml | oc apply -f - || true
	cd $(HELM_OPERATORS) && helm dependency update
	cd $(HELM_WORKLOADS) && helm dependency update
	helm upgrade --install billing-operators $(HELM_OPERATORS) $(OPERATORS_HELM_FLAGS) -n $(NAMESPACE)
	helm upgrade --install billing-workloads $(HELM_WORKLOADS) $(WORKLOADS_HELM_FLAGS) -n $(NAMESPACE)

cleanup:
	@chmod +x $(CLEANUP_SCRIPT)
	@$(CLEANUP_SCRIPT) $(NAMESPACE) force

uninstall:
	@chmod +x $(CLEANUP_SCRIPT)
	@$(CLEANUP_SCRIPT) $(NAMESPACE) pre-helm
	helm uninstall billing-workloads -n $(NAMESPACE) --ignore-not-found --no-hooks || true
	helm uninstall billing-operators -n $(NAMESPACE) --ignore-not-found || true
	@$(CLEANUP_SCRIPT) $(NAMESPACE) post-helm
	oc delete project $(NAMESPACE) --ignore-not-found --wait=false || true
	@$(CLEANUP_SCRIPT) $(NAMESPACE) force

terminate: cleanup
	helm uninstall billing-workloads -n $(NAMESPACE) --ignore-not-found --no-hooks || true
	helm uninstall billing-operators -n $(NAMESPACE) --ignore-not-found || true
	oc delete project $(NAMESPACE) --ignore-not-found --wait=false || true
	@chmod +x $(CLEANUP_SCRIPT)
	@$(CLEANUP_SCRIPT) $(NAMESPACE) force
