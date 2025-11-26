# Image Signing Enhancement (AWS Recommended)

Based on AWS EKS Best Practices, cryptographic image signing provides stronger security than tag-based attestations.

## Current vs Enhanced Approach

| Approach | Current | Enhanced (AWS Recommended) |
|----------|---------|---------------------------|
| Method | Tag-based attestation (`scan-passed-*`) | Cryptographic signature |
| Verification | Check tag exists in ECR | Verify digital signature |
| Tampering Protection | Low (tags can be recreated) | High (signatures are cryptographic) |
| AWS Service | N/A | AWS Signer |
| Kubernetes Integration | Custom validation | Native Kyverno `verifyImages` |

## AWS-Recommended Solution: AWS Signer + Kyverno

### Step 1: Set Up AWS Signer

```bash
# Create a signing profile
aws signer put-signing-profile \
  --profile-name guestbook-signing-profile \
  --platform-id Notation-OCI-SHA384-ECDSA

# Note the profile ARN for use in CI/CD
```

### Step 2: Update CI/CD to Sign Images

Add to `.github/workflows/build-and-push.yml`:

```yaml
      - name: Install Notation CLI
        run: |
          curl -Lo notation.tar.gz https://github.com/notaryproject/notation/releases/download/v1.1.0/notation_1.1.0_linux_amd64.tar.gz
          tar -xzf notation.tar.gz
          sudo mv notation /usr/local/bin/
          
      - name: Install AWS Signer plugin for Notation
        run: |
          curl -Lo notation-aws-signer.tar.gz https://d2hvyiie56hcat.cloudfront.net/linux/amd64/plugin/latest/notation-aws-signer-plugin.tar.gz
          tar -xzf notation-aws-signer.tar.gz
          mkdir -p ~/.config/notation/plugins/com.amazonaws.signer.notation.plugin
          mv notation-aws-signer-plugin ~/.config/notation/plugins/com.amazonaws.signer.notation.plugin/

      - name: Sign image with AWS Signer
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          notation sign $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG \
            --plugin com.amazonaws.signer.notation.plugin \
            --plugin-config profile_arn=arn:aws:signer:us-east-1:407645373626:/signing-profiles/guestbook-signing-profile
          echo "✅ Image signed with AWS Signer"
```

### Step 3: Update Kyverno Policy for Signature Verification

Replace the tag-based policy with signature verification:

```yaml
# policies/kyverno/verify-image-signature.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-image-signature
  annotations:
    policies.kyverno.io/title: Verify AWS Signer Image Signatures
    policies.kyverno.io/category: Supply Chain Security
    policies.kyverno.io/severity: high
spec:
  validationFailureAction: Enforce
  webhookTimeoutSeconds: 30
  rules:
    - name: verify-signature
      match:
        any:
          - resources:
              kinds:
                - Pod
              namespaces:
                - guestbook
      verifyImages:
        - imageReferences:
            - "407645373626.dkr.ecr.*.amazonaws.com/eks-lab/*"
          attestors:
            - count: 1
              entries:
                - keys:
                    kms: "arn:aws:signer:us-east-1:407645373626:/signing-profiles/guestbook-signing-profile"
          required: true
```

### Step 4: Install Kyverno with AWS Signer Support

```bash
# Install Kyverno with Notation extension
helm install kyverno kyverno/kyverno \
  --namespace kyverno \
  --create-namespace \
  --set features.notationExtension.enabled=true \
  --set features.notationExtension.awsSigner.enabled=true
```

## Benefits of AWS Signer

1. **Cryptographic Verification**: Signatures cannot be forged
2. **AWS-Managed Keys**: No key management overhead
3. **Audit Trail**: CloudTrail logs all signing operations
4. **Revocation**: Can revoke signatures if needed
5. **Compliance**: Meets SOC2, PCI-DSS requirements

## References

- [AWS Signer Documentation](https://docs.aws.amazon.com/signer/latest/developerguide/Welcome.html)
- [Container Image Signing with AWS Signer and Amazon EKS](https://aws.amazon.com/blogs/containers/announcing-container-image-signing-with-aws-signer-and-amazon-eks/)
- [Kyverno Image Verification](https://kyverno.io/docs/writing-policies/verify-images/)
- [EKS Best Practices - Image Security](https://docs.aws.amazon.com/eks/latest/best-practices/image-security.html)
- [AWS Well-Architected DevOps Guidance - Enforce Verification](https://docs.aws.amazon.com/wellarchitected/latest/devops-guidance/dl.cs.3-enforce-verification-before-using-signed-artifacts.html)

## Migration Path

1. **Phase 1 (Current)**: Tag-based attestation + Kyverno registry restriction
2. **Phase 2**: Add AWS Signer signing to CI/CD
3. **Phase 3**: Enable Kyverno signature verification
4. **Phase 4**: Remove tag-based attestation (optional)

This provides a gradual migration path without disrupting existing deployments.




