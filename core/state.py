"""Explicit run state separate from the score (todo F3).

The score can be None; validation observation is permanent. Transitions follow
a small table so a validated claim cannot silently regress or skip a stage.
"""
STATES = ('operator', 'reference', 'numerical', 'statistical', 'comparison')
STATUS = ('not_run', 'draft', 'validated', 'failed')
ALLOWED = {('not_run', 'draft'), ('not_run', 'failed'), ('draft', 'validated'),
           ('draft', 'failed'), ('validated', 'failed')}


class RunState:
    def __init__(self):
        self.status = {name: 'not_run' for name in STATES}
        self.evidence = {name: [] for name in STATES}
        self.validation_observed = False
        self.score = None

    def set(self, name, status, evidence=None):
        if name not in STATES:
            raise ValueError(f'unknown state {name!r}')
        if status not in STATUS:
            raise ValueError(f'unknown status {status!r}')
        if (self.status[name], status) not in ALLOWED:
            raise ValueError(f'illegal transition {name}: {self.status[name]} -> {status}')
        self.status[name] = status
        if evidence:
            self.evidence[name].append(evidence)
        return self

    def observe_validation(self, reference='unknown'):
        """Permanent record; a second observation does not reset the leak flag."""
        self.validation_observed = True
        self.evidence['comparison'].append(f'validation_observed:{reference}')
        return self

    def score_or_null(self):
        """A score requires the statistical and comparison stages to be valid."""
        if self.status['statistical'] != 'validated' or self.status['comparison'] != 'validated':
            return None
        return self.score

    def summary(self):
        return {'status': dict(self.status), 'validation_observed': self.validation_observed,
                'score': self.score_or_null(), 'evidence': self.evidence}
