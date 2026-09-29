set -euo pipefail

UMU_VERSION="1.4.4"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$ROOT/resources"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

URL="https://github.com/Open-Wine-Components/umu-launcher/releases/download/${UMU_VERSION}/umu-launcher-${UMU_VERSION}-zipapp.tar"
mkdir -p "$DEST"

echo "Downloading UMU Launcher ${UMU_VERSION}..."
curl -fL --retry 3 "$URL" -o "$TMP/umu.tar"
tar -xf "$TMP/umu.tar" -C "$TMP"

UMU_FILE="$(find "$TMP" -type f -name 'umu-run*' -print -quit)"
if [[ -z "$UMU_FILE" ]]; then
    echo "Could not find umu-run in the release archive." >&2
    exit 1
fi

install -Dm755 "$UMU_FILE" "$DEST/umu-run"
echo "Installed bundled UMU Launcher at $DEST/umu-run"
