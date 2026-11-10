import argparse
import json
import pathlib
import re
import time

import verifier_agent_v8_1 as v81
import output_contracts as oc

VERSION = 'verifier-agent-v8.4'
NAME = 'Structural validity'
SCOPES = ['structural_validity']
SUITE_NAME = 'structural_validity_test.py'
REPORT_NAME = 'structural_validity.json'
RUNS = v81.v8.ARM / 'verifier-runs' / VERSION
NUMERIC_VALUES = re.compile(r'\b(?:each|every)\s+`([^`]+)`\s+value\s+must\s+be\s+(?:the\s+|a\s+)?numeric\b', re.I)


def object_paths(block, field):
    if block['kind'] != 'fenced_structure':
        return []
    raw = block['raw'].splitlines(keepends=True)
    body = ''.join(raw[1:-1])
    try:
        cooked = re.sub(r'(?<!")<([^<>\n]+)>(?!")', lambda m: json.dumps('__slot:' + m[1] + '__'), body)
        tree = json.loads(cooked)
    except (ValueError, TypeError):
        return []
    paths = []
    def visit(node, path):
        if not isinstance(node, dict):
            return
        for key, child in node.items():
            child_path = path + [key]
            if key == field:
                if child == '__slot:object__':
                    paths.append(child_path)
                elif isinstance(child, dict) and child == {'value': '__slot:object__'}:
                    paths.append(child_path + ['value'])
            visit(child, child_path)
    visit(tree, [])
    return paths


def add_structure_notes(statement, contracts):
    lines = statement.splitlines(keepends=True)
    masked = v81.v8.ins.fenced_out(statement.splitlines())
    sections = v81.v8.ins.index(statement)['sections']
    notes = []
    for span in contracts['sections']:
        active = []
        pos, end = span['line_start'] - 1, span['line_end']
        while pos < end:
            if masked[pos] is None:
                pos += 1
                continue
            section = next((s for s in sections if s['line_start'] - 1 == pos), None)
            if section:
                active = [f['file'] for f in contracts['files'] if v81.cites_name(f['file'], section['path'])]
            names = [f['file'] for f in contracts['files'] if v81.cites_name(f['file'], lines[pos])]
            if names:
                active = names
            if not re.match(r'^\s*[-*]\s+', lines[pos]):
                pos += 1
                continue
            stop = pos + 1
            while stop < end and masked[stop] is not None and lines[stop].strip() and not re.match(r'^\s*(?:[-*]\s+|#{1,6}\s)', lines[stop]):
                stop += 1
            raw = ''.join(lines[pos:stop])
            if active and re.search(r'\b(keys?|values?|numeric|scalar|object|array|columns?|headers?|format|strings?|integer|boolean)\b', raw, re.I):
                notes.append({'files': active[:], 'line_start': pos + 1, 'line_end': stop, 'raw': raw})
            pos = stop
    contracts['structure_notes'] = notes
    rules, unresolved = [], []
    for index, note in enumerate(notes):
        text = ' '.join(note['raw'].split())
        match = NUMERIC_VALUES.search(text)
        if not match:
            unresolved.append({'note_index': index, 'reason': 'preserved structure note; no supported executable interpretation'})
            continue
        field = match.group(1)
        candidates = []
        for file in note['files']:
            if pathlib.PurePosixPath(file).suffix != '.json':
                continue
            for block in contracts['blocks']:
                if file in block['files']:
                    for path in object_paths(block, field):
                        candidates.append((file, tuple(path)))
        candidates = sorted(set(candidates))
        if len(candidates) != 1:
            unresolved.append({'note_index': index, 'reason': 'numeric-value note has no unique object path in copied template'})
            continue
        file, path = candidates[0]
        rules.append({'file': file, 'path': list(path), 'kind': 'each_object_value_numeric',
                      'source_note_index': index, 'line_start': note['line_start'], 'line_end': note['line_end'],
                      'source_raw': note['raw']})
    contracts['note_rules'] = rules
    contracts['unresolved_structure_notes'] = unresolved
    return contracts


def render_note_tests(run_dir, contracts):
    generated = []
    with (run_dir / SUITE_NAME).open('a') as handle:
        for index, rule in enumerate(contracts['note_rules']):
            name = 'test_numeric_object_values_' + str(index)
            generated.append(name)
            expression = 'data' + ''.join('[' + repr(key) + ']' for key in rule['path'])
            handle.write(f'''\n# Output structure note: lines {rule['line_start']}-{rule['line_end']}
def {name}():
    data = _load({rule['file']!r})
    values = {expression}
    assert isinstance(values, dict), "Expected object at {'.'.join(rule['path'])}"
    for pair, value in values.items():
        assert type(value) in (int, float), f"{{pair}}: expected numeric scalar, got {{type(value).__name__}}"
''')
    return generated


DECLARATION = re.compile(r'^\s*(?:[-*]\s+)?(?:\*\*)?(?:csv\s+)?(?:columns?|headers?)(?:\s*\([^)\n]*\))?(?:\*\*)?\s*:\s*(?:\*\*)?\s*'
                         r'(`[^`\n]+`(?:\s*,\s*`[^`\n]+`)+)\s*\.?\s*$', re.I)
COLUMN_NAME = re.compile(r'[A-Za-z_][A-Za-z0-9_.+-]*')
PARAGRAPH_STOP = re.compile(r'^\s*(?:#|`{3,}|~{3,})')
EXACT_WORDS = (re.compile(r'\bexact(?:ly)?\b', re.I), re.compile(r'\bcolumns?\b', re.I), re.compile(r'\border\b', re.I))


def is_fragment(block):
    return block['kind'] == 'inline_csv' and not re.search(r'[A-Za-z0-9]', block['raw'])


def fix_inline_column_lists(statement, contracts):
    lines = statement.splitlines()
    fragments = {}
    for block in contracts['blocks']:
        if is_fragment(block):
            fragments.setdefault(block['line_start'], set()).update(block['files'])
    kept = [b for b in contracts['blocks'] if not is_fragment(b)]
    fixed, uncovered = [], []
    for line_no, files in sorted(fragments.items()):
        text = lines[line_no - 1]
        m = DECLARATION.match(text)
        names = [i.strip().strip('`') for i in m.group(1).split(',')] if m else []
        if not m or any(not COLUMN_NAME.fullmatch(n) for n in names) or len(set(names)) != len(names):
            uncovered.append({'line': line_no, 'source_line': text, 'files': sorted(files),
                              'reason': 'not an explicit "Columns: `a`, `b`" declaration of plain names; no check generated'})
            continue
        start = line_no - 1
        while start > 0 and lines[start - 1].strip() and not PARAGRAPH_STOP.match(lines[start - 1]):
            start -= 1
        context = '\n'.join(lines[start:line_no])
        mode = 'exact' if all(w.search(context) for w in EXACT_WORDS) else 'required'
        block = {'files': sorted(files), 'kind': 'inline_csv', 'line_start': line_no, 'line_end': line_no,
                 'raw': '`' + ','.join(names) + '`', 'source_line': text,
                 'header_context': {'line_start': line_no, 'line_end': line_no, 'source_raw': text, 'mode': mode}}
        kept.append(block)
        fixed.append({'line': line_no, 'source_line': text, 'files': sorted(files), 'columns': names, 'mode': mode})
    contracts['blocks'] = kept
    for entry in contracts['files']:
        entry['block_indices'] = [i for i, b in enumerate(kept) if entry['file'] in b['files']]
        entry['status'] = 'STRUCTURE_COPIED' if entry['block_indices'] else 'NO_STRUCTURE_CAPTURED'
    contracts['inline_column_lists'] = {'fixed': fixed, 'uncovered': uncovered}
    return fixed, uncovered


def build_structural_validity(unit):
    statement = v81.v8.load_statement(v81.v8.UNITS / unit)
    source, required = v81.v31_source(unit, statement)
    contracts = oc.extract(statement, v81.v8.ins.index(statement)['sections'], required, matches_name=v81.cites_name, csv_header_context=True)
    fix_inline_column_lists(statement, contracts)
    add_structure_notes(statement, contracts)
    oc.extract_array_lengths(statement, contracts)
    contracts.update(unit=unit, instruction_sha256=v81.sha(statement), v31_record=str(source))
    run_dir = RUNS / unit / f"{time.strftime('%Y%m%dT%H%M%S')}-{time.time_ns()}"
    oc.write_artifacts(run_dir, contracts)
    (run_dir / 'structure_notes.md').write_text('\n'.join(n['raw'] for n in contracts['structure_notes']))
    generation = oc.generate_structural_validity_pytest(run_dir, contracts)
    generation['generated_tests'] += render_note_tests(run_dir, contracts)
    generation['note_rules'] = contracts['note_rules']
    generation['unresolved_structure_notes'] = contracts['unresolved_structure_notes']
    generation['scope'] += '; explicit numeric object-value notes; explicit inline column-name declarations'
    (run_dir / REPORT_NAME).write_text(json.dumps(generation, indent=2))
    record = {'version': VERSION, 'name': NAME, 'layer': 2, 'scopes': SCOPES,
              'suite': SUITE_NAME, 'report': REPORT_NAME, 'unit': unit, 'status': 'PARTIAL' if generation['generated_tests'] else 'UNCOVERED',
              'required_files': required, 'statement_sha256': v81.sha(statement), 'v31_record': str(source),
              'contracts_sha256': v81.sha((run_dir / 'output_contracts.json').read_text()),
              'pytest_sha256': v81.sha((run_dir / SUITE_NAME).read_text()),
              'structural_validity': generation, 'cost': {'requests': 0},
              'code_fingerprint': {str(p.name): v81.sha(p.read_text()) for p in [pathlib.Path(__file__), pathlib.Path(oc.__file__), pathlib.Path(v81.__file__)]}}
    (run_dir / 'code_fingerprint.json').write_text(json.dumps(record['code_fingerprint'], indent=2))
    (run_dir / 'construction.json').write_text(json.dumps(record, indent=2))
    return {'run_dir': str(run_dir), **record}


build = build_structural_validity


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['build'])
    parser.add_argument('unit')
    args = parser.parse_args()
    print(json.dumps(build(args.unit), indent=2))
