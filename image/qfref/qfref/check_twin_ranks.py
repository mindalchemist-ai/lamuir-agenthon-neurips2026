import json, glob, os, sys


def walk(obj, path=''):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, f'{path}.{k}')
    elif isinstance(obj, list):
        if len(obj) >= 3 and all(isinstance(r, dict) for r in obj):
            keys = [k for k in obj[0] if 'rank' in k.lower() and all(isinstance(r.get(k), int) for r in obj)]
            for i in range(len(keys)):
                for j in range(i + 1, len(keys)):
                    if all(r[keys[i]] == r[keys[j]] for r in obj):
                        yield path, keys[i], keys[j]
        for n, v in enumerate(obj):
            yield from walk(v, f'{path}[{n}]')


if __name__ == '__main__':
    raw = '/Users/Agenthon/fca-mini-swe/mini-swe/trajectories/raw'
    fired = {}
    for b in sys.argv[1:]:
        for f in glob.glob(f'{raw}/{b}/t1-*/output/**/*.json', recursive=True):
            try:
                d = json.load(open(f))
            except (ValueError, OSError):
                continue
            hits = list(walk(d))
            if hits:
                run = os.path.relpath(f, raw).split('/output/')[0]
                g = open(f'{raw}/{run}/grader_output.txt').read().strip().splitlines()[-1]
                fired[run] = ('PASS' if 'failed' not in g and 'error' not in g else 'FAIL', hits[:2])
    for k, v in sorted(fired.items()):
        print(k, v)
    print('runs fired:', len(fired), 'pass:', sum(v[0] == 'PASS' for v in fired.values()))
