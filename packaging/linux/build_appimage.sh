#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

APP_NAME="docx-a11y"
VERSION="0.5.0"
DIST_DIR="${REPO_ROOT}/dist"
APP_DIR="${DIST_DIR}/AppDir"
OUT_DIR="${DIST_DIR}/linux"

mkdir -p "${OUT_DIR}"
rm -rf "${APP_DIR}"
mkdir -p "${APP_DIR}/usr/bin" \
         "${APP_DIR}/usr/share/applications" \
         "${APP_DIR}/usr/share/icons/hicolor/256x256/apps" \
         "${APP_DIR}/usr/lib"

echo "==> Building PyInstaller bundle..."
PYINSTALLER_BIN="${REPO_ROOT}/.venv/bin/pyinstaller"
if [ ! -x "${PYINSTALLER_BIN}" ]; then
  PYINSTALLER_BIN="$(command -v pyinstaller || true)"
fi
if [ -z "${PYINSTALLER_BIN}" ]; then
  echo "Error: pyinstaller executable not found."
  exit 1
fi

"${PYINSTALLER_BIN}" --noconfirm --clean "${REPO_ROOT}/packaging/specs/${APP_NAME}-gui.spec"

echo "==> Staging Linux AppDir files..."
cp -r "${DIST_DIR}/docx-a11y-gui"/* "${APP_DIR}/usr/bin/"

# Ensure main launcher AppRun script
cat << EOF > "${APP_DIR}/AppRun"
#!/bin/sh
SELF=\$(readlink -f "\$0")
HERE=\${SELF%/*}
export PATH="\${HERE}/usr/bin:\${PATH}"
export LD_LIBRARY_PATH="\${HERE}/usr/bin:\${LD_LIBRARY_PATH:-}"
exec "\${HERE}/usr/bin/${APP_NAME}" "\$@"
EOF
chmod +x "${APP_DIR}/AppRun"

# Copy icons
cp "${REPO_ROOT}/packaging/icons/docx-a11y.png" "${APP_DIR}/usr/share/icons/hicolor/256x256/apps/"
cp "${REPO_ROOT}/packaging/icons/docx-a11y.png" "${APP_DIR}/"

# Desktop entry
cat > "${APP_DIR}/docx-a11y.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Word Accessibility Auditor
Exec=docx-a11y
Icon=docx-a11y
Comment=Audit and remediate Microsoft Word .docx files against WCAG 2.1 AA
Categories=Office;Accessibility;Utility;
Terminal=false
EOF

cp "${APP_DIR}/docx-a11y.desktop" "${APP_DIR}/usr/share/applications/"

echo "==> Building Linux AppImage..."
if command -v appimagetool >/dev/null 2>&1; then
  export APPIMAGE_EXTRACT_AND_RUN=1
  appimagetool "${APP_DIR}" "${OUT_DIR}/${APP_NAME}-v${VERSION}-x86_64.AppImage"
  echo "==> AppImage built successfully: ${OUT_DIR}/${APP_NAME}-v${VERSION}-x86_64.AppImage"
else
  echo "Warning: appimagetool not found. AppDir staged at: ${APP_DIR}"
fi
