import argparse
from .common import DEFAULT_OUTPUT


def main():
    parser = argparse.ArgumentParser(description='Fixed S16T16 pion projection pilot')
    parser.add_argument('--output', default=str(DEFAULT_OUTPUT))
    commands = parser.add_subparsers(dest='command', required=True)
    measure = commands.add_parser('measure')
    measure.add_argument('--split', choices=['development', 'validation'], required=True)
    measure.add_argument('--limit', type=int)
    commands.add_parser('develop')
    commands.add_parser('evaluate')
    commands.add_parser('plot')
    candidate = commands.add_parser('candidate')
    candidate.add_argument('--definition', required=True)
    candidate.add_argument('--split', choices=['development', 'validation'], required=True)
    candidate.add_argument('--verify-only', action='store_true')
    agent = commands.add_parser('agent')
    agent.add_argument('--model', required=True)
    agent.add_argument('--space', choices=['paths', 'basis'], default='paths',
                       help='Design spatial transport paths (default) or tune the seven diffusion coefficients')
    agent.add_argument('--rounds', type=int, help='Default: one measured path proposal or four basis rounds')
    agent.add_argument('--feedback', choices=['round', 'batch'],
                       help='For paths: return development measurements each round (default) or collect all proposals first')
    agent.add_argument('--terminal', action='store_true', help='Read path proposals as JSON from stdin')
    agent.add_argument('--with-validation', action='store_true', help='Evaluate the selected LLM proposal on held-out data after search')
    validate = commands.add_parser('validate-selection', help='Evaluate a frozen path search winner without a new search')
    validate.add_argument('--session', required=True, help='Path to the completed agent/operators-* directory')
    report = commands.add_parser('report')
    report.add_argument('--model', required=True)
    axial = commands.add_parser('check-axial', help='Compare local PP and A4P on cached development propagators')
    axial.add_argument('--dest', required=True, help='New diagnostic output directory')
    ranking = commands.add_parser('diagnose-ranking')
    ranking.add_argument('--dest', required=True, help='New diagnostic output directory')
    compare = commands.add_parser('compare-search')
    compare.add_argument('--model', required=True)
    compare.add_argument('--dest', required=True, help='New comparison output directory')
    compare.add_argument('--seed', type=int, default=20261109)
    compare.add_argument('--terminal', action='store_true', help='Read one JSON model reply per round from stdin')
    synthetic = commands.add_parser('check-synthetic')
    synthetic.add_argument('--dest', required=True, help='New synthetic result directory')
    synthetic.add_argument('--seed', type=int, default=20261109)
    benchmark = commands.add_parser('benchmark-optimization', help='Paired synthetic held-out search benchmark')
    benchmark.add_argument('--dest', required=True, help='New result directory')
    benchmark.add_argument('--episodes', type=int, default=12)
    benchmark.add_argument('--seed', type=int, default=20261118)
    benchmark.add_argument('--replay', help='Evaluate four archived JSON replies as a fixed proposal set')
    benchmark.add_argument('--model', help='Include the API model with and without round feedback')
    args = parser.parse_args()
    if args.command == 'benchmark-optimization':
        from agents.optimization_benchmark import benchmark
        result = benchmark(args.dest, args.seed, args.episodes, args.model, replay=args.replay)
        for row in result['paired_test_risk']:
            print(row)
    elif args.command == 'check-axial':
        from .axial import check
        check(args.output, args.dest)
    elif args.command == 'check-synthetic':
        from .synthetic import run
        run(args.dest, args.seed)
    elif args.command == 'compare-search':
        from agents.comparison import compare
        compare(args.output, args.dest, args.model, args.seed, args.terminal)
    elif args.command == 'diagnose-ranking':
        from .ranking import diagnose
        diagnose(args.output, args.dest)
    elif args.command == 'agent':
        if args.space == 'paths':
            from agents.operator_search import run
            run(args.output, args.model, 1 if args.rounds is None else args.rounds,
                allow_validation=args.with_validation, terminal=args.terminal, feedback=args.feedback or 'round')
        else:
            if args.feedback:
                parser.error('--feedback requires --space paths')
            if args.terminal:
                parser.error('--terminal requires --space paths')
            from agents.loop import run
            run(args.output, args.model, 4 if args.rounds is None else args.rounds, allow_validation=args.with_validation)
    elif args.command == 'validate-selection':
        from agents.operator_search import validate_selection
        selection = validate_selection(args.session)
        print(selection.get('validation_result') or selection.get('validation_failure_reason') or 'No valid proposal')
    elif args.command == 'report':
        from agents.report import run
        run(args.output, args.model)
    elif args.command == 'measure':
        from .measure import measure
        measure(args.output, args.split, args.limit)
    elif args.command == 'candidate':
        from .candidate import run_candidate
        run_candidate(args.output, args.definition, args.split, args.verify_only)
    elif args.command == 'plot':
        from .plots import plot
        plot(args.output)
    else:
        from .experiment import develop, evaluate
        (develop if args.command == 'develop' else evaluate)(args.output)


if __name__ == '__main__':
    main()
