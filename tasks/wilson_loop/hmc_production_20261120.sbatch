#!/bin/bash
#SBATCH -J la_chain_20261120
#SBATCH -p kshdnormal
#SBATCH -N 1
#SBATCH -n 1
#SBATCH --gres=dcu:1
#SBATCH -t 03:00:00
#SBATCH -o /public/home/acwzoxdwvj/dianjun/LatticeArena/runs/task_closure_20261120/logs/hmc_%j.out
#SBATCH -e /public/home/acwzoxdwvj/dianjun/LatticeArena/runs/task_closure_20261120/logs/hmc_%j.err
set -euo pipefail
source /public/home/acwzoxdwvj/env_pyquda_conda.sh
cd /public/home/acwzoxdwvj/dianjun/LatticeArena/runs/task_closure_20261120
export OMP_NUM_THREADS=1
export PYTHONUNBUFFERED=1
python -m tasks.wilson_loop.hmc_production --protocol tasks/wilson_loop/hmc_chain_20261120.json
