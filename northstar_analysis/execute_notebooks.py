"""Execute selected deliverable notebooks with a fresh kernel and fail on cell errors."""
from pathlib import Path
import os
import argparse
import sys
import tempfile
import nbformat
from nbclient import NotebookClient
from jupyter_client.kernelspec import KernelSpecManager

root = Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--notebook',action='append',choices=['01_analysis_and_solution.ipynb','02_monitoring.ipynb','03_learning_early_warning.ipynb'],help='Run only this notebook; may be repeated')
args=parser.parse_args()
names=args.notebook or ['01_analysis_and_solution.ipynb','02_monitoring.ipynb','03_learning_early_warning.ipynb']
# Temporary kernelspec uses this interpreter; no global/user Jupyter installation needed.
with tempfile.TemporaryDirectory(prefix='northstar-kernel-') as tmp:
    import json
    spec = Path(tmp) / 'northstar'
    spec.mkdir()
    (spec/'kernel.json').write_text(json.dumps({'argv':[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],
        'display_name':'Northstar analysis','language':'python'}))
    os.environ.setdefault('IPYTHONDIR',str(Path(tmp)/'ipython'))
    manager = KernelSpecManager(kernel_dirs=[tmp])
    from jupyter_client import KernelManager
    for name in names:
        nb = nbformat.read(root/name,as_version=4)
        km = KernelManager(kernel_name='northstar',kernel_spec_manager=manager)
        try:
            NotebookClient(nb,timeout=180,km=km,resources={'metadata':{'path':str(root)}}).execute()
        finally:
            nbformat.write(nb,root/name)
        assert not any(o.output_type=='error' for c in nb.cells if c.cell_type=='code' for o in c.outputs)
        print('Executed successfully:', name, flush=True)
