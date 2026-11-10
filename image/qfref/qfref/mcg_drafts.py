
C1 = {
"V1": """Output check: in {file}, `{path}` holds two estimates of one quantity that differ by a pure unit factor: {k1} = {a:.6g}, {k2} = {b:.6g} (ratio {ratio}). Estimators of the same derivative should agree within a few standard errors. A difference quotient divided by the bump measured in the input's own units is a derivative per unit of that input; a label such as "per 1%" or "per day" does not change that number unless the code multiplies it. Find the line that applies the extra factor to one method only, put every method on one unit, and rewrite {file}.""",
"V2": """In your next cell fix only the unit of `{path}` in {file}; leave the other files as they are. {k1} = {a:.6g} and {k2} = {b:.6g} differ by {ratio}, so one method carries an extra scale factor. Keep the unit the explicit formula produces for the bumped method, remove the extra factor from the other, then run this before rewriting the file:
    import json, itertools
    G = json.load(open({file_repr}))
    for opt, d in G.items():
        for greek, m in d.items():
            vals = {{k: v['value'] for k, v in m.items() if isinstance(v, dict) and v.get('value') is not None}}
            for x, y in itertools.combinations(vals, 2):
                if vals[y]: print(opt, greek, x, y, round(vals[x] / vals[y], 4))
Every printed ratio should be close to 1.""",
"V3": """Before you continue, run one cell that prints, for every option and Greek in {file}, each method's value and the ratio between methods. Two estimators of one sensitivity must share sign, unit and scale before they are written side by side. Here `{path}` shows {k1} = {a:.6g} against {k2} = {b:.6g} ({ratio}). When a ratio equals 100, 252 or 365 (or their inverses), find where that factor enters one method's code, decide from the explicit formula which unit is meant, apply it to every method, and rewrite {file}.""",
}

C3 = {
"V1": """Output check: in {err_file}, `{err_path}` = {e:.6g}, which is about twice `{est_path}` = {v:.6g} in {est_file}. A difference that equals twice the estimate means the reference has the same size and the opposite sign: the two numbers are one quantity on two sign conventions (for time decay, dV/dT of time to maturity versus dV/dt of the calendar date). Put the reference on the estimate's convention for the comparison only, keep the written estimate as its explicit formula defines it, then recompute the comparison and every flag that uses it.""",
"V2": """In your next cell change only how `{err_path}` is computed; leave {est_file} as it is. Its value {e:.6g} is about 2 x {v:.6g}, so the reference used in the difference has the opposite sign of the estimate. Reverse the reference's sign in that comparison (for example `ref_cmp = -ref` for the time-decay entry only), recompute the differences and the relative-error flag, print them, and rewrite {err_file} and the summary file.""",
"V3": """Before you build the summary flags, run this check as its own cell: for each entry of {err_file} whose name contains error or diff, print the matching estimate from {est_file}, the reference, and estimate + reference. Two estimates of one Greek must be on one sign and time-unit convention before a relative-error test. If the sum is near zero while the difference is large, the two are the same number with opposite signs: convert one side to the other's convention for the comparison only, then recompute the differences and the summary file.""",
}

C2B = {
"V1": """Output check: in {csv_file}, at the largest sample size {n}, `{label}` = {a:.6g} and {b_label} = {b:.6g} differ by {diff:.3g}, more than {band:.3g} (6 combined standard errors). Rows that differ only in method estimate one quantity from the same paths, so they should agree. The outlying row's code path differs from the one that produced the matching value elsewhere in your outputs; compare the two, fix the outlier, and rewrite {csv_file} and the summary file.""",
"V2": """In your next cell recompute only the outlying row of {csv_file} (`{label}` at size {n}, value {a:.6g}) with the same function you used for the main estimate of that quantity, and print both. If they differ, print `.shape` of every array that enters the payoff in the outlier's code: an array with one entry per path must be one-dimensional; a two-dimensional path matrix there evaluates the payoff at every date. Fix that line, rewrite {csv_file}, then recompute the summary flags.""",
"V3": """Before you finish, check {csv_file} against your other outputs: at size {n}, `{label}` = {a:.6g} while {b_label} = {b:.6g}. Values at the same sample size from methods that share paths must agree within a few standard errors, and the largest-size row of a method must match the value that method reports in the main results file. Find which of the two code paths differs (array shapes, which time column, discounting), make both use one path, and rewrite {csv_file} and the summary file.""",
}
