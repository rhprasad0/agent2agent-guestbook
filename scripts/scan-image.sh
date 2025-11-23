#!/bin/bash
# Local Trivy scanning script for development
# Usage: ./scripts/scan-image.sh [image-name]

set -e

IMAGE="${1:-guestbook:local}"

echo "🔍 Scanning image: $IMAGE"
echo ""

# Check if Trivy is installed
if ! command -v trivy &> /dev/null; then
    echo "❌ Trivy not found. Install it first:"
    echo "   brew install trivy  # macOS"
    echo "   apt-get install trivy  # Ubuntu/Debian"
    echo "   Or see: https://aquasecurity.github.io/trivy/latest/getting-started/installation/"
    exit 1
fi

echo "📋 Running vulnerability scan..."
trivy image \
    --severity HIGH,CRITICAL \
    --exit-code 1 \
    "$IMAGE"

SCAN_RESULT=$?

if [ $SCAN_RESULT -eq 0 ]; then
    echo ""
    echo "✅ No HIGH or CRITICAL vulnerabilities found"
    echo ""
    echo "📦 Generating SBOM..."
    trivy image --format cyclonedx --output sbom.json "$IMAGE"
    echo "✅ SBOM saved to sbom.json"
else
    echo ""
    echo "❌ HIGH or CRITICAL vulnerabilities detected"
    echo "Fix these before pushing to ECR"
    exit 1
fi
