#!/usr/bin/env bash
#
# Purpose:
#   Remediate the shared Hemma nginx-proxy default host so unknown public-edge
#   requests fail closed through a reserved non-product container.
#
# Relationships:
#   - Implements the Task 254 shared-infrastructure default-host contract.
#   - Edits /home/paunchygent/infrastructure/docker-compose.yml on Hemma.
#   - Must be launched through hemma-command-start when --deploy is used.
#

set -euo pipefail

infra_root="${HEMMA_INFRASTRUCTURE_ROOT:-/home/paunchygent/infrastructure}"
compose_file="${infra_root}/docker-compose.yml"
reserved_host="hemma-reserved-default-host"
reserved_conf="${infra_root}/nginx/reserved-default-host.conf"
deploy=0

usage() {
  cat >&2 <<'EOF'
Usage: bash scripts/devops/hemma-public-edge-default-host-remediate.sh [--deploy]

Options:
  --deploy    Run docker compose up -d for nginx-proxy, acme-companion, and
              hemma-reserved-default-host after writing the config.
EOF
}

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --deploy)
      deploy=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ ! -f "${compose_file}" ]]; then
  echo "Infrastructure compose file not found: ${compose_file}" >&2
  exit 1
fi

backup_path="${compose_file}.bak-$(date -u +%Y%m%dT%H%M%SZ)"
cp -p "${compose_file}" "${backup_path}"
echo "Backed up infrastructure compose: ${backup_path}"

mkdir -p "$(dirname "${reserved_conf}")"
cat > "${reserved_conf}" <<'EOF'
server {
    listen 8080 default_server;
    server_name _;

    add_header X-Hemma-Reserved-Default-Host "hemma-reserved-default-host" always;
    add_header X-Content-Type-Options "nosniff" always;
    default_type text/plain;

    return 404 "hemma-reserved-default-host\n";
}
EOF
echo "Wrote reserved default-host nginx config: ${reserved_conf}"

if grep -qE '^[[:space:]]*-[[:space:]]*DEFAULT_HOST=' "${compose_file}"; then
  sed -i "s/^[[:space:]]*-[[:space:]]*DEFAULT_HOST=.*/      - DEFAULT_HOST=${reserved_host}/" "${compose_file}"
else
  tmp_file="$(mktemp)"
  awk '
    /^      - TRUST_DOWNSTREAM_PROXY=/ && ! inserted {
      print
      print "      - DEFAULT_HOST=hemma-reserved-default-host"
      inserted = 1
      next
    }
    { print }
    END {
      if (! inserted) {
        exit 7
      }
    }
  ' "${compose_file}" > "${tmp_file}" || {
    rm -f "${tmp_file}"
    echo "Could not insert DEFAULT_HOST under nginx-proxy environment." >&2
    exit 1
  }
  mv "${tmp_file}" "${compose_file}"
fi

if ! grep -qE "^  ${reserved_host}:" "${compose_file}"; then
  reserved_service_block="$(cat <<'EOF'
  hemma-reserved-default-host:
    image: nginx:1.27-alpine
    container_name: hemma-reserved-default-host
    restart: unless-stopped
    volumes:
      - ./nginx/reserved-default-host.conf:/etc/nginx/conf.d/default.conf:ro
    expose:
      - "8080"
    environment:
      - VIRTUAL_HOST=hemma-reserved-default-host
      - VIRTUAL_PORT=8080
      - PROXY_DEFAULT_SERVER=true
    networks:
      default:
        aliases:
          - hemma-reserved-default-host

EOF
)"
  tmp_file="$(mktemp)"
  awk -v block="${reserved_service_block}" '
    /^  acme-companion:/ && ! inserted {
      printf "%s\n", block
      inserted = 1
    }
    { print }
    END {
      if (! inserted) {
        printf "%s\n", block
      }
    }
  ' "${compose_file}" > "${tmp_file}"
  mv "${tmp_file}" "${compose_file}"
fi

sudo docker compose -f "${compose_file}" config >/dev/null
echo "Infrastructure compose validates with reserved default host."

if [[ "${deploy}" -eq 1 ]]; then
  sudo docker compose -f "${compose_file}" up -d \
    nginx-proxy \
    acme-companion \
    "${reserved_host}"
  echo "Infrastructure public edge services reconciled."
fi
