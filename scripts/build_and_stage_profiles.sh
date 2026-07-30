#!/usr/bin/env bash
#
# Build every shipping profile into a WLED checkout and stage its output as
# release assets.
#
# Used by both release.yml and build.yml: the rehearsal on a pull request and
# the real release run the same code, so the only thing that differs on release
# day is the version string.
#
# Profiles are staged one at a time -- each writes platformio_override.ini into
# the WLED checkout, so the next iteration overwrites it. Everything that reads
# a profile's build configuration therefore has to happen inside the loop.

set -euo pipefail

repo_root="${1:?repository root}"
wled_dir="${2:?WLED checkout}"
release_version="${3:?release version}"
wled_ref="${4:?WLED ref}"
dist_dir="${5:?dist directory}"

cd "$repo_root"
mkdir -p "$dist_dir"
# Outside dist/ on purpose: everything in there is published.
: > built_envs.txt

# Single source of truth: SHIPPING_PROFILE_FILENAMES in
# scripts/release_profiles.py (via iter_shipping_profiles, which also validates
# each file exists). Keep this in sync by editing that tuple only -- do NOT
# hard-code the profile list here.
mapfile -t profiles < <(
  python -c "from pathlib import Path; from scripts.release_profiles import iter_shipping_profiles; [print('build_profiles/' + p.name) for p in iter_shipping_profiles(Path('build_profiles'))]"
)
if [ "${#profiles[@]}" -eq 0 ]; then
  echo "No shipping profiles resolved from SHIPPING_PROFILE_FILENAMES"
  exit 1
fi
printf 'Shipping profiles to build:\n'; printf '  %s\n' "${profiles[@]}"

for profile in "${profiles[@]}"; do
  echo "::group::$profile"

  mapfile -t envs < <(
    python scripts/stage_wled_profile.py stage-profile \
      --repo-root "$repo_root" \
      --wled-dir "$wled_dir" \
      --profile "$repo_root/$profile"
  )

  if [ "${#envs[@]}" -eq 0 ]; then
    echo "Profile $profile did not expose any envs"
    exit 1
  fi

  args=()
  for env_name in "${envs[@]}"; do
    echo "$env_name" >> built_envs.txt
    args+=("-e" "$env_name")
  done

  # Before the build, not after: `project metadata` cleans the build directory,
  # so collecting it afterwards deletes the very firmware.bin about to be
  # staged. Everything it reports is derived from the configuration -- the
  # offsets, and paths like $BUILD_DIR/bootloader.bin -- so the files it names
  # do not have to exist yet.
  python -m platformio project metadata \
    --project-dir "$wled_dir" \
    "${args[@]}" \
    --json-output-path "$repo_root/metadata.json"

  python -m platformio run --project-dir "$wled_dir" "${args[@]}"

  python scripts/stage_wled_profile.py stage-assets \
    --profile "$repo_root/$profile" \
    --build-root "$wled_dir/.pio/build" \
    --dist-dir "$dist_dir" \
    --release-version "$release_version" \
    --wled-ref "$wled_ref" \
    --metadata "$repo_root/metadata.json"

  echo "::endgroup::"
done

python scripts/stage_wled_profile.py finalize \
  --dist-dir "$dist_dir" \
  --release-version "$release_version" \
  --wled-ref "$wled_ref"
