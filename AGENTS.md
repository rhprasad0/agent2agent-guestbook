# AGENTS.md

Guidelines for coding agents (e.g., Amazon Q Developer, Claude Code, ChatGPT) working in this repository.

This repository hosts the **sample application** (`a2a-guestbook`) for the **AWS/EKS DevOps Learning Lab**.

**Crucial Distinction:**
- **Main Repository (`aws-devops-lab`)**: Contains the **Platform Infrastructure** (VPC, EKS Cluster, IAM Roles, ALB Controller, etc.).
- **This Repository (`agent2agent-guestbook`)**: Contains the **Application Code**, Container definitions, and Kubernetes manifests to deploy the app onto the platform.

---

## 1. Philosophy

1.  **Application as an Artifact.**
    - This repo produces **artifacts**:
        - Docker Container Images.
        - Kubernetes Manifests (YAML) or Helm Charts.
    - It consumes the platform provided by the Main Repo.

2.  **Deployment-Centric.**
    - Changes to `app/` often require updates to `k8s/` (e.g., new environment variables).
    - Agents must ensure that code changes are reflected in the deployment configuration.

3.  **Production Standards.**
    - **Security**: Non-root containers, read-only filesystems, no hardcoded secrets.
    - **Observability**: Structured JSON logs, `/health` and `/metrics` endpoints.
    - **Resilience**: Graceful shutdown, retries for dependencies (DynamoDB).

---

## 2. Repository Structure (Target)

Agents should respect and maintain this structure:

```text
agent2agent-guestbook/
├─ app/                 # FastAPI Application source code
├─ k8s/                 # Kubernetes Manifests (Deployment, Service, Ingress)
├─ .github/             # CI/CD Workflows
├─ Dockerfile           # Production Dockerfile
├─ Makefile             # Local dev & build tasks
└─ README.md
```

*Note: If `k8s/` is missing, agents should create it when asked to prepare for deployment.*

---

## 3. Allowed Agent Actions

Agents **ARE allowed** to:

1.  **Modify Application Code (`app/`)**:
    - Add features, fix bugs.
    - **Must** follow 12-factor app principles (config via env vars).

2.  **Update Packaging (`Dockerfile`)**:
    - Optimize builds, update dependencies (`requirements.txt`).
    - Ensure security scanning compliance.

3.  **Create/Update Manifests (`k8s/`)**:
    - Write standard `apps/v1` Deployment and Service manifests.
    - Create `Ingress` resources that use the **AWS Load Balancer Controller** (provisioned by the Main Repo).
    - Create `ServiceAccount` definitions that map to IAM roles via EKS Pod Identity (provisioned by the Main Repo).

4.  **CI/CD (`.github/`)**:
    - Configure workflows to build and push images to ECR.
    - Configure image scanning (Trivy).

---

## 4. Forbidden Actions

Agents MUST NOT:

1.  **Create Platform Infrastructure**:
    - **No Terraform** for VPCs, EKS Clusters, or Node Groups in this repo.
    - **No AWS CLI** commands to create clusters.
    - Assume the cluster exists.

2.  **Hardcode Secrets**:
    - Never put API keys or credentials in code or manifests.
    - Use `ExternalSecrets` or assume they are mounted as K8s Secrets.

3.  **Confuse Scopes**:
    - If the user asks for an S3 bucket for the *app* to use, check if it should be created here (app-specific) or in the Main Repo (shared infra).
    - **Rule**: Assume all infrastructure (DynamoDB, S3, RDS, etc.) is provisioned in the Main Repo. Do not generate Terraform code in this repository. Use the resources provided by the platform.

---

## 5. Interaction Guidelines

1.  **Dependency Checks**:
    - If adding a feature that needs DynamoDB, ask: "Has the DynamoDB table been provisioned in the Main Repo infrastructure?"
    - If adding a new Secret, ask: "Has this secret been created in AWS Secrets Manager?"

2.  **Pod Identity Integration**:
    - This app uses **EKS Pod Identity** for AWS permissions (not IRSA).
    - The **Application** repo defines the `ServiceAccount` in `k8s/serviceaccount.yaml`.
    - The **Main** repo provisions the IAM Role and creates the **Pod Identity Association** binding the role to this ServiceAccount.
    - Agent Instruction: Create a standard `ServiceAccount` in `k8s/`. **Do not** add the `eks.amazonaws.com/role-arn` annotation. Ensure the ServiceAccount name matches what the Platform team expects.

3.  **Ingress Integration**:
    - The Main Repo installs the AWS Load Balancer Controller.
    - This repo defines the `Ingress` object.
    - Agent Instruction: Use the `alb` ingress class and appropriate annotations (`alb.ingress.kubernetes.io/scheme`, etc.).

---

## 6. DevSecOps Expectations

- **Vulnerability Scanning**: Ensure `trivy` or similar scans run in CI.
- **Least Privilege**: The application's IAM Role (via Pod Identity) should only have `dynamodb:PutItem/GetItem` and `secretsmanager:GetSecretValue`. Do not ask for `*:*`.
- **Network Policy**: Ingress should be restricted. Service should likely be `ClusterIP`.

---

## 7. Example Scenarios

**Scenario: Adding a new Env Var**
> User: "Add a feature flag."
> Agent: "I've updated `app/config.py` to read `FEATURE_FLAG`. I also updated `k8s/deployment.yaml` to include this environment variable."

