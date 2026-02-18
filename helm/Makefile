# Install and uninstall billing-operators and billing-workloads Helm charts
NAMESPACE ?= eyelevel
REPO_ROOT := $(abspath $(dir $(MAKEFILE_LIST))..)
HELM_OPERATORS := $(REPO_ROOT)/helm/billing-operators
HELM_WORKLOADS := $(REPO_ROOT)/helm/billing-workloads

.PHONY: install uninstall

install:
	oc create namespace $(NAMESPACE) --dry-run=client -o yaml | oc apply -f - || true
	cd $(HELM_OPERATORS) && helm dependency update
	cd $(HELM_WORKLOADS) && helm dependency update
	helm upgrade --install billing-operators $(HELM_OPERATORS) -f $(HELM_OPERATORS)/values.yaml -n $(NAMESPACE)
	helm upgrade --install billing-workloads $(HELM_WORKLOADS) -f $(HELM_WORKLOADS)/values.yaml -n $(NAMESPACE)

uninstall:
	helm uninstall billing-workloads -n $(NAMESPACE) --ignore-not-found || true
	helm uninstall billing-operators -n $(NAMESPACE) --ignore-not-found || true
	# oc delete project $(NAMESPACE) --ignore-not-found || true
