"""Design a spatial pion sink and measure each proposal using the frozen point source."""
import fcntl
import json
import tempfile
from pathlib import Path
from time import monotonic

from agents.llm import chat
from core.io import digest, fingerprint, write_json
from tasks.pion_projection import candidate, experiment, path_kernel, statistics
from tasks.pion_projection.candidate import CandidateRejected, run_candidate
from tasks.pion_projection.path_kernel import expand_paths

BUILDER = 'tasks.pion_projection.path_kernel:build_kernel'
PROMPT = """Design a zero-momentum pseudoscalar sink operator for a fixed point-source pion two-point function.
Return JSON {"terms": [...]} with a "path" (list of steps) and "weight" for each term.
Invent the support, lengths, bends, ordering and weights. Each signed step ±1, ±2, ±3 is x,y,z.
Parallel transport uses the actual links on this timeslice. Each weight multiplies the cubic/parity
orbit average. Hermitian and neutral-partner C-even projection fix pion G=-1. The empty path is identity.
Signed real weights survive this projection. A [real,imaginary] seed contributes its real part. An overall nonzero scale cancels from the loss.
For each proposal we measure C(t)=sum S(t)^dagger K S(t) on the development configurations.
Lower risk is better: average of Var_boot(q) + (q-1)^2 over the early window,
q=C/(A*f0) with development reference mass and fitted late amplitude.
Propose one operator. Each reply uses one attempt, including duplicates and invalid proposals.
"""


def terminal_proposal(prompt, model):
    print(prompt, flush=True)
    return input(f'{model} JSON reply> ')


def evaluator_hashes():
    return {m.__name__: digest(m.__file__) for m in (candidate, experiment, statistics, path_kernel)}


def operator_replies(session, propose, context, model, source, rounds, feedback, history):
    prior_replies = []
    for i in range(1, rounds + 1):
        visible = {'development': context, 'attempt': i, 'attempt_budget': rounds,
                   'feedback': feedback}
        if feedback == 'round':
            visible['history'] = history
        else:
            visible['previous_replies'] = prior_replies
        prompt = PROMPT + json.dumps(visible)
        reply = propose(prompt, model)
        folder = session / f'round-{i}'
        folder.mkdir()
        write_json(folder / 'exchange.json', {'model': model, 'source': source, 'prompt': prompt, 'reply': reply})
        if feedback == 'batch':
            prior_replies.append(reply)
        yield i, folder, reply


def run(output, model, rounds=1, allow_validation=False, *, terminal=False, feedback='round'):
    if rounds < 1:
        raise ValueError('rounds must be positive')
    if feedback not in ('round', 'batch'):
        raise ValueError('feedback must be round or batch')
    output = Path(output)
    frozen = json.loads((output / 'submission.json').read_text())
    protocol = json.loads((output / 'development_provenance.json').read_text())['protocol']
    development = json.loads((output / 'development_results.json').read_text())
    context = {'geometry': protocol['geometry'], 'score_window': protocol['score_window'],
               'reference': frozen['calibration']['reference'], 'reference_passed': frozen['calibration']['reference_passed'],
               'basis': [{'power': n, 'risk': v['risk'], 'q': v['q']} for n, v in
                         zip(protocol['powers'], development['basis'])],
               'slsqp_risk': development['agent']['risk']}
    context['resource_limits'] = {k: protocol[k] for k in ('wall_seconds_per_configuration', 'gpu_memory_limit_gib')}
    root = output / 'agent'
    root.mkdir(exist_ok=True)
    session = Path(tempfile.mkdtemp(prefix='operators-', dir=root))
    history = []
    seen = set()
    best = None
    propose = terminal_proposal if terminal else chat
    source = 'terminal' if terminal else 'api'
    conditions = {
        'proposal_budget': rounds, 'development_provenance': digest(output / 'development_provenance.json'),
        'reference_submission': digest(output / 'submission.json'), 'initial_context': fingerprint(context),
        'implementation': evaluator_hashes(),
        'search_implementation': digest(__file__),
    }
    write_json(session / 'search_protocol.json', {'conditions': conditions, 'conditions_hash': fingerprint(conditions),
               'feedback': feedback, 'model': model, 'source': source})
    replies = operator_replies(session, propose, context, model, source, rounds, feedback, history)
    if feedback == 'batch':
        # Commit every reply before invoking even the first development measurement.
        replies = list(replies)
    for i, folder, reply in replies:
        record = {'round': i, 'development_measurement_attempted': False}
        try:
            params = json.loads(reply)
            coefficients = expand_paths(params)
            identity = tuple(sorted(coefficients.items()))
            if identity in seen:
                raise ValueError('Repeated projected operator')
            seen.add(identity)
        except (ValueError, TypeError, OverflowError) as exc:
            record['rejected'] = str(exc)
        else:
            record['terms'] = params['terms']
            definition = {'builder': BUILDER, 'parameters': params}
            path = folder / 'definition.json'
            write_json(path, definition)
            record['development_measurement_attempted'] = True
            start = monotonic()
            try:
                destination = run_candidate(output, path, 'development', candidate_root=session / 'measurements')
            except CandidateRejected as exc:
                record['rejected'] = str(exc)
            else:
                measured = json.loads((destination / 'frozen.json').read_text())['development_diagnostic']
                record.update({key: measured[key] for key in ('risk', 'variance', 'departure_squared', 'q', 'mean', 'se')})
                record['measurement'] = str(destination.relative_to(session))
                if best is None or record['risk'] < best['risk']:
                    best = dict(record, definition=str(path.relative_to(session)), definition_hash=fingerprint(definition))
            finally:
                record['development_evaluator_seconds'] = monotonic() - start
        record['best_development_risk'] = best['risk'] if best is not None else None
        history.append(record)
        write_json(session / 'history.json', history)
    first = next((r for r in history if 'risk' in r), None)
    selection = {'model': model, 'rounds': rounds, 'best': best, 'validation_status': 'not_read',
                 'feedback': feedback, 'conditions_hash': fingerprint(conditions),
                 'attempts': len(history), 'valid_proposals': sum('risk' in r for r in history),
                 'development_measurement_attempts': sum(r['development_measurement_attempted'] for r in history),
                 'development_evaluator_seconds': sum(r.get('development_evaluator_seconds', 0.) for r in history),
                 'first_valid_round': first['round'] if first else None,
                 'first_valid_risk': first['risk'] if first else None,
                 'best_development_risk_by_attempt': [r['best_development_risk'] for r in history]}
    write_json(session / 'selection.json', selection)
    if allow_validation and best:
        selection = validate_selection(session)
    print(session, flush=True)
    return selection


def validate_selection(session):
    """Measure the already-selected winner, including when search and validation run separately."""
    session = Path(session)
    output = session.parent.parent
    evaluation = session / 'evaluation.json'
    with (session / 'selection.json').open() as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        selection = json.load(f)
        if evaluation.exists():
            return json.loads(evaluation.read_text())
        best = selection['best']
        if best is None:
            return selection
        if 'conditions_hash' in selection:
            conditions = json.loads((session / 'search_protocol.json').read_text())['conditions']
            if (selection['conditions_hash'] != fingerprint(conditions)
                    or conditions['implementation'] != evaluator_hashes()
                    or conditions['reference_submission'] != digest(output / 'submission.json')
                    or conditions['development_provenance'] != digest(output / 'development_provenance.json')):
                raise ValueError('Frozen search conditions changed')
        path = session / best['definition']
        if fingerprint(json.loads(path.read_text())) != best['definition_hash']:
            raise ValueError('Selected operator changed')
        try:
            destination = run_candidate(output, path, 'validation', candidate_root=session / 'measurements')
        except CandidateRejected as exc:
            selection.update(validation_status='rejected', validation_failure_reason=str(exc))
        else:
            selection.update(validation_status='measured', validation_result=str((destination / 'results.json').relative_to(session)))
        write_json(session / 'evaluation.json', selection)
    return selection
