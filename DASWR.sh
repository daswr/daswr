python3 -m venv daswr-env
source daswr-env/bin/activate
pip3 install wheel
pip3 install pulsectl
pip3 install psutil  
pip3 install bleach
pip3 install python-libxdo 
pip3 install python-xlib
pip3 install pysciter
PATH="$PATH:$PWD/sciter/bin.lnx/x64" python3 GUI.py 
