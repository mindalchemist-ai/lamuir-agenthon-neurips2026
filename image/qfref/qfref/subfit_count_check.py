import json, re, sys

COUNT = re.compile(r"^(num_|n_)?(obs|observations|nobs|n_obs|num_obs|observations_fit|num_observations_fit|n)$")
FIT_KEYS = {"kappa", "sigma", "theta", "beta", "phi", "slope", "ols_slope", "half_life", "mu", "alpha"}


def fit_block(v):
    if not isinstance(v, dict):
        return None
    keys = {k.lower() for k in v}
    if not keys & FIT_KEYS:
        return None
    for k, x in v.items():
        if COUNT.match(k.lower()) and isinstance(x, int) and not isinstance(x, bool):
            return k, x
    return None


def issues(v, path=""):
    out = []
    if isinstance(v, dict):
        blocks = {k: fit_block(x) for k, x in v.items()}
        blocks = {k: b for k, b in blocks.items() if b}
        if len(blocks) >= 3:
            full_key = max(blocks, key=lambda k: blocks[k][1])
            full = blocks[full_key][1]
            subs = {k: b[1] for k, b in blocks.items() if k != full_key}
            total = sum(subs.values())
            k = len(subs)
            if total in (full + 1, full) and total != full - (k - 1):
                out.append(f"{path or '<root>'}: the largest fit block {full_key} reports {full}; the other blocks "
                           f"({', '.join(f'{a}={b}' for a, b in subs.items())}) add up to {total}. If these are {k} consecutive "
                           f"segments of that sample fitted separately, each segment of N_s points gives N_s - 1 pairs, so the "
                           f"pair counts add up to {full - (k - 1)} when the largest block is itself a pair count. Check that every "
                           f"count field holds the number of pairs actually regressed in its own fit (len of its regression arrays).")
        for kk, x in v.items():
            out += issues(x, f"{path}.{kk}")
    elif isinstance(v, list):
        for i, x in enumerate(v):
            out += issues(x, f"{path}[{i}]")
    return out


if __name__ == "__main__":
    for f in sys.argv[1:]:
        for line in issues(json.load(open(f))):
            print(f, line)
