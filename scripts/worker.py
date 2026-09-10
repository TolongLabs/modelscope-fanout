#!/usr/bin/env python3
"""Bounded headless Claude Code dispatch through a local ModelScope proxy route."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import urllib.request

import yaml


def routing(config):
    providers = config.get('openai-compatibility', [])
    matches = [p for p in providers if p.get('name') == 'modelscope']
    if len(matches) != 1:
        raise ValueError('Configure exactly one modelscope provider.')
    provider = matches[0]
    if provider.get('base-url', '').rstrip('/') != 'https://api-inference.modelscope.ai/v1':
        raise ValueError('ModelScope upstream must be https://api-inference.modelscope.ai/v1.')
    aliases = {}
    for model in provider.get('models', []):
        alias, name = model.get('alias'), model.get('name')
        if not isinstance(alias, str) or not alias or not isinstance(name, str) or not name:
            raise ValueError('Each ModelScope model needs a name and a unique alias.')
        if alias in aliases:
            raise ValueError('Duplicate ModelScope alias.')
        aliases[alias] = name
    if not aliases:
        raise ValueError('No ModelScope aliases configured.')
    for other in providers:
        if other is not provider:
            for model in other.get('models', []):
                if model.get('alias') in aliases or model.get('name') in aliases:
                    raise ValueError('ModelScope alias collides with another provider.')
    keys = config.get('api-keys', [])
    if not isinstance(keys, list) or not keys or not isinstance(keys[0], str) or not keys[0]:
        raise ValueError('A local proxy API token is required.')
    port = config.get('port', 8317)
    if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
        raise ValueError('Invalid proxy port.')
    return port, keys[0], aliases


def environment(inherited, config_dir, port, token, model):
    env = {k: v for k, v in inherited.items()
           if not k.startswith(('ANTHROPIC_', 'CLAUDE_', 'CLIPROXY_', 'OPENAI_', 'OPENROUTER_', 'MODELSCOPE_'))
           and k != 'CLAUDECODE'}
    env.update(CLAUDE_CONFIG_DIR=config_dir,
               ANTHROPIC_BASE_URL=f'http://127.0.0.1:{port}',
               ANTHROPIC_AUTH_TOKEN=token,
               ANTHROPIC_MODEL=model,
               ANTHROPIC_DEFAULT_HAIKU_MODEL=model,
               ANTHROPIC_DEFAULT_SONNET_MODEL=model,
               ANTHROPIC_DEFAULT_OPUS_MODEL=model,
               CLAUDE_CODE_SUBAGENT_MODEL=model,
               CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC='1')
    return env


def success(result):
    return (isinstance(result, dict) and result.get('type') == 'result'
            and result.get('subtype') == 'success' and not result.get('is_error')
            and not result.get('permission_denials'))


def positive(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError('Must be positive.')
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=Path.home() / '.cli-proxy-api/config.yaml')
    parser.add_argument('--list', action='store_true', help='Validate and list live ModelScope aliases; no inference')
    parser.add_argument('--model', default='ms-qwen3.5-122b')
    parser.add_argument('--cwd', type=Path)
    parser.add_argument('--brief', type=Path)
    parser.add_argument('--log', type=Path, help='New JSON output path; stderr stored alongside')
    parser.add_argument('--max-turns', type=positive, default=8, help='Turn limit, NOT an upstream billing cap')
    parser.add_argument('--timeout', type=positive, default=600)
    parser.add_argument('--analysis', action='store_true', help='No tools; answer from the supplied brief only')
    args = parser.parse_args()
    try:
        config = yaml.safe_load(args.config.read_text())
        port, token, aliases = routing(config)
    except (OSError, ValueError, TypeError, AttributeError, yaml.YAMLError):
        parser.exit(2, 'Invalid or unreadable proxy config; check ModelScope routing, aliases and local auth. Config withheld.\n')
    try:
        request = urllib.request.Request(f'http://127.0.0.1:{port}/v1/models', headers={'Authorization': f'Bearer {token}'})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=10) as response:
            live = json.load(response)['data']
        live_aliases = {m['id'] for m in live if m.get('owned_by', '').lower() == 'modelscope'}
        available = aliases.keys() & live_aliases
    except Exception:
        parser.exit(2, 'Cannot verify live ModelScope routes. Start/check CLIProxyAPI; no worker launched.\n')
    if args.list:
        for alias in sorted(available):
            print(f'{alias}\t{aliases[alias]}')
        return 0 if available else 2
    if args.model not in available:
        parser.exit(2, 'Selected alias is not a live ModelScope route; no fallback.\n')
    if not args.cwd or not args.cwd.is_dir() or not args.brief or not args.brief.is_file() or not args.log:
        parser.error('--cwd directory, --brief file and --log are required.')
    config_dir = Path.home() / '.modelscope-fanout'
    config_dir.mkdir(mode=0o700, exist_ok=True)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    env = environment(os.environ, str(config_dir), port, token, args.model)
    command = ['claude', '-p', '--model', args.model, '--setting-sources', '',
               '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
               '--settings', '{"disableAllHooks":true}',
               '--tools', '' if args.analysis else 'Read,Edit,Write,Glob,Grep',
               '--permission-mode', 'default' if args.analysis else 'acceptEdits',
               '--max-turns', str(args.max_turns), '--output-format', 'json', '--no-session-persistence']
    # Never put auth in argv, or mix diagnostic output with the result JSON.
    os.umask(0o077)
    try:
        with args.log.open('x') as out, Path(str(args.log) + '.stderr').open('x') as err:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=out, stderr=err,
                                       text=True, cwd=args.cwd.resolve(), env=env, start_new_session=True)
            try:
                brief = (f'Your working directory is {args.cwd.resolve()}. Resolve all relative output paths '
                         'inside that directory. Never guess a home-directory path.\n\n' + args.brief.read_text())
                process.communicate(brief, timeout=args.timeout)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                print('Worker timed out; review partial files. No automatic retry.', file=sys.stderr)
                return 124
    except (OSError, UnicodeError):
        print('Cannot launch worker or create new logs; existing logs are never overwritten.', file=sys.stderr)
        return 2
    if process.returncode:
        print(f'Worker exit={process.returncode}; inspect private stderr. No automatic retry.', file=sys.stderr)
        return process.returncode if process.returncode > 0 else 1
    try:
        result = json.loads(args.log.read_text())
    except (ValueError, OSError):
        print('Missing or invalid worker JSON; inspect private logs.', file=sys.stderr)
        return 1
    if not success(result):
        print('Worker reported an error or permission denial; review partial output.', file=sys.stderr)
        return 1
    print(f'Model={args.model} turns={result.get("num_turns", "unknown")} status=success; verify files. Magicubes=unmeasured')
    return 0


if __name__ == '__main__':
    sys.exit(main())
