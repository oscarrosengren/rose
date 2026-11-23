"""Offline tests for rose using fake `claude` and `codex` executables.

Run: python3 -I test_rose.py
No real login, model request or network access happens.
"""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest

ROSE = str(Path(__file__).resolve().parent / 'rose')

FAKE_CLAUDE = r'''#!/usr/bin/env python3
import json, os, re, sys, time, uuid, datetime as dt
home = os.environ['CLAUDE_CONFIG_DIR']; name = os.path.basename(home)
args = sys.argv[1:]
with open(os.environ['FAKE_LOG'], 'a') as f:
    f.write(json.dumps({'tool': 'claude', 'account': name, 'args': args,
                        'api_key': os.environ.get('ANTHROPIC_API_KEY')}) + '\n')
if args[:2] == ['auth', 'status']:
    ok = os.path.exists(os.path.join(home, '.credentials.json'))
    print(json.dumps({'loggedIn': ok, 'authMethod': 'claude.ai'})); sys.exit(0)
if args[:2] == ['auth', 'login']:
    open(os.path.join(home, '.credentials.json'), 'w').write('{}'); sys.exit(0)
sid = None
if '--session-id' in args: sid = args[args.index('--session-id') + 1]
if '--resume' in args: sid = args[args.index('--resume') + 1]
sid = sid or str(uuid.uuid4())
cwd = os.getcwd()
d = os.path.join(home, 'projects', re.sub(r'[^A-Za-z0-9]', '-', cwd)); os.makedirs(d, exist_ok=True)
now = lambda: dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00', 'Z')
prompt = args[-1] if args and not args[-1].startswith('-') and args[-1] != sid else 'hello from ' + name
with open(os.path.join(d, sid + '.jsonl'), 'a') as f:
    f.write(json.dumps({'type': 'user', 'cwd': cwd, 'sessionId': sid, 'timestamp': now(),
                        'message': {'role': 'user', 'content': prompt}}) + '\n')
    if name in os.environ.get('FAKE_LIMITED', '').split(','):
        f.write(json.dumps({'type': 'assistant', 'isApiErrorMessage': True, 'apiError': 'usage_limit_reached',
                            'error': 'rate_limit', 'timestamp': now(), 'cwd': cwd,
                            'apiErrorParams': {'rate_limit_info': {'resetsAt': int(time.time()) + 3600,
                                                                   'rateLimitType': 'five_hour'}},
                            'message': {'role': 'assistant', 'content': [{'type': 'text', 'text': "You've hit your limit"}]}}) + '\n')
        f.flush()
        if os.environ.get('FAKE_HANG'): time.sleep(30)   # a TUI stays open after the error
    else:
        f.write(json.dumps({'type': 'assistant', 'timestamp': now(), 'cwd': cwd,
                            'message': {'role': 'assistant', 'content': [{'type': 'text', 'text': 'ok'}]}}) + '\n')
'''

FAKE_CODEX = r'''#!/usr/bin/env python3
import json, os, sys, time, uuid, datetime as dt
home = os.environ['CODEX_HOME']; name = os.path.basename(home)
args = sys.argv[1:]
with open(os.environ['FAKE_LOG'], 'a') as f:
    f.write(json.dumps({'tool': 'codex', 'account': name, 'args': args,
                        'api_key': os.environ.get('OPENAI_API_KEY')}) + '\n')
if args[:2] == ['login', 'status']:
    ok = os.path.exists(os.path.join(home, 'auth.json')); print('Logged in' if ok else 'Not logged in'); sys.exit(0 if ok else 1)
if args[:1] == ['login']:
    open(os.path.join(home, 'auth.json'), 'w').write('{}'); sys.exit(0)
now = lambda: dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00', 'Z')
if args[:1] == ['resume']:
    sid = [a for a in args[1:] if not a.startswith('-')][0]
    path = [os.path.join(r, f) for r, _, fs in os.walk(os.path.join(home, 'sessions')) for f in fs if sid in f][0]
else:
    sid = str(uuid.uuid4()); d = os.path.join(home, 'sessions', '2026', '11', '23'); os.makedirs(d, exist_ok=True)
    path = os.path.join(d, 'rollout-2026-11-23T10-00-00-' + sid + '.jsonl')
    with open(path, 'w') as f:
        f.write(json.dumps({'type': 'session_meta', 'timestamp': now(), 'payload': {'id': sid, 'cwd': os.getcwd()}}) + '\n')
with open(path, 'a') as f:
    f.write(json.dumps({'type': 'event_msg', 'timestamp': now(), 'payload': {'type': 'user_message', 'message': 'task for ' + name}}) + '\n')
    if name in os.environ.get('FAKE_LIMITED', '').split(','):
        f.write(json.dumps({'type': 'event_msg', 'timestamp': now(), 'payload': {
            'type': 'error', 'message': "You've hit your usage limit.", 'codex_error_info': 'usage_limit_exceeded'}}) + '\n')
        f.flush()
        if os.environ.get('FAKE_HANG'): time.sleep(30)
    else:
        f.write(json.dumps({'type': 'event_msg', 'timestamp': now(), 'payload': {'type': 'agent_message', 'message': 'ok'}}) + '\n')
'''


class RoseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='rose-test-'))
        bin_dir = self.tmp / 'bin'
        bin_dir.mkdir()
        for n, src in (('claude', FAKE_CLAUDE), ('codex', FAKE_CODEX)):
            (bin_dir / n).write_text(src)
            (bin_dir / n).chmod(0o755)
        self.shared_claude = self.tmp / 'dot-claude'
        self.shared_codex = self.tmp / 'dot-codex'
        (self.shared_claude / 'skills').mkdir(parents=True)
        (self.shared_claude / 'settings.json').write_text('{"env": {"ANTHROPIC_API_KEY": "sk-shared"}}')
        (self.shared_claude / '.credentials.json').write_text('{"secret": 1}')
        self.shared_codex.mkdir()
        (self.shared_codex / 'config.toml').write_text('model = "x"\n')
        (self.shared_codex / 'auth.json').write_text('{"secret": 1}')
        self.project = self.tmp / 'project'
        self.project.mkdir()
        self.log = self.tmp / 'calls.jsonl'
        self.env = dict(os.environ, ROSE_HOME=str(self.tmp / 'rose'), PATH=f'{bin_dir}:{os.environ["PATH"]}',
                        ROSE_CLAUDE_SHARED=str(self.shared_claude), ROSE_CODEX_SHARED=str(self.shared_codex),
                        FAKE_LOG=str(self.log), ANTHROPIC_API_KEY='sk-ambient', OPENAI_API_KEY='sk-openai')
        for v in ('CLAUDE_CONFIG_DIR', 'CODEX_HOME', 'FAKE_LIMITED', 'FAKE_HANG'):
            self.env.pop(v, None)
        for spec in ('claude work', 'claude personal', 'codex main', 'codex spare'):
            self.rose(*'add {} --no-login'.format(spec).split())
            self.rose('login', *spec.split())

    def rose(self, *args, check=True, env=None, cwd=None, input=None):
        r = subprocess.run([sys.executable, ROSE, *args], env=dict(self.env, **(env or {})), cwd=cwd or self.project,
                           capture_output=True, text=True, timeout=60,
                           **({'input': input} if input is not None else {'stdin': subprocess.DEVNULL}))
        if check and r.returncode != 0:
            self.fail(f'rose {args} failed ({r.returncode}):\n{r.stdout}\n{r.stderr}')
        return r

    def calls(self):
        return [json.loads(x) for x in self.log.read_text().splitlines()] if self.log.exists() else []

    def home(self, tool, name):
        return self.tmp / 'rose' / 'accounts' / tool / name

    def test_shared_config_but_private_credentials(self):
        h = self.home('claude', 'work')
        self.assertTrue((h / 'settings.json').is_symlink())
        self.assertTrue((h / 'skills').is_symlink())
        self.assertFalse((h / '.credentials.json').is_symlink())
        self.assertTrue((self.home('codex', 'main') / 'config.toml').is_symlink())
        self.assertFalse((self.home('codex', 'main') / 'auth.json').is_symlink())

    def test_status_warns_about_shared_api_key(self):
        out = self.rose('status').stdout
        self.assertIn('ANTHROPIC_API_KEY', out)
        self.assertIn('work', out)
        self.assertIn('main', out)

    def test_launch_strips_ambient_keys_and_tracks_chat(self):
        self.rose('claude', '-a', 'work')
        call = [c for c in self.calls() if c['args'] and '--session-id' in c['args']][-1]
        self.assertIsNone(call['api_key'])
        self.assertEqual(call['account'], 'work')
        rows = json.loads(self.rose('sessions', '--json').stdout)
        self.assertEqual([(r['tool'], r['account']) for r in rows], [('claude', 'work')])

    def test_env_file_is_applied(self):
        env_path = self.rose('env', 'claude', 'work').stdout.strip()
        Path(env_path).write_text('ANTHROPIC_API_KEY=sk-company\n')
        self.rose('claude', '-a', 'work')
        self.assertEqual(self.calls()[-1]['api_key'], 'sk-company')

    def test_claude_auto_failover_moves_and_continues(self):
        self.rose('failover', 'claude', 'auto')
        t0 = time.time()
        r = self.rose('claude', '-a', 'work', env={'FAKE_LIMITED': 'work', 'FAKE_HANG': '1'})
        self.assertLess(time.time() - t0, 25, 'watcher should close the limited session')
        self.assertIn('work → personal', r.stderr)
        first, second = [c for c in self.calls() if c['tool'] == 'claude' and c['args'][:1] != ['auth']][-2:]
        sid = first['args'][first['args'].index('--session-id') + 1]
        self.assertEqual(second['account'], 'personal')
        self.assertEqual(second['args'][:2], ['--resume', sid])
        self.assertIn('[rose]', second['args'][-1])
        copied = list((self.home('claude', 'personal') / 'projects').glob(f'*/{sid}.jsonl'))
        self.assertEqual(len(copied), 1)
        self.assertIn('usage_limit_reached', copied[0].read_text())  # full history kept
        rows = json.loads(self.rose('sessions', '--json').stdout)
        self.assertEqual([(r['id'], r['account']) for r in rows], [(sid, 'personal')])
        cool = json.loads((self.tmp / 'rose' / 'cooldowns.json').read_text())
        self.assertIn('claude:work', cool)
        self.assertIn('auto_switched', self.rose('activity').stdout)

    def test_all_accounts_limited_stops(self):
        self.rose('failover', 'claude', 'auto')
        r = self.rose('claude', '-a', 'work', env={'FAKE_LIMITED': 'work,personal', 'FAKE_HANG': '1'})
        self.assertIn('no other account is available', r.stderr)
        self.assertEqual(len([c for c in self.calls() if c['tool'] == 'claude' and c['args'][:1] != ['auth']]), 2)

    def test_ask_mode_without_terminal_never_moves(self):
        r = self.rose('claude', '-a', 'work', env={'FAKE_LIMITED': 'work'})
        self.assertIn('failover is off', r.stderr)
        self.assertFalse(list((self.home('claude', 'personal') / 'projects').glob('*/*.jsonl')))

    def test_codex_auto_failover(self):
        self.rose('failover', 'codex', 'auto')
        r = self.rose('codex', '-a', 'main', env={'FAKE_LIMITED': 'main', 'FAKE_HANG': '1'})
        self.assertIn('main → spare', r.stderr)
        last = self.calls()[-1]
        self.assertEqual((last['account'], last['args'][0]), ('spare', 'resume'))
        self.assertIsNone(last['api_key'])

    def test_manual_move_and_resume_with_codex_projection_reset(self):
        self.rose('codex', '-a', 'main')
        sid = json.loads(self.rose('sessions', '--json').stdout)[0]['id']
        db = self.home('codex', 'spare') / 'thread_history_1.sqlite'
        con = sqlite3.connect(db)
        con.execute('CREATE TABLE thread_items (thread_id TEXT, v TEXT)')
        con.execute('INSERT INTO thread_items VALUES (?, ?), (?, ?)', (sid, 'stale', 'other', 'keep'))
        con.commit()
        con.close()
        self.rose('move', sid[:6], '--to', 'spare')
        rows = sqlite3.connect(db).execute('SELECT thread_id FROM thread_items').fetchall()
        self.assertEqual(rows, [('other',)])
        self.rose('resume', sid[:6])
        last = self.calls()[-1]
        self.assertEqual((last['account'], last['args'][:1]), ('spare', ['resume']))
        self.assertIn(sid, last['args'])

    def test_resume_to_other_claude_account(self):
        self.rose('claude', '-a', 'work')
        sid = json.loads(self.rose('sessions', '--json').stdout)[0]['id']
        self.rose('resume', sid[:8], '--to', 'personal')
        last = self.calls()[-1]
        self.assertEqual((last['account'], last['args'][:2]), ('personal', ['--resume', sid]))

    def test_pin_default_and_shell_emit(self):
        self.rose('pin', 'claude', 'personal')
        self.rose('claude')
        self.assertEqual(self.calls()[-1]['account'], 'personal')
        out = self.rose('__emit', 'use', 'work').stdout
        self.assertIn('unset ANTHROPIC_API_KEY;', out)
        self.assertIn('export CLAUDE_CONFIG_DIR=', out)
        self.assertIn('accounts/claude/work', out)
        auto = self.rose('__emit', 'auto').stdout
        self.assertIn('use claude personal', auto)

    def test_ambiguous_without_choice_fails_cleanly(self):
        r = self.rose('claude', check=False, cwd=self.tmp)
        self.assertEqual(r.returncode, 1)
        self.assertIn('not a terminal', r.stderr)

    def test_passthrough_subcommand(self):
        r = self.rose('claude', '-a', 'work', 'auth', 'status')
        self.assertIn('loggedIn', r.stdout)
        self.assertEqual(self.calls()[-1]['args'], ['auth', 'status'])

    def test_adopt_existing_home(self):
        self.rose('add', 'codex', 'old', '--adopt', str(self.shared_codex), '--no-login')
        self.rose('codex', '-a', 'old')
        self.assertTrue(list((self.shared_codex / 'sessions').rglob('*.jsonl')))

    def test_old_limit_does_not_retrigger_on_resume(self):
        self.rose('claude', '-a', 'work', env={'FAKE_LIMITED': 'work'})       # ask→off without tty
        sid = json.loads(self.rose('sessions', '--json').stdout)[0]['id']
        self.rose('failover', 'claude', 'auto')
        r = self.rose('resume', sid[:8])                                      # now succeeds on work
        self.assertNotIn('→', r.stderr)


    def test_name_new_chat_and_resume_by_name(self):
        r = self.rose('claude', '-a', 'work', '--name', 'excel-calcs')
        self.assertIn('rose resume excel-calcs', r.stderr)
        sid = json.loads(self.rose('sessions', '--json').stdout)[0]['id']
        self.rose('resume', 'excel-calcs', '--to', 'personal')         # name survives a move
        last = self.calls()[-1]
        self.assertEqual((last['account'], last['args'][:2]), ('personal', ['--resume', sid]))
        self.assertIn('excel-calcs', self.rose('sessions').stdout)

    def test_rename_collision_and_clear(self):
        self.rose('claude', '-a', 'work')
        self.rose('codex', '-a', 'main')
        rows = json.loads(self.rose('sessions', '--json', '--all').stdout)
        claude_id = [x['id'] for x in rows if x['tool'] == 'claude'][0]
        codex_id = [x['id'] for x in rows if x['tool'] == 'codex'][0]
        self.rose('name', claude_id[:8], 'budget')
        r = self.rose('name', codex_id[:8], 'BUDGET', check=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn('already used', r.stderr)
        self.rose('name', 'budget', 'budget-v2')                         # rename by current name
        self.rose('resume', 'budget-v2')
        self.assertEqual(self.calls()[-1]['args'][:2], ['--resume', claude_id])
        self.rose('name', 'budget-v2', '--clear')
        self.assertEqual(self.rose('resume', 'budget-v2', check=False).returncode, 1)
        r = self.rose('name', claude_id[:8], 'has space', check=False)
        self.assertIn('no spaces', r.stderr)

    def test_codex_chat_named_after_exit(self):
        self.rose('codex', '-a', 'main', '-n', 'refactor')
        self.rose('resume', 'refactor')
        self.assertEqual(self.calls()[-1]['args'][0], 'resume')

    def statusline_input(self, five, week):
        reset = int(time.time()) + 3600
        return json.dumps({'session_id': 'x', 'workspace': {'current_dir': '/tmp/proj'},
                           'rate_limits': {'five_hour': {'used_percentage': five, 'resets_at': reset},
                                           'seven_day': {'used_percentage': week, 'resets_at': reset + 86400}}})

    def test_usage_install_record_and_restore(self):
        settings = self.shared_claude / 'settings.json'
        data = json.loads(settings.read_text())
        data['statusLine'] = {'type': 'command', 'command': 'cat >/dev/null; echo ORIGINAL-LINE'}
        settings.write_text(json.dumps(data))
        self.rose('usage', 'install')
        cmd = json.loads(settings.read_text())['statusLine']['command']
        self.assertIn('statusline', cmd)
        self.assertEqual(json.loads(settings.read_text())['env'], {'ANTHROPIC_API_KEY': 'sk-shared'})  # rest kept
        # Claude runs the status line with the account in its environment
        work_home = str(self.home('claude', 'work'))
        out = self.rose('statusline', input=self.statusline_input(42, 63),
                        env={'CLAUDE_CONFIG_DIR': work_home}).stdout
        self.assertEqual(out.strip(), 'ORIGINAL-LINE')          # status line unchanged
        status = self.rose('status', '--fast').stdout
        self.assertIn('5h 42%', status)
        self.assertIn('week 63%', status)
        self.assertIn('no usage seen yet', status)                 # personal never ran
        self.rose('usage', 'uninstall')
        self.assertEqual(json.loads(settings.read_text())['statusLine']['command'],
                         'cat >/dev/null; echo ORIGINAL-LINE')

    def test_statusline_never_breaks_on_bad_input(self):
        r = self.rose('statusline', input='not json')
        self.assertEqual(r.returncode, 0)

    def test_failover_skips_account_known_at_100_percent(self):
        self.rose('add', 'claude', 'third', '--no-login')
        self.rose('login', 'claude', 'third')
        self.rose('statusline', input=self.statusline_input(100, 70), env={'ROSE_CLAUDE': 'personal'})
        self.rose('failover', 'claude', 'auto')
        r = self.rose('claude', '-a', 'work', env={'FAKE_LIMITED': 'work', 'FAKE_HANG': '1'})
        self.assertIn('work → third', r.stderr)

    def test_codex_login_uses_device_code_when_headless(self):
        self.rose('login', 'codex', 'spare', env={'SSH_CONNECTION': '1 2 3 4'})
        self.assertEqual(self.calls()[-1]['args'], ['login', '--device-auth'])
        self.rose('login', 'codex', 'spare', '--browser', env={'SSH_CONNECTION': '1 2 3 4'})
        self.assertEqual(self.calls()[-1]['args'], ['login'])
        self.rose('login', 'claude', 'work', env={'SSH_CONNECTION': '1 2 3 4'})
        self.assertEqual(self.calls()[-1]['args'], ['auth', 'login'])

    def set_usage(self, account, five, week=10):
        self.rose('statusline', input=self.statusline_input(five, week), env={'ROSE_CLAUDE': account})

    def test_order_requires_tool_and_accepts_old_form(self):
        self.assertIn('say which tool', self.rose('order', 'personal', check=False).stderr)
        out = self.rose('order', 'claude:personal', 'codex:main', 'claude:work').stdout
        self.assertIn('Claude · personal → Codex · main → Claude · work', out)
        self.assertIn('Order: Claude · personal', self.rose('status', '--fast').stdout)

    def test_limit_hands_over_to_codex_next_in_order(self):
        self.rose('order', 'claude:personal', 'codex:main', 'claude:work')
        self.rose('failover', 'claude', 'auto')
        r = self.rose('claude', '-a', 'personal', '--name', 'excel-calcs', 'build the sheet',
                      env={'FAKE_LIMITED': 'personal', 'FAKE_HANG': '1'})
        self.assertIn('to Codex · main', r.stderr)
        last = self.calls()[-1]
        self.assertEqual((last['tool'], last['account']), ('codex', 'main'))
        self.assertIn('[rose handoff]', last['args'][-1])
        self.assertIn('build the sheet', last['args'][-1])          # earlier conversation carried over
        self.assertNotIn("You've hit your limit", last['args'][-1])  # the error itself is not
        rows = json.loads(self.rose('sessions', '--json', '--all').stdout)
        named = [x for x in rows if x['name'] == 'excel-calcs']
        self.assertEqual([(x['tool'], x['account']) for x in named], [('codex', 'main')])  # name followed

    def test_codex_limit_continues_on_claude_work(self):
        self.rose('order', 'claude:personal', 'codex:main', 'claude:work')
        self.rose('failover', 'codex', 'auto')
        self.rose('codex', '-a', 'main', env={'FAKE_LIMITED': 'main', 'FAKE_HANG': '1'})
        last = self.calls()[-1]
        self.assertEqual((last['tool'], last['account']), ('claude', 'work'))
        self.assertIn('[rose handoff]', last['args'][-1])

    def test_threshold_new_chat_starts_on_next_in_order(self):
        self.rose('order', 'claude:personal', 'codex:main', 'claude:work')
        self.rose('default', 'claude', 'personal')
        self.rose('threshold', '95')
        self.rose('failover', 'claude', 'auto')
        self.set_usage('personal', 96)
        r = self.rose('claude', 'hello')
        self.assertIn('starting on Codex · main', r.stderr)
        last = self.calls()[-1]
        self.assertEqual((last['tool'], last['account'], last['args']), ('codex', 'main', ['hello']))
        self.rose('claude', '-a', 'personal')                        # explicit choice still wins
        self.assertEqual(self.calls()[-1]['account'], 'personal')

    def test_threshold_ask_mode_without_terminal_does_not_switch(self):
        self.rose('order', 'claude:personal', 'codex:main')
        self.rose('default', 'claude', 'personal')
        self.rose('threshold', '95')
        self.set_usage('personal', 99)
        self.rose('claude')
        self.assertEqual(self.calls()[-1]['account'], 'personal')

    def test_rose_chat_uses_first_available(self):
        self.rose('order', 'claude:personal', 'codex:main', 'claude:work')
        self.rose('threshold', '95')
        self.rose('chat', 'first task')
        self.assertEqual(self.calls()[-1]['account'], 'personal')
        self.set_usage('personal', 97)
        r = self.rose('chat', 'second task')
        self.assertIn('skipping Claude · personal (over threshold)', r.stderr)
        self.assertEqual((self.calls()[-1]['tool'], self.calls()[-1]['args']), ('codex', ['second task']))

    def test_resume_over_threshold_moves_within_claude(self):
        self.rose('order', 'claude:personal', 'claude:work')
        self.rose('threshold', '95')
        self.rose('failover', 'claude', 'auto')
        self.rose('claude', '-a', 'personal', '-n', 'notes')
        self.set_usage('personal', 95)
        r = self.rose('resume', 'notes')
        self.assertIn('continuing on Claude · work', r.stderr)
        last = self.calls()[-1]
        self.assertEqual((last['account'], last['args'][0]), ('work', '--resume'))

    def test_statusline_warns_over_threshold(self):
        self.rose('order', 'claude:personal', 'codex:main')
        self.rose('threshold', '95')
        out = self.rose('statusline', input=self.statusline_input(96, 20), env={'ROSE_CLAUDE': 'personal'}).stdout
        self.assertIn('⚠ personal 96%', out)
        self.assertIn('next: main', out)

    def test_usage_shows_all_accounts_with_bars(self):
        self.rose('order', 'claude:personal', 'codex:main', 'claude:work')
        self.set_usage('personal', 50, 25)
        d = self.home('codex', 'main') / 'sessions' / '2026' / '11' / '23'
        d.mkdir(parents=True)
        sid = '11111111-2222-3333-4444-555555555555'
        reset = int(time.time()) + 7200
        (d / f'rollout-2026-11-23T10-00-00-{sid}.jsonl').write_text('\n'.join(json.dumps(x) for x in [
            {'type': 'session_meta', 'timestamp': '2026-11-23T10:00:00Z', 'payload': {'id': sid, 'cwd': '/tmp'}},
            {'type': 'event_msg', 'timestamp': '2026-11-23T10:01:00Z', 'payload': {
                'type': 'token_count', 'rate_limits': {
                    'primary': {'used_percent': 75.0, 'window_minutes': 300, 'resets_at': reset},
                    'secondary': {'used_percent': 10.0, 'window_minutes': 10080, 'resets_in_seconds': 86400}}}},
        ]) + '\n')
        out = self.rose('usage').stdout
        self.assertLess(out.index('Claude · personal'), out.index('Codex · main'))
        self.assertLess(out.index('Codex · main'), out.index('Claude · work'))
        self.assertIn('#1 in order', out)
        self.assertIn('█' * 12 + '░' * 12 + '   50%', out)          # personal 5h
        self.assertIn('█' * 18 + '░' * 6 + '   75%', out)          # codex 5h from its session file
        self.assertIn('no usage seen yet', out)                      # work never ran
        self.assertIn('Codex · spare', out)                          # accounts outside the order too
        self.assertIn('5h 75%', self.rose('status', '--fast').stdout)

if __name__ == '__main__':
    unittest.main(verbosity=2)
