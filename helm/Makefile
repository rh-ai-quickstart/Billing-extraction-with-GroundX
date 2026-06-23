# Install and uninstall billing-operators and billing-workloads Helm charts
NAMESPACE ?= eyelevel
REPO_ROOT := $(abspath $(dir $(MAKEFILE_LIST))..)
HELM_OPERATORS := $(REPO_ROOT)/helm/billing-operators
HELM_WORKLOADS := $(REPO_ROOT)/helm/billing-workloads

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

.PHONY: install uninstall

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

uninstall:
	oc get perconaxtradbclusters.pxc.percona.com -n $(NAMESPACE) -o name | xargs -n 1 -I {} oc patch {} -n $(NAMESPACE) -p '{"metadata":{"finalizers":[]}}' --type=merge
	@for topic in $$(oc get kafkatopics -n $(NAMESPACE) -o name 2>/dev/null); do \
		oc patch "$$topic" -n $(NAMESPACE) --type=merge -p '{"metadata":{"finalizers":[]}}'; \
	done
	helm uninstall billing-workloads -n $(NAMESPACE) --ignore-not-found || true
	helm uninstall billing-operators -n $(NAMESPACE) --ignore-not-found || true
	# oc delete project $(NAMESPACE) --ignore-not-found || true


.PHONY: terminate
terminate:
	# Remove finalizers from Percona PXC CRs which are stuck in terminating state
	oc get perconaxtradbclusters.pxc.percona.com -n $(NAMESPACE) -o name | \
		xargs -n 1 -I {} oc patch {} -n $(NAMESPACE) -p '{"metadata":{"finalizers":[]}}' --type=merge