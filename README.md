# Data extraction with GroundX with OpenShift AI

GroundX by EyeLevel is an enterprise platform that eliminates LLM hallucinations by grounding AI responses in a company’s specific, private data. The platform utilizes advanced computer vision to preserve the context of complex document layouts, such as nested tables and schematics, ensuring high-fidelity search and retrieval. Beyond information discovery, it functions as a powerful tool for automated data extraction, transforming unstructured files into structured, verifiable insights with direct source citations.

When used with OpenShift AI on premises, customers can have complete control of their own data and where it is stored and processed.

## Table of contents

- [Detailed description](#detailed-description)
  - [See it in action](#see-it-in-action)
  - [Architecture diagrams](#architecture-diagrams)
- [Requirements](#requirements)
  - [Minimum hardware requirements](#minimum-hardware-requirements)
  - [Minimum software requirements](#minimum-software-requirements)
  - [Required user permissions](#required-user-permissions)
- [Deploy](#deploy)
  - [Pre-requisites](#pre-requisites)
  - [Deployment steps](#deployment-steps)
  - [Delete](#delete)
- [References](#references)
- [Technical details](#technical-details)
- [Tags](#tags)

## Detailed description

This AI quickstart demonstrates how to use **GroundX** from **EyeLevel** for billing data extraction in an on-prem AI environment with OpenShift AI.

You will deploy GroundX, as well as other components including MinIO (object storage), Percona MySQL, and Strimzi Kafka. You'll then open the included Jupyter notebook and follow the workflow. 

### See it in action

1. Create a new project called `eyelevel` and deploy the following in the project:
  - Custome storage class
  - Percona MySQK
  - MinIO
  - Strimzi Kafka
  - GroundX
2. Run a Jupytper notebook to demostrate data extraction from a mobile phone bill

### Architecture diagrams

![alt text](docs/images/groundx-arch.png "GroundX architecture")


## Requirements

This quickstart was developed and test on an OpenShift cluster with the following components and resources. This can be considered the minimum requirements.

### Minimum hardware requirements 

| Node Type           | Qty  | vCPU   | Memory (GB) |
| --------------------|------|-------|--------------|
| Control Plane       | 3    | 4     | 16           |
| Worker              | 3    | 4     | 16           |

Nvidia GPU with 16GB of vRAM

### Minimum software requirements

This quickstart was tested with the following software versions:

| Software                           | Version  |
| ---------------------------------- |:---------|
| Red Hat OpenShift                  | 4.20.5   |
| Red Hat OpenShift Service Mesh     | 2.5.11-0 |
| Red Hat OpenShift Serverless       | 1.37.0   |
| Red Hat OpenShift AI               | 2.25     |
| helm                               | 3.17.1   |
| GroundX                            | 2.9.92   |
| MinIO                              | TBD      |


### Required user permissions

The user performing this quickstart should have the ability to create a project in OpenShift and OpenShift AI. This requires the cluster role of `admin` (does not require `cluster-admin`)


## Deploy

The process is very simple. Just follow the steps below.

### Pre-requisites

The steps assume the following pre-requisite products and components are deployed and functional with required permissions on the cluster:

1. Red Hat OpenShift Container Platform
2. Red Hat OpenShift Service Mesh
3. Red Hat OpenShift Serverless
4. Red Hat OpenShift AI
5. Node Feature Discovery operator
6. Nvidia GPU operator75. User has `admin` permissions in the cluster
7. The `eyelevel` project should not exist

### Deployment Steps

1. Clone this repo and change into the directory
```
$ git clone https://github.com/rh-ai-quickstart/Billing-extraction-with-GroundX.git

cd Billing-extraction-with-GroundX
```

2. Login to the OpenShift cluster:
```
$ oc login --token=<user_token> --server=https://api.<openshift_cluster_fqdn>:6443
```

3. Make sure `setup` file is executable and run it, passing it the name of the project in which to install. It can be an existing or new project. In this example, it will deploy to the `lakefs` project.
```
# Make script executable
$ chmod + setup

# Run script passing it the project in which to install
$ ./setup
```

### Delete

The project the apps were installed in can be deleted, which will delete all of the resources in it.
```
oc delete project eyelevel
```

## References 

* [GroundX documentation](https://docs.eyelevel.ai/documentation/fundamentals/welcome)
* OpenShift AI documentatin [v2.25](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/2.25)

## Technical details


## Tags

* Product: OpenShift AI
* Partner: EyeLevel
* Partner product: GroundX
* Business challenge: Data extraction
