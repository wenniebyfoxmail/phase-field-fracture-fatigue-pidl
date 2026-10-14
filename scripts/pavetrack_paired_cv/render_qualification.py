#!/usr/bin/env python3
"""Post-run caption clarification: cyan is emitted output,possibly original."""
import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('frozen_qualification_plotter',Path(__file__).with_name('qualification_analysis.py'));q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
original=q.plt.Figure.suptitle
def caption(self,text,*args,**kwargs):return original(self,text.replace('cyan correction','cyan emitted'),*args,**kwargs)
q.plt.Figure.suptitle=caption
q.main()
