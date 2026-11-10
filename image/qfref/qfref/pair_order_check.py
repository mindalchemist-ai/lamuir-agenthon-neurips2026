import csv, glob, json, os, re, sys

TOK = r'[A-Z][A-Z0-9.^=]{0,9}'
LIST_RE = re.compile(rf'(?<![\w`])`?({TOK})`?(?:\s*,\s*(?:and\s+)?`?({TOK})`?){{2,}}')
SORT_WORDS = re.compile(r'\b(alphabetical|alphabetically|sorted|lexicographic)', re.I)
STOP = {'CSV', 'JSON', 'NAN', 'AIC', 'BIC', 'OLS', 'ID', 'API', 'USD', 'PNL', 'CDF', 'PDF', 'VAR', 'ES'}


def task_lists(text):
    out = []
    for m in re.finditer(rf'(?:`?{TOK}`?\s*,\s*(?:and\s+)?){{2,}}`?{TOK}`?', text):
        names = [t.strip('`').rstrip('.') for t in re.split(r'\s*,\s*(?:and\s+)?', m.group(0))]
        names = [n for n in names if n not in STOP]
        if len(names) >= 3 and len(set(names)) == len(names):
            out.append(names)
    return out


def labels_in_outputs(out_dir):
    pairs = []
    for f in glob.glob(os.path.join(out_dir, '**', '*'), recursive=True):
        if f.endswith('.json'):
            try:
                obj = json.load(open(f))
            except Exception:
                continue
            stack = [obj]
            while stack:
                o = stack.pop()
                if isinstance(o, dict):
                    stack.extend(o.values())
                    stack.extend(k for k in o.keys())
                elif isinstance(o, list):
                    stack.extend(o)
                elif isinstance(o, str):
                    m = re.fullmatch(r'([^-_/\s]+)[-_/]([^-_/\s]+)', o)
                    if m:
                        pairs.append((os.path.basename(f), m.group(1), m.group(2)))
        elif f.endswith('.csv'):
            try:
                rows = list(csv.reader(open(f)))
            except Exception:
                continue
            for r in rows[1:]:
                for a, b in zip(r, r[1:]):
                    pairs.append((os.path.basename(f), a, b))
                for c in r:
                    m = re.fullmatch(r'([^-_/\s]+)[-_/]([^-_/\s]+)', c)
                    if m:
                        pairs.append((os.path.basename(f), m.group(1), m.group(2)))
    return pairs


def check(instruction_text, out_dir):
    if SORT_WORDS.search(instruction_text):
        return []
    problems = []
    for names in task_lists(instruction_text):
        pos = {n: i for i, n in enumerate(names)}
        if names == sorted(names):
            continue
        seen = set()
        for fname, a, b in labels_in_outputs(out_dir):
            if a in pos and b in pos and a != b and pos[a] > pos[b] and (fname, a, b) not in seen:
                seen.add((fname, a, b))
                problems.append(f'{fname}: pair {a},{b} is in the reverse of the task list order {names}')
    return problems


if __name__ == '__main__':
    raw = '/Users/Agenthon/fca-mini-swe/mini-swe/trajectories/raw'
    batches = sys.argv[1:] or ['rag13zv212oc10-full-1', 'rag13zv212oc10-full-2', 'rag13zv212oc11-full-1', 'rag13zv212oc11-full-2']
    n_runs = 0
    for b in batches:
        for d in sorted(glob.glob(f'{raw}/{b}/t1-*')):
            ins = os.path.join(d, 'staged', 'instruction.md')
            g = os.path.join(d, 'grader_output.txt')
            if not os.path.exists(ins):
                continue
            n_runs += 1
            last = open(g).read().strip().splitlines()[-1] if os.path.exists(g) else ''
            ok = 'passed' in last and 'failed' not in last and 'error' not in last
            p = check(open(ins).read(), os.path.join(d, 'output'))
            if p:
                print(f'{b} {os.path.basename(d)} grader={"PASS" if ok else "FAIL"} problems={len(p)} first={p[0]}')
    print('runs scanned:', n_runs)
