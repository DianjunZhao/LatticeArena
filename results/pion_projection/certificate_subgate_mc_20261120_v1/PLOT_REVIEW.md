# Figure review: Pion chi-square subgate MC

The frozen simulation and statistics are unchanged. The original plot is preserved as the preregistered artifact. Its x-axis labels were too long to read clearly, so this supplemental figure uses shortened scenario labels and separates null rejection, misspecification sensitivity, and pure-E1 acceptance.

![Readable subgate diagnostic](subgate_calibration_diagnostic_review.png)

The right panel highlights the structural limit: a pure-E1 dataset can increasingly pass a single-cosh fit as the number of blocks grows. This fit-quality subgate does not identify the state as the ground state.

The figure is reproduced with `python -B -m tasks.pion_projection.certificate_subgate_plot_review`. Input and output hashes are in `plot_review_provenance.json`.
