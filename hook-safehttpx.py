"""
PyInstaller hook for safehttpx
Collects the version.txt file that safehttpx requires at runtime
"""
from PyInstaller.utils.hooks import get_package_paths
import os

# Get the safehttpx package paths
try:
    pkg_base, pkg_dir = get_package_paths('safehttpx')

    # Collect the version.txt file if it exists
    datas = []
    version_file = os.path.join(pkg_dir, 'version.txt')
    if os.path.exists(version_file):
        datas = [(version_file, 'safehttpx')]

    # Collect all data files from safehttpx
    from PyInstaller.utils.hooks import collect_data_files
    datas += collect_data_files('safehttpx')

except Exception:
    # Fallback: just try to collect data files
    from PyInstaller.utils.hooks import collect_data_files
    datas = collect_data_files('safehttpx')

# Hidden imports that safehttpx might need
hiddenimports = ['safehttpx', 'httpx', 'httpx._transports.default']
