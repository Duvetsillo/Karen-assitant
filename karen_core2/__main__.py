"""Explicit Core 2 CLI. Mutations require an interactive per-step decision."""
import argparse
import json

from .runtime import CoreRuntime


def main():
    parser = argparse.ArgumentParser(description='Karen Core 2 local')
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('status')
    sub.add_parser('models')
    sub.add_parser('plans')
    plan = sub.add_parser('plan'); plan.add_argument('goal')
    for action in ('run', 'resume', 'cancel', 'inspect', 'remember'):
        command = sub.add_parser(action); command.add_argument('id')
    vision = sub.add_parser('vision'); vision.add_argument('--scope', choices=('window', 'screen'), default='window'); vision.add_argument('--capture', action='store_true', required=True)
    args = parser.parse_args()
    runtime = CoreRuntime()
    def approve(request):
        print(json.dumps(request, ensure_ascii=False, indent=2))
        return input('Autoriza esta operación concreta escribiendo APROBAR: ') == 'APROBAR'
    if args.action == 'models': result = runtime.models.discover(force=True)
    elif args.action == 'status': result = runtime.status()
    elif args.action == 'plans': result = runtime.plans.list()
    elif args.action == 'plan': result = runtime.create_plan(args.goal)
    elif args.action == 'inspect': result = runtime.plans.inspect(args.id)
    elif args.action in {'run', 'resume'}: result = runtime.run(args.id, approve=approve, resume=args.action == 'resume')
    elif args.action == 'cancel': result = runtime.plans.cancel(args.id)
    elif args.action == 'remember': result = runtime.memory.record_procedure(runtime.plans.inspect(args.id))
    else:
        runtime.vision.pause(False)
        try: result = runtime.vision.analyze(scope=args.scope)
        finally: runtime.vision.pause()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
