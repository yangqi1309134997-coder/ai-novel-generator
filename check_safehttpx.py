import safehttpx
import os
print('safehttpx path:', os.path.dirname(safehttpx.__file__))
version_file = os.path.join(os.path.dirname(safehttpx.__file__), 'version.txt')
print('version.txt exists:', os.path.exists(version_file))
if os.path.exists(version_file):
    with open(version_file) as f:
        print('version content:', f.read())
