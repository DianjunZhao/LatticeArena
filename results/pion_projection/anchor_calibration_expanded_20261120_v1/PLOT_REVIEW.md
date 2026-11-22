# Plot finalization review

The preregistered dataset calculations completed for all 1,200 planned datasets, but the original run stopped during figure creation because the installed Matplotlib version no longer accepts `labels=` in `Axes.boxplot`. The figure and README were re-rendered from the unchanged raw and summary JSON using `tick_labels=`. No dataset calculation or result value was changed. Hashes and the repair record are in `plot_review_provenance.json`.
