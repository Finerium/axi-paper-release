"""e3-public-01: how much do an agent's self-claim and its own reproduction test know about hidden-test correctness,
on public trajectories of other agents and models? Exploratory pilot; README.md holds sources, rules and deviations.

Sources (both CC-BY-4.0):
  openhands  nebius/SWE-rebench-openhands-trajectories: OpenHands v0.54.0 + Qwen3-Coder-480B-A35B-Instruct, SWE-rebench
  swe_agent  nebius/SWE-agent-trajectories: SWE-agent + Llama-3.1-based swe-agent-llama-{8b,70b,405b}, SWE-bench-extra
Run from the repo root:
  .venv-harness/bin/python -I analysis/e3-public/e3_public.py fetch openhands   # pyarrow; HTTP range reads of what is needed
  .venv-harness/bin/python -I analysis/e3-public/e3_public.py fetch swe_agent
  /usr/bin/python3 -I analysis/e3-public/e3_public.py analyze                   # stdlib; writes analysis/e3-public/results.json
  /usr/bin/python3 -I analysis/e3-public/e3_public.py selftest
"""
import collections, hashlib, io, json, os, random, re, shlex, sys, urllib.request

SOURCES = {
    'openhands': {'dataset': 'nebius/SWE-rebench-openhands-trajectories',
                  'rev': '35455389ab51bf5e2306bfd436ef72d0f98bf882',  # HF commit, lastModified 2025-12-27
                  'files': ['trajectories.parquet'], 'small': ['trajectory_id', 'instance_id', 'exit_status', 'resolved'],
                  'explicit': ('submit',)},
    'swe_agent': {'dataset': 'nebius/SWE-agent-trajectories',
                  'rev': '68195a1450865274106246d0d0296a1d6807b88e',  # HF commit, lastModified 2024-12-23
                  'files': [f'data/train-{i:05d}-of-00012.parquet' for i in range(12)],
                  'small': ['instance_id', 'model_name', 'exit_status', 'target'],
                  'explicit': ('submitted', 'submitted_no_patch')},
}
RAW = 'scratch/e3-public'  # git-ignored; one subdirectory per source
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results.json')
SEED, N_PER_CLASS, B = 20261006, 150, 10000


# ---------------------------------------------------------------- fetch (needs pyarrow)
class HTTPFile(io.RawIOBase):
    """Seekable read-only file over HTTP range requests, so pyarrow reads only the footer and the column chunks asked for."""
    def __init__(self, url):
        with urllib.request.urlopen(urllib.request.Request(url, method='HEAD'), timeout=60) as r:
            self.url, self.size = r.geturl(), int(r.headers['Content-Length'])
        self.pos = self.fetched = 0
    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos
    def seek(self, off, whence=0):
        self.pos = (off, self.pos + off, self.size + off)[whence]
        return self.pos
    def readinto(self, b):
        n = min(len(b), self.size - self.pos)
        if n <= 0:
            return 0
        req = urllib.request.Request(self.url, headers={'Range': f'bytes={self.pos}-{self.pos + n - 1}'})
        with urllib.request.urlopen(req, timeout=300) as r:
            data = r.read()
        b[:len(data)] = data
        self.pos += len(data); self.fetched += len(data)
        return len(data)


def sample(frame):
    """Indices into frame: per class (resolved 1, then 0), N_PER_CLASS distinct instances, one random trajectory each."""
    rng, pick = random.Random(SEED), []
    for cls in (1, 0):
        by = collections.defaultdict(list)
        for i, r in enumerate(frame):
            if r['resolved'] == cls:
                by[r['instance_id']].append(i)
        inst = sorted(by)
        rng.shuffle(inst)
        pick += [rng.choice(by[k]) for k in inst[:N_PER_CLASS]]
    return pick


def fetch(name):
    import pyarrow.parquet as pq
    S, raw = SOURCES[name], f'{RAW}/{name}'
    os.makedirs(raw, exist_ok=True)
    handles, meta, groups = [], [], []  # groups: (file, row group, first meta row, rows)
    for fi, path in enumerate(S['files']):
        f = HTTPFile(f"https://huggingface.co/datasets/{S['dataset']}/resolve/{S['rev']}/{path}")
        pf = pq.ParquetFile(f)
        for g in range(pf.metadata.num_row_groups):
            groups.append((fi, g, len(meta), pf.metadata.row_group(g).num_rows))
            meta += pf.read_row_group(g, columns=S['small']).to_pylist()
        handles.append((f, pf))
    for r in meta:
        r['resolved'] = int(r.pop('target') if 'target' in r else r['resolved'])
    with open(f'{raw}/meta_all.jsonl', 'w') as fo:  # small columns of every row
        fo.writelines(json.dumps(r) + '\n' for r in meta)
    # sampling frame: row groups in a seeded random order until each class has N_PER_CLASS distinct instances
    order, frame_groups, seen = groups[:], [], {0: set(), 1: set()}
    random.Random(SEED).shuffle(order)
    for g in order:
        frame_groups.append(g)
        for r in meta[g[2]:g[2] + g[3]]:
            seen[r['resolved']].add(r['instance_id'])
        if min(len(v) for v in seen.values()) >= N_PER_CLASS:
            break
    frame = [i for g in sorted(frame_groups) for i in range(g[2], g[2] + g[3])]
    pick = sorted(frame[i] for i in sample([meta[i] for i in frame]))
    with open(f'{raw}/sample.jsonl', 'w') as fo:
        for fi, g, start, n in sorted(frame_groups):
            want = [i - start for i in pick if start <= i < start + n]
            if want:  # a row group is the smallest unit a range read can fetch
                t = handles[fi][1].read_row_group(g, columns=['trajectory']).take(want).to_pylist()
                fo.writelines(json.dumps({**meta[start + i], 'trajectory': r['trajectory']}) + '\n' for i, r in zip(want, t))
    with open(f'{raw}/frame.json', 'w') as fo:
        json.dump({'row_groups': [[S['files'][fi], g] for fi, g, _, _ in sorted(frame_groups)], 'rows': len(frame),
                   'rows_total': len(meta)}, fo)
    print(f'{name}: {len(meta)} rows in {len(groups)} row groups; frame {len(frame_groups)} row groups ({len(frame)} rows); '
          f'sampled {len(pick)}; fetched {sum(h[0].fetched for h in handles) / 2**20:.1f} MB '
          f'of {sum(h[0].size for h in handles) / 2**20:.0f} MB')


# ---------------------------------------------------------------- rules (stdlib)
EXIT = re.compile(r'\[(?:The command completed|Command finished) with exit code (-?\d+)')
SEG = re.compile(r'&&|\|\||[;|\n]')                      # shell segments, in order
GIT_EDIT = re.compile(r'\bgit\s+(?:checkout|restore|stash|reset|apply|am)\b|\bpatch\s+-p')
SED_I = re.compile(r'\bsed\s+(?:-\S+\s+)*-i')
DOCS = ('.md', '.rst', '.txt')  # only for the docs-not-edits variant
FAILMARK = re.compile(r'Traceback \(most recent call last\)|^\s*\w*(?:Error|Exception)\b:|\bFAILED\b|\bFAIL\b'
                      r'|\b[1-9]\d* (?:failed|errors?)\b|\u274c', re.M)  # "traceback or failure in the output"


def names_file(seg, base):
    return re.search(r'(?:^|[\s/=\'"])' + re.escape(base) + r'(?:$|[\s:\'"])', seg) is not None


def executed(seg):
    """Basenames a shell segment executes: python's script argument, or the targets of pytest / python -m pytest|unittest.
    A file passed as data (python -m pyflakes x.py, python tool.py x.py) is not executed."""
    try:
        tok = shlex.split(seg)
    except ValueError:
        tok = seg.split()
    tok = [re.split(r'[<>]', t)[0] for t in tok]  # drop glued redirections (x.py>out)
    targets = lambda rest: {os.path.basename(x.split('::')[0]) for x in rest if not x.startswith('-')}
    for i, t in enumerate(tok):
        exe = os.path.basename(t)
        if exe in ('pytest', 'py.test'):
            return targets(tok[i + 1:])
        if re.fullmatch(r'python[\d.]*', exe):
            rest = tok[i + 1:]
            while rest and rest[0].startswith('-'):
                o = rest.pop(0)
                if o == '-c':
                    return set()
                if o == '-m':
                    return targets(rest[1:]) if rest and rest[0] in ('pytest', 'unittest') else set()
                if o in ('-W', '-X'):
                    rest = rest[1:]
            return {os.path.basename(rest[0])} if rest else set()
    return set()


def shell_events(k, cmd, created, runs, edits, passed):
    """Runs of created .py files and shell source edits in one command, at positions (step, segment)."""
    for j, seg in enumerate(SEG.split(cmd)):
        hit = {b for b in executed(seg) if created.get(b, k) < k}
        if hit:
            runs.append(((k, j), hit) + passed)
        if GIT_EDIT.search(seg) or SED_I.search(seg):
            edits.append(((k, j), False, seg, 'git' if GIT_EDIT.search(seg) else 'sed'))


def verdicts(claim, runs, edits):
    """runs: (pos, basenames, passed, passed_strict); edits: (pos, is_doc, path or shell segment, kind file|sed|git).
    A source edit is a write to any file other than a reproduction test (a created .py file that was later executed)."""
    repro = set().union(*[r[1] for r in runs])
    edits = [e for e in edits if e[3] == 'git' or (e[3] == 'file' and os.path.basename(e[2]) not in repro)
             or (e[3] == 'sed' and not any(names_file(e[2], b) for b in repro))]

    def last_after(pos):
        after = [r for r in runs if r[0] > pos]
        return after[-1] if after else None
    code = [e[0] for e in edits if not e[1]]
    last = last_after(max(e[0] for e in edits)) if edits else None  # no source edit: nothing to check, undefined
    v = lambda r, i: None if r is None else ('accept' if r[i] else 'reject')
    return {'self_claim': claim, 'own_repro': v(last, 2), 'own_repro_strict': v(last, 3),
            'own_repro_docs_not_edits': v(last_after(max(code)) if code else None, 2),
            'own_repro_no_edit_counts': v(last if edits else last_after((-1, -1)), 2),  # literal: every run is "after"
            'n_repro_files': len(repro), 'n_repro_runs': len(runs), 'n_source_edits': len(edits)}


def classify_openhands(traj):
    """OpenHands: tool calls (execute_bash, str_replace_editor, finish, ...) answered by tool messages; exit codes known."""
    first_user = next((m.get('content') or '' for m in traj if m['role'] == 'user'), '')
    mroot = re.search(r'<uploaded_files>\s*(\S+?)/?\s*</uploaded_files>', first_user)
    root = mroot.group(1) if mroot else '/workspace'
    st, pending = [], {}
    for m in traj:
        if m['role'] == 'tool' and m.get('tool_call_id') in pending:
            pending.pop(m['tool_call_id'])['obs'] = m.get('content') or ''
        for t in m.get('tool_calls') or []:
            try:
                args = json.loads(t['function']['arguments'])
            except (TypeError, ValueError):
                args = {}
            pending[t.get('id')] = s = {'fn': t['function']['name'], 'args': args if isinstance(args, dict) else {}, 'obs': None}
            st.append(s)
    created, runs, edits = {}, [], []
    for k, s in enumerate(st):
        a, obs = s['args'], s['obs']
        if s['fn'] == 'str_replace_editor' and a.get('command') in ('create', 'str_replace', 'insert', 'undo_edit'):
            p = str(a.get('path') or '')
            if obs is not None and not obs.startswith('ERROR'):  # a failed write changed nothing
                if a['command'] == 'create' and p.endswith('.py'):
                    created.setdefault(os.path.basename(p), k)
                if p == root or p.startswith(root + '/'):
                    edits.append(((k, 0), p.endswith(DOCS), p, 'file'))
        elif s['fn'] == 'execute_bash':
            out = EXIT.split(obs or '')[0]
            code = EXIT.findall(obs or '')
            ok = bool(code) and code[-1] == '0'  # no exit code: still running or killed, so it did not succeed
            shell_events(k, str(a.get('command') or ''), created, runs, edits, (ok, ok and not FAILMARK.search(out)))
    last_asst = next((m for m in reversed(traj) if m['role'] == 'assistant'), {})
    claim = 'accept' if any(t['function']['name'] == 'finish' for t in last_asst.get('tool_calls') or []) else 'reject'
    return verdicts(claim, runs, edits)


FENCE = re.compile(r'```[^\n]*\n(.*?)```', re.S)
FOOTER = re.compile(r'\(Open file: (.*)\)\n\(Current directory: (.*)\)\nbash-\$\s*$')
SPECIAL = {'open', 'goto', 'scroll_up', 'scroll_down', 'search_dir', 'search_file', 'find_file', 'create', 'edit', 'submit'}


def classify_swe_agent(traj):
    """SWE-agent: each ai message ends with one fenced command, the next user message is its output plus a state footer
    (open file, current directory). edit rewrites lines of the open file. No exit codes: a run passes when its output has
    no traceback or failure marker."""
    msgs = [m for m in traj if m['role'] in ('ai', 'user')]
    first = FOOTER.search(next((m['text'] or '' for m in msgs if m['role'] == 'user'), ''))
    root = first.group(2) if first else '/'
    st, open_file = [], None
    for i, m in enumerate(msgs):
        if m['role'] == 'user':
            f = FOOTER.search(m['text'] or '')
            open_file = f.group(1) if f else open_file
            continue
        b = FENCE.findall(m['text'] or '')
        obs = msgs[i + 1]['text'] or '' if i + 1 < len(msgs) and msgs[i + 1]['role'] == 'user' else None
        st.append((b[-1].strip() if b else '', obs, open_file))
    created, runs, edits = {}, [], []
    for k, (act, obs, cur) in enumerate(st):
        word = act.split(None, 1)[0] if act else ''
        if word == 'create':
            mf = re.match(r'\[File: (\S+) \(', obs or '')
            if mf:
                if mf.group(1).endswith('.py'):
                    created.setdefault(os.path.basename(mf.group(1)), k)
                if mf.group(1).startswith(root.rstrip('/') + '/'):
                    edits.append(((k, 0), mf.group(1).endswith(DOCS), mf.group(1), 'file'))
        elif word == 'edit':
            if obs and 'File updated' in obs and cur and cur.startswith(root.rstrip('/') + '/'):
                edits.append(((k, 0), cur.endswith(DOCS), cur, 'file'))
        elif word not in SPECIAL:
            out = FOOTER.split(obs)[0] if obs else ''
            ok = obs is not None and not FAILMARK.search(out)
            shell_events(k, act, created, runs, edits, (ok, ok))
    claim = 'accept' if st and st[-1][0].split('\n')[0].strip() == 'submit' else 'reject'
    return verdicts(claim, runs, edits)


CLASSIFY = {'openhands': classify_openhands, 'swe_agent': classify_swe_agent}


# ---------------------------------------------------------------- statistics (stdlib)
def per_instance(rows, key):
    """[accepted resolved, defined resolved, accepted unresolved, defined unresolved] per instance (undefined dropped)."""
    per = collections.defaultdict(lambda: [0, 0, 0, 0])
    for r in rows:
        if r[key] is None:
            continue
        c, o = per[r['instance_id']], 0 if r['resolved'] else 2
        c[o] += r[key] == 'accept'
        c[o + 1] += 1
    return [per[k] for k in sorted(per)]


def ratio(c):
    ar, nr, au, nu = (sum(x[i] for x in c) for i in range(4))
    if not nr or not nu:
        return None
    a, b = ar / nr, au / nu
    return a, b, (a / b if b else float('inf'))


def summary(c, reps=B):
    ar, nr, au, nu = (sum(x[i] for x in c) for i in range(4))
    a, b, lr = ratio(c)
    rng, n, boots = random.Random(SEED), len(c), []
    for _ in range(reps):  # percentile bootstrap that resamples instances (clusters)
        r = ratio([c[rng.randrange(n)] for _ in range(n)])
        if r:
            boots.append(r)
    ci = []
    for i in range(3):
        v = sorted(x[i] for x in boots)
        ci.append([round(v[int(0.05 * (len(v) - 1))], 4), round(v[int(0.95 * (len(v) - 1))], 4)])
    return {'n_instances': n, 'resolved_accepted': ar, 'resolved_defined': nr, 'unresolved_accepted': au,
            'unresolved_defined': nu, 'alpha': round(a, 4), 'alpha_ci90': ci[0], 'beta': round(b, 4),
            'beta_ci90': ci[1], 'lr': round(lr, 3), 'lr_ci90': ci[2], 'bootstrap_reps': len(boots)}


def analyze_source(name):
    S, raw = SOURCES[name], f'{RAW}/{name}'
    with open(f'{raw}/sample.jsonl', 'rb') as f:
        data = f.read()
    rows = []
    for line in data.decode().splitlines():
        r = json.loads(line)
        rows.append({**{k: v for k, v in r.items() if k != 'trajectory'}, **CLASSIFY[name](r['trajectory'])})
    out = {'dataset': S['dataset'], 'revision': S['rev'], 'frame': json.load(open(f'{raw}/frame.json')),
           'sample': {'n_trajectories': len(rows), 'n_instances': len({r['instance_id'] for r in rows}),
                      'n_resolved': sum(r['resolved'] for r in rows), 'sha256': hashlib.sha256(data).hexdigest()}}
    if 'model_name' in rows[0]:
        out['sample']['models'] = dict(collections.Counter(r['model_name'] for r in rows))
    for key in ('self_claim', 'own_repro', 'own_repro_strict', 'own_repro_docs_not_edits', 'own_repro_no_edit_counts'):
        s = summary(per_instance(rows, key))
        s['resolved_undefined'] = sum(1 for r in rows if r['resolved'] and r[key] is None)
        s['unresolved_undefined'] = sum(1 for r in rows if not r['resolved'] and r[key] is None)
        out[key if key in ('self_claim', 'own_repro') else 'variant_' + key] = s
    out['check_self_claim_vs_exit_status'] = dict(collections.Counter(
        f"{r['self_claim']}|{r['exit_status'] if r['exit_status'] in S['explicit'] else 'other'}" for r in rows))
    meta = [json.loads(l) for l in open(f'{raw}/meta_all.jsonl')]
    for r in meta:
        r['claim'] = 'accept' if r['exit_status'] in S['explicit'] else 'reject'
    full = {'all': summary(per_instance(meta, 'claim'), reps=2000)}
    for m in sorted({r.get('model_name') for r in meta} - {None}):
        full[m] = summary(per_instance([r for r in meta if r['model_name'] == m], 'claim'), reps=2000)
    out['self_claim_full_dataset_exit_status'] = full
    out['rows'] = [{k: r.get(k) for k in ('trajectory_id', 'instance_id', 'model_name', 'resolved', 'exit_status', 'self_claim',
                                         'own_repro', 'own_repro_strict', 'own_repro_docs_not_edits',
                                         'own_repro_no_edit_counts', 'n_repro_files',
                                         'n_repro_runs', 'n_source_edits') if k in r} for r in rows]
    return out


def analyze():
    res = {'id': 'e3-public-01', 'seed': SEED, 'n_per_class': N_PER_CLASS, 'bootstrap_reps': B,
           'sources': {n: analyze_source(n) for n in SOURCES if os.path.exists(f'{RAW}/{n}/sample.jsonl')}}
    with open(OUT, 'w') as fo:
        json.dump(res, fo, indent=1)
    keys = ('sample', 'self_claim', 'own_repro', 'variant_own_repro_strict', 'variant_own_repro_docs_not_edits',
            'variant_own_repro_no_edit_counts', 'check_self_claim_vs_exit_status')
    brief = lambda s: {k: s[k] for k in ('resolved_accepted', 'resolved_defined', 'unresolved_accepted', 'unresolved_defined',
                                         'alpha', 'alpha_ci90', 'beta', 'beta_ci90', 'lr', 'lr_ci90')}
    for n, o in res['sources'].items():
        print(n, json.dumps({k: (brief(o[k]) if 'alpha' in o[k] else o[k]) | {kk: o[k][kk] for kk in o[k] if 'undefined' in kk}
                             for k in keys}, indent=1))
        print(n, 'full-dataset self-claim', {m: brief(s) for m, s in o['self_claim_full_dataset_exit_status'].items()})


def selftest():
    # OpenHands
    def call(fn, i, **a):
        return {'role': 'assistant', 'content': '', 'tool_calls': [
            {'id': str(i), 'function': {'name': fn, 'arguments': json.dumps(a)}}]}
    def obs(i, text):
        return {'role': 'tool', 'tool_call_id': str(i), 'content': text}
    ok = '\n[The command completed with exit code 0.]'
    bad = 'Traceback (most recent call last):\nValueError: x\n[The command completed with exit code 1.]'
    R = '/workspace/r__x__1'
    head = [{'role': 'system', 'content': ''}, {'role': 'user', 'content': f'<uploaded_files>\n{R}\n</uploaded_files>'}]
    t = head + [
        call('str_replace_editor', 1, command='create', path=f'{R}/repro.py', file_text='x'),
        obs(1, f'File created successfully at: {R}/repro.py'),
        call('execute_bash', 2, command=f'cd {R} && python repro.py'), obs(2, bad),
        call('str_replace_editor', 3, command='str_replace', path=f'{R}/src/a.py', old_str='a', new_str='b'),
        obs(3, f'The file {R}/src/a.py has been edited.'),
        call('str_replace_editor', 4, command='str_replace', path=f'{R}/repro.py', old_str='a', new_str='b'),
        obs(4, f'The file {R}/repro.py has been edited.'),
        call('execute_bash', 5, command=f'cd {R} && python repro.py'), obs(5, 'all good' + ok)]
    C = classify_openhands
    v = C(t + [call('finish', 6, message='done')])
    assert (v['self_claim'], v['own_repro'], v['n_source_edits'], v['n_repro_runs']) == ('accept', 'accept', 1, 2), v
    v = C(t[:-2] + [call('execute_bash', 5, command='git stash && python repro.py && git stash pop'), obs(5, ok)])
    assert (v['self_claim'], v['own_repro']) == ('reject', None), v      # the run sits between two edits: undefined
    v = C(t + [call('execute_bash', 6, command=f'sed -i s/b/c/ {R}/src/a.py && python repro.py | tail'), obs(6, bad)])
    assert v['own_repro'] == 'reject' and v['n_source_edits'] == 2, v   # run after a shell edit, failed
    v = C(t + [call('execute_bash', 6, command='sed -i s/b/c/ repro.py && python repro.py'), obs(6, ok)])
    assert v['own_repro'] == 'accept' and v['n_source_edits'] == 1, v   # sed on the reproduction test is not a source edit
    v = C(t[:-2] + [call('execute_bash', 5, command='python repro.py'), obs(5, 'Error: x\n' + ok)])
    assert (v['own_repro'], v['own_repro_strict']) == ('accept', 'reject'), v
    v = C(t[:-2] + [call('execute_bash', 5, command='python repro.py'), obs(5, 'no new output after 30 s')])
    assert v['own_repro'] == 'reject', v  # a run without an exit code did not succeed
    v = C(t[:6] + [call('finish', 6, message='done')])  # created and ran a script, never edited a source file
    assert (v['own_repro'], v['own_repro_no_edit_counts'], v['n_source_edits']) == (None, 'reject', 0), v
    v = C(t + [call('str_replace_editor', 6, command='create', path=f'{R}/SUMMARY.md', file_text='x'),
               obs(6, f'File created successfully at: {R}/SUMMARY.md')])
    assert (v['own_repro'], v['own_repro_docs_not_edits']) == (None, 'accept'), v  # a summary note after the last run
    # SWE-agent
    foot = lambda f: f'\n(Open file: {f})\n(Current directory: /r)\nbash-$'
    ai = lambda cmd: {'role': 'ai', 'text': f'DISCUSSION\nx\n```\n{cmd}\n```'}
    us = lambda text, f='n/a': {'role': 'user', 'text': text + foot(f)}
    t = [{'role': 'system', 'text': ''}, us('ISSUE'), ai('create reproduce.py'), us('[File: /r/reproduce.py (1 lines total)]\n1:', '/r/reproduce.py'),
         ai('edit 1:1\nimport a\nend_of_edit'), us('[File: /r/reproduce.py]\nFile updated.', '/r/reproduce.py'),
         ai('python reproduce.py'), us('Traceback (most recent call last):\nValueError', '/r/reproduce.py'),
         ai('open a.py'), us('[File: /r/a.py (9 lines total)]', '/r/a.py'),
         ai('edit 2:2\nx = 1\nend_of_edit'), us('[File: /r/a.py]\nFile updated.', '/r/a.py'),
         ai('python reproduce.py'), us('Script completed successfully, no errors.', '/r/a.py')]
    v = classify_swe_agent(t + [ai('submit')])
    assert (v['self_claim'], v['own_repro'], v['n_source_edits'], v['n_repro_runs']) == ('accept', 'accept', 1, 2), v
    v = classify_swe_agent(t + [ai('edit 3:3\ny = 2\nend_of_edit'), us('Your proposed edit has introduced new syntax error(s)', '/r/a.py')])
    assert (v['self_claim'], v['own_repro'], v['n_source_edits']) == ('reject', 'accept', 1), v  # a refused edit changed nothing
    v = classify_swe_agent(t[:-2] + [ai('python reproduce.py'), us('=== 1 failed, 3 passed ===', '/r/a.py')])
    assert v['own_repro'] == 'reject', v
    # shared parts
    assert executed(' timeout 10 python3 -u x.py 2>&1') == {'x.py'} and executed('python tool.py x.py') == {'tool.py'}
    assert executed('python -m pytest tests/t.py::test_a -v') == {'t.py'} and executed('pytest -q t.py') == {'t.py'}
    assert executed('python -m pyflakes x.py') == set() and executed('python -c "import x"') == set()
    c = per_instance([{'instance_id': 'a', 'resolved': 1, 'k': 'accept'}, {'instance_id': 'b', 'resolved': 0, 'k': 'reject'},
                      {'instance_id': 'b', 'resolved': 0, 'k': 'accept'}, {'instance_id': 'c', 'resolved': 0, 'k': None}], 'k')
    assert ratio(c) == (1.0, 0.5, 2.0), ratio(c)
    print('selftest ok')


if __name__ == '__main__':
    {'fetch': lambda: fetch(sys.argv[2]), 'analyze': analyze, 'selftest': selftest}[sys.argv[1]]()
