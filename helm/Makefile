# Install and uninstall billing-operators and billing-workloads Helm charts
NAMESPACE ?= eyelevel
REPO_ROOT := $(abspath $(dir $(MAKEFILE_LIST))..)
HELM_OPERATORS := $(REPO_ROOT)/helm/billing-operators
HELM_WORKLOADS := $(REPO_ROOT)/helm/billing-workloads

.PHONY: check-groundx-key install uninstall

check-groundx-key:
ifndef GROUNDX_AGENT_API_KEY
	$(error GROUNDX_AGENT_API_KEY is not set. Export it before running install, e.g.: export GROUNDX_AGENT_API_KEY=<your-key>)
endif

install: check-groundx-key
	oc create namespace $(NAMESPACE) --dry-run=client -o yaml | oc apply -f - || true
	cd $(HELM_OPERATORS) && helm dependency update
	cd $(HELM_WORKLOADS) && helm dependency update
	helm upgrade --install billing-operators $(HELM_OPERATORS) -f $(HELM_OPERATORS)/values.yaml -n $(NAMESPACE)
	helm upgrade --install billing-workloads $(HELM_WORKLOADS) -f $(HELM_WORKLOADS)/values.yaml -n $(NAMESPACE) \
		--set groundx-secret.data.GROUNDX_AGENT_API_KEY=$(GROUNDX_AGENT_API_KEY)

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