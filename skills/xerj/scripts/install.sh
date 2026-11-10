#!/bin/sh
# Deploy the xerj wrappers to ~/.bun/bin as symlinks back to this repo.
# These wrappers are local code, not part of the xerj release: `xerj-service
# install/update` only replaces the `xerj` binary and never touches them.
set -eu

src=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
dst="${XERJ_BIN_DIR:-$HOME/.bun/bin}"
mkdir -p "$dst"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

body() { sed 1d "$1"; }

for name in xerj-service xerj-project; do
  if [ -L "$dst/$name" ]; then
    rm -f "$dst/$name"
  elif [ -e "$dst/$name" ]; then
    # Only the shebang may differ between the live copy and the repo copy;
    # anything else is a real local edit and gets preserved.
    body "$src/$name" >"$tmp/a"
    body "$dst/$name" >"$tmp/b"
    if cmp -s "$tmp/a" "$tmp/b"; then
      rm -f "$dst/$name"
    else
      mv "$dst/$name" "$dst/$name.pre-repo.$(date +%Y%m%d%H%M%S)"
      echo "kept the previous $name aside as $name.pre-repo.*"
    fi
  fi
  ln -s "$src/$name" "$dst/$name"
  chmod +x "$src/$name"
  echo "linked $dst/$name -> $src/$name"
done

"$dst/xerj-project" info >/dev/null
echo "ok: xerj-project resolves its project prefix"
