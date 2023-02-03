import sys
import subprocess
import os

home_directory = os.path.expanduser( '~' )

# implement pip as a subprocess:
subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-e'
f'{home_directory}/src/snspd-measure/'])

subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-e'
f'{home_directory}/src/snspd-core/'])

subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-e'
f'{home_directory}/src/snspd-analyze/'])