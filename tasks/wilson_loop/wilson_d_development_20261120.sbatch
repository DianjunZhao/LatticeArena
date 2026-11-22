#!/bin/bash
#SBATCH -J la_wilson_d_dev
#SBATCH -p kshdnormal
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 1
#SBATCH --gres=dcu:1
#SBATCH --mem=3G
#SBATCH -t 24:00:00
#SBATCH -o /public/home/acwzoxdwvj/dianjun/LatticeArena/runs/wilson_production_d_20261120/logs/wilson_d_development_%j.out
#SBATCH -e /public/home/acwzoxdwvj/dianjun/LatticeArena/runs/wilson_production_d_20261120/logs/wilson_d_development_%j.err
set -euo pipefail
source /public/home/acwzoxdwvj/env_pyquda_conda.sh
ROOT=/public/home/acwzoxdwvj/dianjun/LatticeArena/runs/wilson_production_d_20261120
cd "$ROOT"
export PYTHONPATH="$ROOT"
export WILSON_PROTOCOL="$ROOT/tasks/wilson_loop/protocol_d_20261120.json"
export OMP_NUM_THREADS=1
export MPLBACKEND=Agg
python -m tasks.wilson_loop --output results/wilson_loop/s16t16d_development_20261120 measure --split development
