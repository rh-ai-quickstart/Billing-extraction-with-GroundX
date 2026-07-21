#!/bin/sh
# Remove billing-extraction CRs and finalizers that block helm uninstall
# or leave the OpenShift project stuck in Terminating.
#
# Usage: cleanup-namespace.sh <namespace> [phase]
#   phase: all (default) | pre-helm | post-helm | force

set -eu

NAMESPACE="${1:?namespace required}"
PHASE="${2:-all}"

patch_finalizers() {
  resource="$1"
  name="$2"
  if oc get "$resource" -n "$NAMESPACE" "$name" >/dev/null 2>&1; then
    oc patch "$resource" -n "$NAMESPACE" "$name" --type=merge \
      -p '{"metadata":{"finalizers":[]}}' || true
  fi
}

patch_all_finalizers() {
  resource="$1"
  for item in $(oc get "$resource" -n "$NAMESPACE" -o name 2>/dev/null); do
    oc patch "$item" -n "$NAMESPACE" --type=merge \
      -p '{"metadata":{"finalizers":[]}}' || true
  done
}

cleanup_hook_jobs() {
  echo "Removing billing hook jobs..."
  oc delete job -n "$NAMESPACE" \
    -l app.kubernetes.io/instance=billing-workloads \
    --ignore-not-found --wait=false 2>/dev/null || true
  for job in billing-workloads-cleanup-crs billing-workloads-delete-project \
    billing-workloads-notebook-git-clone; do
    oc delete job "$job" -n "$NAMESPACE" --ignore-not-found --wait=false 2>/dev/null || true
  done
}

cleanup_kafka() {
  echo "Cleaning up Kafka / Strimzi resources..."

  oc delete kafkatopic --all -n "$NAMESPACE" --wait=false 2>/dev/null || true
  sleep 2
  patch_all_finalizers kafkatopics.kafka.strimzi.io
  oc delete kafkatopic --all -n "$NAMESPACE" --wait=false --force --grace-period=0 2>/dev/null || true

  oc delete kafka --all -n "$NAMESPACE" --wait=false 2>/dev/null || true
  patch_finalizers kafka stream-cluster
  patch_finalizers kafkas.kafka.strimzi.io stream-cluster
  patch_all_finalizers kafkas.kafka.strimzi.io

  oc delete kafkanodepool --all -n "$NAMESPACE" --wait=false 2>/dev/null || true
  patch_all_finalizers kafkanodepools.kafka.strimzi.io
}

cleanup_minio() {
  echo "Cleaning up MinIO tenant..."

  oc delete tenant --all -n "$NAMESPACE" --wait=false 2>/dev/null || true
  patch_finalizers tenant minio-tenant
  patch_finalizers tenants.minio.min.io minio-tenant
  patch_all_finalizers tenants.minio.min.io
}

cleanup_percona() {
  echo "Cleaning up Percona PXC cluster..."

  oc delete pxc --all -n "$NAMESPACE" --wait=false 2>/dev/null || true
  patch_finalizers pxc db-cluster
  patch_finalizers perconaxtradbclusters.pxc.percona.com db-cluster
  patch_all_finalizers perconaxtradbclusters.pxc.percona.com
}

cleanup_notebook() {
  echo "Cleaning up OpenShift AI notebooks..."

  oc delete notebook --all -n "$NAMESPACE" --wait=false 2>/dev/null || true
  patch_all_finalizers notebooks.kubeflow.org
}

cleanup_groundx_deployments() {
  echo "Removing GroundX deployments..."
  oc delete deployment --all -n "$NAMESPACE" --wait=false 2>/dev/null || true
}

cleanup_namespace_finalizers() {
  if ! oc get namespace "$NAMESPACE" >/dev/null 2>&1; then
    return 0
  fi

  phase="$(oc get namespace "$NAMESPACE" -o jsonpath='{.status.phase}' 2>/dev/null || true)"
  if [ "$phase" = "Terminating" ]; then
    echo "Namespace $NAMESPACE is Terminating; clearing remaining CR finalizers..."
    cleanup_kafka
    cleanup_minio
    cleanup_percona
    cleanup_notebook

    echo "Removing namespace/project finalizers..."
    oc patch namespace "$NAMESPACE" --type=merge \
      -p '{"spec":{"finalizers":[]}}' 2>/dev/null || true
    oc patch project "$NAMESPACE" --type=merge \
      -p '{"spec":{"finalizers":[]}}' 2>/dev/null || true
  fi
}

run_pre_helm() {
  cleanup_hook_jobs
  cleanup_groundx_deployments
  cleanup_kafka
  cleanup_minio
  cleanup_percona
  cleanup_notebook
}

run_post_helm() {
  cleanup_kafka
  cleanup_minio
  cleanup_percona
  cleanup_notebook
  cleanup_hook_jobs
  cleanup_namespace_finalizers
}

case "$PHASE" in
  pre-helm)
    run_pre_helm
    ;;
  post-helm)
    run_post_helm
    ;;
  force)
    run_pre_helm
    run_post_helm
    ;;
  all)
    run_pre_helm
    run_post_helm
    ;;
  *)
    echo "Unknown phase: $PHASE" >&2
    exit 1
    ;;
esac

echo "Cleanup complete for namespace $NAMESPACE (phase: $PHASE)."
