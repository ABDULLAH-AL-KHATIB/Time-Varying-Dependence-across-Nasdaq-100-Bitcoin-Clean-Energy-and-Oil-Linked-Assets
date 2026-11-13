#!/usr/bin/env python3
"""Install the exact core research repositories recorded in the run manifest."""
from pathlib import Path
import subprocess, sys
ROOT=Path(__file__).resolve().parents[1]
VENDOR=ROOT/'vendor';VENDOR.mkdir(exist_ok=True)
REPOS={
 'QVAR':('https://github.com/merwanroudane/QVAR.git','926f660c501eb1d2a1b29e2dc4ab15705cc8a87b'),
 'hybridmetrics':('https://github.com/merwanroudane/hybridmetrics.git','2fc7e314619d3d439cdd38c20f9fc32ebb59533c'),
}
for name,(url,commit) in REPOS.items():
 p=VENDOR/name
 if not p.exists(): subprocess.check_call(['git','clone',url,str(p)])
 subprocess.check_call(['git','-C',str(p),'fetch','origin',commit])
 subprocess.check_call(['git','-C',str(p),'checkout','--detach',commit])
 subprocess.check_call([sys.executable,'-m','pip','install','-e',str(p)])
subprocess.check_call([sys.executable,'-m','pip','install','dscc==0.1.1'])
print('Core repositories installed at pinned commits/versions.')
