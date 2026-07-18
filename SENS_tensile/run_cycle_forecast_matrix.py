#!/usr/bin/env python3
"""Dispatch the frozen 20-cell forecast matrix across declared producer GPUs."""
from __future__ import annotations

import argparse
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path

TRAIN_ENDS = (20, 40, 60, 67)
CONTEXTS = (1, 3, 5, 10)


def main(args):
    jobs = [("pointwise", c, 1) for c in TRAIN_ENDS]
    jobs += [("temporal_mesh", c, k) for c in TRAIN_ENDS for k in CONTEXTS]
    pending = queue.Queue()
    for job in jobs: pending.put(job)
    args.out.mkdir(parents=True, exist_ok=True)
    failures=[]; lock=threading.Lock()

    def worker(gpu):
        while True:
            try: model, train_end, context = pending.get_nowait()
            except queue.Empty: return
            tag=f"{model}_c{train_end}_k{context}"; out=args.out/tag; out.mkdir(parents=True,exist_ok=True)
            command=[sys.executable,"-u",str(Path(__file__).with_name("train_cycle_forecast_data_efficiency.py")),
                     "--dataset",str(args.dataset),"--out",str(out),"--model",model,
                     "--train-end",str(train_end),"--context",str(context),"--steps",str(args.steps),
                     "--seed",str(args.seed),"--device","cuda:0","--code-commit",args.code_commit]
            env=os.environ.copy(); env["CUDA_VISIBLE_DEVICES"]=str(gpu)
            with (out/"run.log").open("w",encoding="utf-8") as log:
                result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,env=env)
            if result.returncode:
                with lock: failures.append((tag,result.returncode))
            pending.task_done()

    threads=[threading.Thread(target=worker,args=(gpu,),daemon=False) for gpu in args.gpus]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    if failures: raise SystemExit(f"failed cells: {failures}")


if __name__ == "__main__":
    p=argparse.ArgumentParser(); p.add_argument("--dataset",type=Path,required=True); p.add_argument("--out",type=Path,required=True)
    p.add_argument("--gpus",type=lambda s:[int(x) for x in s.split(",")],required=True)
    p.add_argument("--steps",type=int,default=3000); p.add_argument("--seed",type=int,default=1); p.add_argument("--code-commit",required=True)
    main(p.parse_args())
