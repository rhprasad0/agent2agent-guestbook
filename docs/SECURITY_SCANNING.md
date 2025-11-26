# Security Scanning with Trivy

## Overview

Trivy is integrated into the CI/CD pipeline to scan container images for vulnerabilities before deployment. This implements Week 8's security requirements.

## What Gets Scanned

- **Vulnerabilities**: OS packages and application dependencies
- **Severity Levels**: HIGH and CRITICAL (build fails on these)
- **SBOM Generation**: CycloneDX format for supply chain tracking

## CI/CD Integration

The GitHub Actions workflow (`build-and-push.yml`) automatically:

1. Builds the Docker image
2. Runs Trivy vulnerability scan
3. **Fails the build** if HIGH/CRITICAL vulnerabilities found
4. Uploads results to GitHub Security tab
5. Generates and stores SBOM as artifact
6. Only pushes to ECR if scan passes

## Local Development

### Install Trivy

```bash
# macOS
brew install trivy

# Ubuntu/Debian
sudo apt-get install trivy

# Or see: https://aquasecurity.github.io/trivy/latest/getting-started/installation/
```

### Scan Before Pushing

```bash
# Build your image
docker build -t guestbook:local .

# Run security scan
./scripts/scan-image.sh guestbook:local
```

### Manual Trivy Commands

```bash
# Vulnerability scan (HIGH/CRITICAL only)
trivy image --severity HIGH,CRITICAL guestbook:local

# Full scan (all severities)
trivy image guestbook:local

# Generate SBOM
trivy image --format cyclonedx --output sbom.json guestbook:local

# Scan specific image from ECR
trivy image 407645373626.dkr.ecr.us-east-1.amazonaws.com/eks-lab/guestbook:latest
```

## Understanding Results

### Vulnerability Output

```
guestbook:local (python 3.11-slim)
==================================
Total: 5 (HIGH: 3, CRITICAL: 2)

┌───────────────┬────────────────┬──────────┬───────────────────┬───────────────┬────────────────────────────────────┐
│   Library     │ Vulnerability  │ Severity │ Installed Version │ Fixed Version │             Title                  │
├───────────────┼────────────────┼──────────┼───────────────────┼───────────────┼────────────────────────────────────┤
│ openssl       │ CVE-2024-1234  │ CRITICAL │ 1.1.1n            │ 1.1.1w        │ OpenSSL buffer overflow            │
└───────────────┴────────────────┴──────────┴───────────────────┴───────────────┴────────────────────────────────────┘
```

### Remediation Steps

1. **Update base image**: Use newer Python version with patched dependencies
2. **Update dependencies**: Run `pip install --upgrade <package>`
3. **Accept risk**: Document why vulnerability is acceptable (if applicable)
4. **Suppress**: Add to `.trivyignore` with justification (use sparingly)

## Suppressing False Positives

Create `.trivyignore` in project root:

```
# Suppress specific CVE with justification
CVE-2024-1234  # Not exploitable in our use case - no network exposure
```

**Important**: Always document WHY you're suppressing a vulnerability.

## SBOM (Software Bill of Materials)

The SBOM is generated in CycloneDX format and includes:
- All dependencies and their versions
- License information
- Component relationships

### Viewing SBOM

```bash
# Download from GitHub Actions artifacts
# Or generate locally:
trivy image --format cyclonedx --output sbom.json guestbook:local

# View with jq
cat sbom.json | jq '.components[] | {name: .name, version: .version}'
```

## GitHub Security Integration

Trivy results are uploaded to GitHub's Security tab:

1. Go to repository → Security → Code scanning alerts
2. View Trivy findings with severity, location, and remediation
3. Track vulnerability trends over time

## Cost Considerations

- **Trivy**: Free and open source
- **GitHub Actions**: Free for public repos, included in private repo minutes
- **ECR Scanning**: Also enabled ($0.09/image scan) - provides AWS-native view

## Week 8 Security Checklist

- [x] Trivy integrated into CI/CD pipeline
- [x] Build fails on HIGH/CRITICAL vulnerabilities
- [x] SBOM generation enabled
- [x] Results uploaded to GitHub Security
- [x] Local scanning script available
- [x] Immutable tags (git SHA) used instead of `latest`
- [x] GitHub OIDC for AWS authentication (no long-lived keys)

## Scanned Images Only - Enforcement (Week 9)

The following controls ensure only security-scanned images can be deployed:

### Defense in Depth Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Security Enforcement Layers                  │
├─────────────────────────────────────────────────────────────────┤
│ Layer 1: CI/CD Pipeline                                          │
│   • Trivy scan with exit-code: 1 (fails on HIGH/CRITICAL)        │
│   • Scan attestation tag added (scan-passed-<sha>)               │
│   • Image only pushed after scan passes                          │
├─────────────────────────────────────────────────────────────────┤
│ Layer 2: PR Validation (manifest repo)                           │
│   • validate-image-refs.yml workflow                             │
│   • Checks ECR for scan-passed attestation tag                   │
│   • Blocks PR merge if image not scanned                         │
├─────────────────────────────────────────────────────────────────┤
│ Layer 3: Kubernetes Admission (Kyverno)                          │
│   • require-ecr-images.yaml - Only ECR registry                  │
│   • require-immutable-tags.yaml - No 'latest' tag                │
│   • verify-scan-attestation.yaml - Check attestation (advanced)  │
└─────────────────────────────────────────────────────────────────┘
```

### Infrastructure Setup (aws-devops-lab repo)

The following components are configured in the **infrastructure repo** (`aws-devops-lab`):

1. **Kyverno Installation** - Kubernetes admission controller
2. **Kyverno Policies** - Enforce ECR-only images and block mutable tags
3. **PR Validation Workflow** - Verify image attestations before merge

See the infrastructure repo for setup instructions.

### Scan Attestation

When an image passes Trivy scanning, the CI/CD pipeline:

1. Pushes the image with git SHA tag: `guestbook:abc123def`
2. Creates attestation tag: `guestbook:scan-passed-abc123def`

The PR validation workflow checks for this attestation tag before allowing merge.

## AWS Documentation References

This implementation follows AWS best practices documented in:

- **[EKS Best Practices - Image Security](https://docs.aws.amazon.com/eks/latest/best-practices/image-security.html)**
  - Scan images for vulnerabilities regularly ✅
  - Use attestations to validate artifact integrity ✅
  - Create SBOMs for container images ✅
  - Use immutable tags ✅
  - Image signing and admission controllers ✅

- **[Validate Container Image Signatures](https://docs.aws.amazon.com/eks/latest/userguide/image-verification.html)**
  - Kyverno with AWS Signer plugin for signature validation

- **[Well-Architected DevOps Guidance - DL.CS.3](https://docs.aws.amazon.com/wellarchitected/latest/devops-guidance/dl.cs.3-enforce-verification-before-using-signed-artifacts.html)**
  - Enforce verification before using signed artifacts
  - Integrate signature verification into deployment pipeline
  - Use Kubernetes admission controller

- **[Container Build Lens - Securing Pipelines](https://docs.aws.amazon.com/wellarchitected/latest/container-build-lens/securing-containerized-build-pipelines.html)**
  - Enable tag immutability
  - Scan container images for vulnerabilities
  - Run acceptance tests

- **[Kyverno on Amazon EKS](https://aws.amazon.com/blogs/containers/easy-as-one-two-three-policy-management-with-kyverno-on-amazon-eks/)**
  - Policy-as-code for Kubernetes
  - Validate and mutate configurations

## Next Steps (Week 14)

- [ ] Integrate with External Secrets Operator
- [ ] Implement automated vulnerability remediation PRs
- [ ] Add AWS Signer image signing for cryptographic attestations (see [IMAGE_SIGNING_ENHANCEMENT.md](IMAGE_SIGNING_ENHANCEMENT.md))
- [ ] Implement runtime image verification with Notation
