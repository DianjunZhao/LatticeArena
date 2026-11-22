"""Output-directory rules for Optimize runs.

Completed research outputs are immutable. A partial training run can be resumed
only when the caller opts in and the directory contains only reusable basis
cache files; their protocol/input identity is checked by ``load_basis``.
"""
from pathlib import Path


def prepare_output_directory(path, *, resume=False, allowed_existing=None):
    """Create a fresh run directory or validate an explicitly resumable one.

    ``allowed_existing`` receives each existing child Path and must return True
    only for files that the caller knows how to validate before reuse.
    """
    output = Path(path)
    if output.exists():
        if not resume:
            raise FileExistsError(
                f"refusing to reuse existing output directory {output}; choose a new run path"
            )
        if not output.is_dir():
            raise FileExistsError(f"resume target is not a directory: {output}")
        children = list(output.iterdir())
        if allowed_existing is None:
            raise FileExistsError(
                f"resume is not supported for {output}; existing contents are not validated"
            )
        unexpected = [child.name for child in children if not allowed_existing(child)]
        if unexpected:
            raise FileExistsError(
                f"refusing to overwrite non-resumable outputs in {output}: {unexpected}"
            )
        return output

    output.mkdir(parents=True, exist_ok=False)
    return output
