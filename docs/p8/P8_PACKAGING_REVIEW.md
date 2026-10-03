# P8 packaging review

The supported package is the Python source distribution/editable install on
Python 3.11+. CI runs `pip wheel --no-deps .`, creates a tagged `git archive`
source tarball, and performs a fresh install. A maintainer may additionally
run `python -m build` when the optional build tool is available.

The release workflow produces a wheel/sdist and SHA-256 checksums from a clean
tagged checkout. It never embeds credentials or a local database. The app's
user data lives outside source artifacts and survives ordinary source updates.

macOS Apple Silicon packaging is not selected for this source-only beta: no
signed/notarized artifact is present, so no binary download or Gatekeeper claim
is made. A future native target must add architecture, signing, notarization,
clean-install, and checksum evidence before being linked from finathink.cloud.
