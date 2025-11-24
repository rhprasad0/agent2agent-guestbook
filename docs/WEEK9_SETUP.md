# Week 9 Task 1: GitOps Deployment Setup

## What We Built

Updated the CI/CD pipeline to implement a complete GitOps flow:

```
Code Push → Build Image → Push to ECR → Update Manifest → Argo CD Syncs → Pods Updated
```

## Architecture

1. **Build Job** (`build-and-push`):
   - Builds ARM64 image for Graviton nodes
   - Runs Trivy security scan
   - Generates SBOM
   - Pushes to ECR with git SHA tag

2. **Update Job** (`update-manifest`):
   - Checks out `aws-devops-lab` repo
   - Updates `k8s/guestbook/kustomization.yaml` with new image tag
   - Commits and pushes change
   - Argo CD detects change and auto-syncs

## Setup Instructions

### 1. Create GitHub Personal Access Token (PAT)

The workflow needs permission to push to the `aws-devops-lab` repository.

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Name: `GitOps Manifest Updates`
4. Expiration: 90 days (or custom)
5. Scopes: Check **`repo`** (full control of private repositories)
6. Click "Generate token"
7. **Copy the token immediately** (you won't see it again)

### 2. Add PAT to Repository Secrets

1. Go to `agent2agent-guestbook` repository
2. Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Name: `GITOPS_PAT`
5. Value: Paste the PAT you copied
6. Click "Add secret"

### 3. Verify Argo CD Configuration

Ensure Argo CD is watching the correct branch:

```bash
kubectl get application guestbook -n argocd -o yaml | grep targetRevision
```

Should show: `targetRevision: week9`

### 4. Test the Full Flow

1. Make a code change in `agent2agent-guestbook/app/`:
   ```bash
   cd agent2agent-guestbook
   # Edit app/main.py or any file
   git add .
   git commit -m "test: trigger CI/CD flow"
   git push origin main
   ```

2. Watch the GitHub Actions workflow:
   - Go to Actions tab in `agent2agent-guestbook` repo
   - Watch both jobs: `build-and-push` and `update-manifest`

3. Verify manifest was updated:
   ```bash
   cd ../aws-devops-lab
   git pull origin week9
   cat k8s/guestbook/kustomization.yaml | grep newTag
   ```

4. Watch Argo CD sync:
   ```bash
   # Port-forward to Argo CD UI
   kubectl port-forward svc/argocd-server -n argocd 8080:443
   
   # In another terminal, watch the sync
   kubectl get application guestbook -n argocd -w
   ```

5. Monitor pod rollout:
   ```bash
   kubectl rollout status deployment/guestbook -n guestbook
   kubectl get pods -n guestbook -w
   ```

6. Verify new image is running:
   ```bash
   kubectl get deployment guestbook -n guestbook -o jsonpath='{.spec.template.spec.containers[0].image}'
   ```

## How It Works

### Image Tag Strategy

- **Build time**: Uses git SHA as image tag (e.g., `abc123def`)
- **Immutable tags**: Each commit gets a unique image
- **Traceability**: Can trace running pods back to exact commit

### GitOps Pattern

- **Single source of truth**: Git repo (`aws-devops-lab`)
- **Declarative**: Kustomization defines desired state
- **Automated sync**: Argo CD reconciles every 3 minutes (default)
- **Self-healing**: Manual `kubectl` changes are reverted

### Security Features

- ✅ OIDC authentication (no long-lived AWS keys)
- ✅ Image scanning with Trivy
- ✅ SBOM generation
- ✅ Signed commits from GitHub Actions bot
- ✅ PAT with minimal scope (repo only)

## Troubleshooting

### Workflow fails with "Permission denied"

- Verify `GITOPS_PAT` secret exists and has `repo` scope
- Check PAT hasn't expired
- Ensure PAT is from a user with write access to `aws-devops-lab`

### Argo CD doesn't sync

- Check sync policy: `kubectl get application guestbook -n argocd -o yaml`
- Verify `automated: true` is set
- Check Argo CD logs: `kubectl logs -n argocd deployment/argocd-application-controller`
- Manual sync: `argocd app sync guestbook` (if argocd CLI installed)

### Pods don't update

- Check image pull: `kubectl describe pod -n guestbook <pod-name>`
- Verify ECR image exists: `aws ecr describe-images --repository-name eks-lab/guestbook --region us-east-1`
- Check IRSA permissions for guestbook service account

### Wrong branch

If Argo CD is watching the wrong branch:

```bash
kubectl patch application guestbook -n argocd --type merge -p '{"spec":{"source":{"targetRevision":"week9"}}}'
```

## Cost Impact

**No additional cost** - uses existing infrastructure:
- GitHub Actions: Free for public repos
- ECR storage: ~$0.10/GB/month (minimal for a few images)
- Argo CD: Already running in cluster

## Next Steps (Week 9, Task 2+)

- [ ] Task 2: Configure Argo CD sync policy options (prune, self-heal)
- [ ] Task 3: Implement deployment strategy (Blue/Green or Canary with Argo Rollouts)
- [ ] Task 4: Add rollback testing
- [ ] Task 5: Test full flow with intentional failures

## References

- [Argo CD Automated Sync Policy](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/)
- [Kustomize Image Transformer](https://kubectl.docs.kubernetes.io/references/kustomize/kustomization/images/)
- [GitHub Actions OIDC with AWS](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)
