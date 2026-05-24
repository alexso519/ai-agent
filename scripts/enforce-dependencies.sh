#!/bin/bash
# =============================================================================
# Dependency Enforcement Script
# Governance: Section 3 — Architecture Enforcement Strategy
# =============================================================================
# This script enforces module boundary rules by checking import statements.
# Run in CI to detect forbidden cross-module dependencies.
#
# Canonical dependency map:
#   apps/web       -> packages/shared-types, packages/ui
#   apps/api       -> packages/shared-types, packages/crew-runtime
#   apps/worker    -> packages/shared-types, packages/crew-runtime
#   packages/crew-runtime -> packages/shared-types
#   packages/ui    -> packages/shared-types
# =============================================================================

set -euo pipefail

echo "=== Dependency Boundary Enforcement ==="
echo ""

HAS_ERROR=0

check_forbidden_import() {
    local source="$1"
    local target="$2"
    local message="$3"

    if grep -r "from.*$target" "$source" --include="*.ts" --include="*.tsx" --include="*.py" 2>/dev/null | grep -v "node_modules" | grep -v ".pyc"; then
        echo "ERROR: $message"
        echo "       Found in: $source imports $target"
        HAS_ERROR=1
    fi
}

# Frontend must not import from backend
check_forbidden_import "apps/web/src" "apps/api" "Frontend must not import from API layer"
check_forbidden_import "apps/web/src" "apps/worker" "Frontend must not import from Worker layer"
check_forbidden_import "apps/web/src" "packages/crew-runtime" "Frontend must not import from CrewRuntime"

# Backend must not import from frontend
check_forbidden_import "apps/api/src" "apps/web" "API must not import from Frontend"
check_forbidden_import "apps/worker/src" "apps/web" "Worker must not import from Frontend"

# UI package must not import from runtime
check_forbidden_import "packages/ui/src" "packages/crew-runtime" "UI must not import from CrewRuntime"

# Runtime must not import from apps
check_forbidden_import "packages/crew-runtime/src" "apps" "CrewRuntime must not depend on any app module"

if [ "$HAS_ERROR" -eq 1 ]; then
    echo ""
    echo "=== DEPENDENCY VIOLATIONS DETECTED ==="
    echo "Fix imports to comply with the canonical dependency map."
    exit 1
else
    echo "=== All dependency boundaries respected ==="
    exit 0
fi