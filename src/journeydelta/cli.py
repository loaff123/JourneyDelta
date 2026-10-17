import argparse
import json
import sys
from pathlib import Path
from .app import run_comparison,run_inspection
from .models import Limits
from .output import write_reports,write_inspection
from .render import render_reports
from .report import primitive

def _main(argv=None):
    parser=argparse.ArgumentParser(prog='journeydelta',description='Offline single-boarding GTFS contracts. Multi-leg journeys are not evaluated.')
    parser.add_argument('--version',action='version',version='JourneyDelta 0.1.0a1')
    sub=parser.add_subparsers(dest='command',required=True)
    inspect=sub.add_parser('inspect');inspect.add_argument('feed',type=Path);inspect.add_argument('--json',type=Path);inspect.add_argument('--overwrite',action='store_true')
    compare=sub.add_parser('compare');compare.add_argument('before',type=Path);compare.add_argument('after',type=Path);compare.add_argument('--suite',type=Path,required=True);compare.add_argument('--out',type=Path,required=True);compare.add_argument('--overwrite',action='store_true')
    args=parser.parse_args(argv)
    if args.command=='inspect':
        report=run_inspection(args.feed,Limits());content=(json.dumps(primitive(report.data),ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
        if args.json:
            written=write_inspection(content,args.json,args.overwrite,(args.feed,))
            if written.has_errors: print(written.diagnostics[0].message,file=sys.stderr);return 3
        else: print(content.decode(),end='')
        return report.exit_code
    report=run_comparison(args.before,args.after,args.suite,Limits())
    written=write_reports(render_reports(report),args.out,args.overwrite,(args.before,args.after,args.suite))
    if written.has_errors: print(written.diagnostics[0].message,file=sys.stderr);return 3
    print(f'{report.data["status"]}; exit {report.exit_code}; reports: {args.out}')
    return report.exit_code


def main(argv=None):
    try:
        return _main(argv)
    except Exception as exc:
        code='resource_limit' if isinstance(exc,MemoryError) else 'internal_error'
        try:
            print(f'{code}: {type(exc).__name__} while executing command; no success is reported',file=sys.stderr)
        except (OSError,MemoryError):
            pass
        return 3
