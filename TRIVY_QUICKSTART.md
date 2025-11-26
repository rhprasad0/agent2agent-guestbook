# Trivy Quick Reference

## Install Trivy

```bash
# macOS
brew install trivy

# Ubuntu/Debian
sudo apt-get install trivy

# Other: https://aquasecurity.github.io/trivy/latest/getting-started/installation/
```

## Common Commands

```bash
# Build and scan locally
make scan

# Scan specific image
trivy image guestbook:local

# Scan with specific severity
trivy image --severity HIGH,CRITICAL guestbook:local

# Generate SBOM
trivy image --format cyclonedx --output sbom.json guestbook:local

# Scan remote ECR image
trivy image 407645373626.dkr.ecr.us-east-1.amazonaws.com/eks-lab/guestbook:latest
```

## CI/CD Behavior

✅ **Scan passes** → Image pushed to ECR with `scan-passed-<sha>` attestation tag  
❌ **HIGH/CRITICAL found** → Build fails, no push, PR validation blocks merge

## View Results

- **GitHub Security**: Repository → Security → Code scanning alerts
- **GitHub Actions**: Workflow run logs
- **SBOM Artifact**: Download from workflow run
- **ECR Console**: Native AWS scanning results

## Suppress False Positives

Create `.trivyignore`:
```
CVE-2024-1234  # Justification required
```

## Week 8 Goals ✅

- [x] Fail builds on HIGH/CRITICAL vulnerabilities
- [x] Generate SBOM for supply chain tracking
- [x] Upload results to GitHub Security
- [x] Use immutable image tags (git SHA)
- [x] No long-lived AWS credentials (OIDC)

## Next: Week 9 GitOps

Update K8s manifests with scanned image tags and deploy via Argo CD.
