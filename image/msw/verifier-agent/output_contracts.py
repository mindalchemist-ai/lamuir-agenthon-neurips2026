import csv
import json
import pathlib
import re


def extract(statement, sections, required, matches_name=None, *, csv_header_context=False):
    lines = statement.splitlines(keepends=True)
    def names_in(text):
        return [n for n in required if (matches_name(n, text) if matches_name else
                re.search(r'(?<![\w.-])' + re.escape(n) + r'(?![\w.-])', text))]
    spans = []
    for i, section in enumerate(sections):
        if not re.search(r'\b(outputs?|deliverables?)\b', section['heading'], re.I):
            continue
        start, end = section['line_start'] - 1, len(lines)
        for following in sections[i + 1:]:
            if following['level'] <= section['level']:
                end = following['line_start'] - 1
                break
        if not any(a <= start < b for a, b in spans):
            spans.append((start, end))
    result = {'sections': [{'line_start': a + 1, 'line_end': b} for a, b in spans],
              'blocks': [], 'files': []}
    def header_context(pos):
        end = pos
        while end > 0 and not lines[end - 1].strip():
            end -= 1
        start = end
        while start > 0 and lines[start - 1].strip() and not re.match(r'^\s*(?:#|[-*]\s|`{3,}|~{3,})', lines[start - 1]):
            start -= 1
        raw = ''.join(lines[start:end])
        explicit = bool(re.search(r'\b(?:columns?|headers?)\s*:|\b(?:these|following)\s+columns?\b', raw, re.I))
        if not explicit:
            return None
        exact = bool(re.search(r'\bexact(?:ly)?\b', raw, re.I) and
                     re.search(r'\bcolumns?\b', raw, re.I) and re.search(r'\border\b', raw, re.I))
        return {'line_start': start + 1, 'line_end': end, 'source_raw': raw,
                'mode': 'exact' if exact else 'required'}

    def add(start, end, kind, active):
        if not active:
            return
        result['blocks'].append({'files': active[:], 'kind': kind,
                                 'line_start': start + 1, 'line_end': end,
                                 'raw': ''.join(lines[start:end])})
    for start, end in spans:
        active, pos = [], start
        while pos < end:
            line = lines[pos]
            heading = next((s for s in sections if s['line_start'] - 1 == pos), None)
            if heading:
                active = names_in(heading['path'])
            mentioned = names_in(line)
            if mentioned:
                active = mentioned
            opening = re.match(r'^\s{0,3}(`{3,}|~{3,})([^\r\n]*)', line)
            if opening:
                fence, language = opening.groups()
                stop = pos + 1
                while stop < end and not re.match(r'^\s{0,3}' + re.escape(fence[0]) + '{' + str(len(fence)) + r',}\s*$', lines[stop].rstrip('\r\n')):
                    stop += 1
                body = ''.join(lines[pos + 1:stop]).lstrip()
                suffixes = {pathlib.PurePosixPath(n).suffix.lower() for n in active}
                kind = language.strip().lower()
                if kind in ('json', 'csv') or (kind in ('', 'text', 'plaintext') and
                    (('.json' in suffixes and body.startswith(('{', '['))) or
                     ('.csv' in suffixes and ',' in body))):
                    add(pos, min(stop + 1, end), 'fenced_structure', active)
                pos = stop + 1
                continue
            if '|' in line and pos + 1 < end and re.match(r'^\s*\|?\s*:?-{3,}', lines[pos + 1]):
                stop = pos + 2
                while stop < end and '|' in lines[stop] and lines[stop].strip():
                    stop += 1
                add(pos, stop, 'schema_table', active)
                pos = stop
                continue
            if ('.csv' in {pathlib.PurePosixPath(n).suffix.lower() for n in active}
                    and re.match(r'^(?: {4}|\t)', line) and ',' in line):
                stop = pos + 1
                while stop < end and re.match(r'^(?: {4}|\t)', lines[stop]) and lines[stop].strip():
                    stop += 1
                add(pos, stop, 'indented_csv', active)
                pos = stop
                continue
            if csv_header_context and '.csv' in {pathlib.PurePosixPath(n).suffix.lower() for n in active}:
                literal = re.fullmatch(r'\s*`([^`\n]*,[^`\n]*)`\s*', line)
                context = header_context(pos) if literal else None
                if context:
                    add(pos, pos + 1, 'inline_csv', active)
                    result['blocks'][-1]['raw'] = '`' + literal[1] + '`'
                    result['blocks'][-1]['header_context'] = context
                    pos += 1
                    continue
            if '.csv' in {pathlib.PurePosixPath(n).suffix.lower() for n in active} and re.search(r'\bcolumns?\b', line, re.I):
                for literal in re.finditer(r'`([^`\n]*,[^`\n]*)`', line):
                    result['blocks'].append({'files': active[:], 'kind': 'inline_csv',
                        'line_start': pos + 1, 'line_end': pos + 1,
                        'column_start': literal.start(), 'column_end': literal.end(),
                        'raw': literal.group(0)})
            pos += 1
    for name in required:
        indices = [i for i, block in enumerate(result['blocks']) if name in block['files']]
        result['files'].append({'file': name, 'format': pathlib.PurePosixPath(name).suffix.lstrip('.'), 'status': 'STRUCTURE_COPIED' if indices else 'NO_STRUCTURE_CAPTURED',
                                'block_indices': indices})
    return result


def write_artifacts(directory, contracts):
    directory = pathlib.Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'output_contracts.json').write_text(json.dumps(contracts, indent=2, ensure_ascii=False))
    (directory / 'output_contracts.md').write_text('\n'.join(b['raw'] for b in contracts['blocks']))
    for entry in contracts['files']:
        path = directory / 'files' / (entry['file'] + '.md')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('\n'.join(contracts['blocks'][i]['raw'] for i in entry['block_indices']))


def markdown_csv_columns(raw):
    rows = []
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith('|') or not line.endswith('|'):
            raise ValueError('ambiguous Markdown table boundaries')
        cells = [cell.strip() for cell in line[1:-1].split('|')]
        rows.append(cells)
    if len(rows) < 3 or len(set(map(len, rows))) != 1:
        raise ValueError('malformed Markdown column table')
    positions = [i for i, name in enumerate(rows[0]) if name == 'Column']
    if len(positions) != 1:
        raise ValueError('Markdown table needs exactly one explicit Column field')
    if not all(re.fullmatch(r':?-{3,}:?', cell) for cell in rows[1]):
        raise ValueError('ambiguous Markdown table separator')
    columns = []
    for row in rows[2:]:
        cell = row[positions[0]]
        if re.fullmatch(r'`[^`]+`', cell):
            name = cell[1:-1]
        elif re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.-]*', cell):
            name = cell
        else:
            raise ValueError('nonliteral or ambiguous Markdown Column name')
        if not name or any(marker in name for marker in ('<', '>', '...', '|', '\\')):
            raise ValueError('nonliteral or ambiguous Markdown Column name')
        columns.append(name)
    if len(set(columns)) != len(columns):
        raise ValueError('duplicate Markdown Column names')
    return columns


def parse_json_template(body):
    token = re.compile(r'\s*("(?:[^"\\\x00-\x1f]|\\.)*"|<[^<>\n]+>|\.\.\.|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?|true|false|null|[{}\[\],:])')
    tokens, cursor = [], 0
    while cursor < len(body):
        if not body[cursor:].strip():
            break
        match = token.match(body, cursor)
        if not match:
            raise ValueError('unrecognized JSON template text')
        tokens.append(match[1])
        cursor = match.end()
    index = 0

    def take(expected=None):
        nonlocal index
        if index >= len(tokens) or (expected is not None and tokens[index] != expected):
            raise ValueError('ambiguous JSON template syntax')
        result = tokens[index]
        index += 1
        return result

    def value(depth=0):
        if depth > 100:
            raise ValueError('JSON template nesting too deep')
        item = take()
        if item in ('{', '['):
            closing = '}' if item == '{' else ']'
            node = {'kind': 'object' if item == '{' else 'array', 'entries': [], 'ellipsis': False}
            keys = set()
            if index < len(tokens) and tokens[index] == closing:
                take(closing)
                return node
            while True:
                if index < len(tokens) and tokens[index] == '...':
                    take('...')
                    take(closing)
                    if not node['entries']:
                        return {'kind': 'unsupported', 'invalid_ellipsis': True,
                                'reason': 'ellipsis has no preceding parallel example'}
                    node['ellipsis'] = True
                    return node
                if item == '{':
                    key_token = take()
                    if not key_token.startswith('"'):
                        raise ValueError('JSON template needs explicit object keys')
                    key = json.loads(key_token)
                    if key in keys:
                        raise ValueError('duplicate JSON template keys')
                    keys.add(key)
                    take(':')
                    node['entries'].append({'key': key, 'schema': value(depth + 1)})
                else:
                    node['entries'].append(value(depth + 1))
                separator = take()
                if separator == closing:
                    return node
                if separator != ',':
                    raise ValueError('ambiguous JSON template delimiter')
        if item == '...':
            return {'kind': 'unsupported', 'invalid_ellipsis': True,
                    'reason': 'ellipsis in value position has no parallel example'}
        if item in ('}', ']', ',', ':'):
            raise ValueError('ambiguous JSON template value')
        if item.startswith('<'):
            kind = item[1:-1].strip()
        else:
            literal = json.loads(item)
            if isinstance(literal, str) and re.fullmatch(r'<[^<>]+>', literal):
                kind = literal[1:-1].strip()
            else:
                kind = {str: 'str', int: 'int', float: 'float', bool: 'bool', type(None): 'null'}[type(literal)]
        if kind not in ('int', 'float', 'bool', 'str'):
            return {'kind': 'unsupported', 'reason': 'unsupported placeholder/type: ' + kind}
        return {'kind': kind}

    tree = value()
    if index != len(tokens):
        raise ValueError('extra JSON template text')
    return tree


def template_root_keys(body):
    tree = parse_json_template(body)
    if tree['kind'] != 'object':
        raise ValueError('root object required')
    def legacy_validate(node):
        if node['kind'] not in ('object', 'array'):
            if node.get('invalid_ellipsis'):
                raise ValueError('ambiguous JSON template value')
            return
        if node['ellipsis'] and not node['entries']:
            raise ValueError('ellipsis has no preceding example')
        for entry in node['entries']:
            legacy_validate(entry['schema'] if node['kind'] == 'object' else entry)
    legacy_validate(tree)
    keys = [entry['key'] for entry in tree['entries']]
    if tree['ellipsis'] or any('<' in key or '>' in key for key in keys):
        raise ValueError('root ellipsis or dynamic keys need template interpretation')
    return keys


def compile_template_schema(tree):
    uncovered = []

    def unsupported(path, reason):
        uncovered.append({'path': path, 'reason': reason})

    def empty_value_example(node):
        if node.get('invalid_ellipsis'):
            return True
        if node['kind'] == 'object' and node['entries']:
            return all(empty_value_example(entry['schema']) for entry in node['entries'])
        return False

    def compile_node(node, path):
        kind = node['kind']
        if path and kind == 'object' and empty_value_example(node):
            unsupported(path, 'object example contains only value-position ellipses; key schema uncovered')
            return {'type': 'object'}
        if kind == 'unsupported':
            unsupported(path, node['reason'])
            return {}
        if kind in ('int', 'float', 'bool', 'str'):
            return {'type': kind}
        if kind == 'object':
            result = {'type': 'object', 'properties': {}}
            dynamic = []
            for entry in node['entries']:
                key = entry['key']
                if re.fullmatch(r'<[^<>]+>', key):
                    dynamic.append(entry['schema'])
                elif '<' in key or '>' in key:
                    unsupported(path + [key], 'ambiguous dynamic key spelling')
                else:
                    result['properties'][key] = compile_node(entry['schema'], path + [key])
            if node['ellipsis'] and not node['entries']:
                unsupported(path, 'ellipsis has no preceding example')
            if dynamic:
                if not node['ellipsis']:
                    unsupported(path + ['*'], 'dynamic key repetition requires an ellipsis')
                elif len(dynamic) != 1 or result['properties']:
                    unsupported(path + ['*'], 'ambiguous mixed dynamic/literal examples')
                else:
                    result['values'] = compile_node(dynamic[0], path + ['*'])
            return result
        result = {'type': 'array'}
        if not node['ellipsis']:
            if node['entries']:
                unsupported(path + ['[]'], 'array element repetition is not explicit')
            return result
        if not node['entries']:
            unsupported(path + ['[]'], 'ellipsis has no preceding example')
            return result
        if any(example != node['entries'][0] for example in node['entries'][1:]):
            unsupported(path + ['[]'], 'parallel examples have different formats')
            return result
        result['items'] = compile_node(node['entries'][0], path + ['[]'])
        return result

    return compile_node(tree, []), uncovered


def add_template_structure_tests(directory, contracts, source, generated):
    rules, uncovered = [], []
    for entry in contracts['files']:
        if entry['format'] != 'json':
            continue
        for block_index in entry['block_indices']:
            block = contracts['blocks'][block_index]
            if block['kind'] != 'fenced_structure':
                continue
            lines = block['raw'].splitlines(keepends=True)
            location = {'file': entry['file'], 'line_start': block['line_start'], 'line_end': block['line_end']}
            try:
                if len(lines) < 3 or not re.fullmatch(r'\s*(`{3,}|~{3,})\s*', lines[-1].strip()):
                    raise ValueError('unclosed structure fence')
                schema, gaps = compile_template_schema(parse_json_template(''.join(lines[1:-1])))
            except ValueError as exc:
                uncovered.append({**location, 'path': [], 'reason': str(exc)})
                continue
            uncovered.extend({**location, **gap} for gap in gaps)
            if not schema:
                continue
            name = 'test_' + re.sub(r'\W', '_', pathlib.PurePosixPath(entry['file']).stem) + '_template_structure_' + str(block_index)
            generated.append(name)
            rules.append({**location, 'schema': schema, 'source_raw': block['raw'], 'test': name})
    if rules:
        source.extend(['', '''def _check_template(value, schema, path):
    kind = schema.get("type")
    expected = {"int": (int,), "float": (int, float), "bool": (bool,),
                "str": (str,), "object": (dict,), "array": (list,)}
    if kind:
        assert type(value) in expected[kind], f"{path}: expected {kind}, got {type(value).__name__}"
    for key, child in schema.get("properties", {}).items():
        assert key in value, f"{path}: missing key {key}"
        _check_template(value[key], child, path + "." + key)
    if "values" in schema:
        for key, child in value.items():
            _check_template(child, schema["values"], path + "." + str(key))
    if "items" in schema:
        for index, child in enumerate(value):
            _check_template(child, schema["items"], path + "[" + str(index) + "]")
'''])
        for rule in rules:
            source.extend([f'# Template structure: lines {rule["line_start"]}-{rule["line_end"]}',
                           f'def {rule["test"]}():',
                           f'    _check_template(_load({rule["file"]!r}), {rule["schema"]!r}, {rule["file"]!r})', ''])
    return rules, uncovered


def extract_array_lengths(statement, contracts):
    def words(text):
        return {word[:-1] if word.endswith('s') and len(word) > 3 else word
                for word in re.findall(r'[a-z0-9]+', text.lower())}
    mentions = []
    for number, line in enumerate(statement.splitlines(keepends=True), 1):
        match = re.fullmatch(r'\s*(?:[-*]\s+)?Top[- ](\d+)\s+([^\n]+)\n?', line, re.I)
        if match:
            mentions.append({'count': int(match[1]), 'words': sorted(words(match[2])),
                             'line_start': number, 'line_end': number, 'source_raw': line})
    rules, uncovered = [], []
    seen = set()
    for entry in contracts['files']:
        if entry['format'] != 'json':
            continue
        for block_index in entry['block_indices']:
            block = contracts['blocks'][block_index]
            if block['kind'] != 'fenced_structure':
                continue
            try:
                tree = parse_json_template(''.join(block['raw'].splitlines(keepends=True)[1:-1]))
            except ValueError:
                continue
            def visit(node, path):
                if node['kind'] == 'object':
                    for child in node['entries']:
                        if '<' not in child['key'] and '>' not in child['key']:
                            visit(child['schema'], path + [child['key']])
                elif node['kind'] == 'array' and path:
                    match = re.fullmatch(r'top_(\d+)_(.+)', path[-1], re.I)
                    if not match:
                        return
                    identity = (entry['file'], tuple(path))
                    if identity in seen:
                        return
                    seen.add(identity)
                    metric = words(match[2].replace('_', ' '))
                    candidates = [m for m in mentions if metric and metric <= set(m['words'])]
                    counts = {m['count'] for m in candidates}
                    if counts != {int(match[1])}:
                        uncovered.append({'file': entry['file'], 'path': path,
                                          'reason': 'no matching explicit Top-N requirement' if not candidates
                                          else 'conflicting Top-N count evidence', 'sources': candidates})
                        return
                    rules.append({'file': entry['file'], 'path': path, 'length': int(match[1]),
                                  'kind': 'array_length', 'sources': candidates,
                                  'template_line_start': block['line_start'],
                                  'template_line_end': block['line_end']})
            visit(tree, [])
    contracts['array_length_rules'] = rules
    contracts['array_length_uncovered'] = uncovered
    return contracts


def add_array_length_tests(contracts, source, generated):
    rules = []
    for index, rule in enumerate(contracts.get('array_length_rules', [])):
        name = 'test_' + re.sub(r'\W', '_', pathlib.PurePosixPath(rule['file']).stem) + '_array_length_' + str(index)
        generated.append(name)
        source.extend([f'# Explicit array length requirement: {rule["sources"][0]["line_start"]}',
                       f'def {name}():', f'    value = _load({rule["file"]!r})',
                       f'    for key in {rule["path"]!r}:',
                       '        assert isinstance(value, dict) and key in value, f"Missing array path key: {key}"',
                       '        value = value[key]',
                       '    assert isinstance(value, list), "Expected JSON array"',
                       f'    assert len(value) == {rule["length"]}, f"Expected {rule["length"]} elements, got {{len(value)}}"', ''])
        rules.append({**rule, 'test': name})
    return rules


def generate_json_pytest(directory, contracts, *, template_structures=False,
                         suite_name="test_schema.py", report_name="schema_generation.json"):
    directory = pathlib.Path(directory)
    source = ['import json', 'import os', 'from pathlib import Path', '',
              'OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/app/output"))', '',
              'def _load(name):', '    path = OUTPUT_DIR / name',
              '    assert path.is_file(), f"Missing {path}"',
              '    return json.loads(path.read_text())', '']
    generated, skipped = [], []
    partial_json_rules = []
    legacy_type_replacements = []
    csv_rules, csv_uncovered = [], []
    for entry in contracts['files']:
        if entry['format'] != 'json':
            continue
        for block_index in entry['block_indices']:
            block = contracts['blocks'][block_index]
            if block['kind'] != 'fenced_structure':
                continue
            body = None
            try:
                raw_lines = block['raw'].splitlines(keepends=True)
                if len(raw_lines) < 3 or not re.fullmatch(r'\s*(`{3,}|~{3,})\s*', raw_lines[-1].strip()):
                    raise ValueError('unclosed structure fence')
                body = ''.join(raw_lines[1:-1])
                def placeholder(match):
                    kind = match.group(1).strip()
                    if kind not in ('int', 'float', 'bool', 'str'):
                        raise ValueError('unsupported placeholder: ' + kind)
                    return json.dumps('__TYPE_' + kind + '__')
                cooked = re.sub(r'(?<!")<([^<>\n]+)>(?!")', placeholder, body)
                tree = json.loads(cooked)
                if not isinstance(tree, dict):
                    raise ValueError('only explicit JSON object templates are supported')
                nested = []
                required_types = {}
                def walk(node, path):
                    if any('<' in key or '>' in key for key in node):
                        raise ValueError('dynamic keys need a later schema interpretation step')
                    if path:
                        nested.append((path, list(node)))
                    for key, value in node.items():
                        if isinstance(value, dict):
                            walk(value, path + [key])
                        elif not path:
                            if isinstance(value, str) and value.startswith('__TYPE_') and value.endswith('__'):
                                kind = value[7:-2]
                            elif template_structures and isinstance(value, str) and value in ('<int>', '<float>', '<bool>', '<str>'):
                                kind = value[1:-1]
                                if kind != 'str':
                                    legacy_type_replacements.append({'file': entry['file'], 'path': [key],
                                                                     'line_start': block['line_start'],
                                                                     'source_placeholder': value, 'old_type': 'str',
                                                                     'new_type': kind,
                                                                     'reason': 'quoted type placeholder denotes a type, not a literal string'})
                            else:
                                kind = {str: 'str', int: 'int', float: 'float', bool: 'bool', list: 'list', type(None): 'NoneType'}[type(value)]
                            if kind == 'NoneType':
                                raise ValueError('null type not supported')
                            required_types[key] = '(int, float)' if kind == 'float' else kind
                walk(tree, [])
                stem = re.sub(r'\W', '_', pathlib.PurePosixPath(entry['file']).stem)
                test_name = f'test_{stem}_schema'
                if test_name in generated:
                    test_name += '_' + str(block_index)
                generated.append(test_name)
                source += [f'# Copied instruction structure: lines {block["line_start"]}-{block["line_end"]}',
                           f'def {test_name}():', f'    data = _load({entry["file"]!r})',
                           f'    required_keys = {list(tree)!r}',
                           '    for key in required_keys:',
                           '        assert key in data, f"Missing key: {key}"']
                if required_types:
                    literal = '{' + ', '.join(repr(k) + ': ' + t for k, t in required_types.items()) + '}'
                    source += [f'    required = {literal}', '    for key, types in required.items():',
                               '        assert isinstance(data[key], types), f"{key}: type={type(data[key]).__name__}, expected {types}"']
                for path, keys in nested:
                    expression = 'data' + ''.join('[' + repr(key) + ']' for key in path)
                    source += [f'    report = {expression}', f'    report_keys = set({keys!r})',
                               '    assert set(report.keys()) >= report_keys, f"Missing nested keys: {report_keys - set(report.keys())}"']
                source += ['']
            except (ValueError, TypeError, KeyError) as exc:
                skipped_item = {'file': entry['file'], 'line_start': block['line_start'], 'reason': str(exc)}
                skipped.append(skipped_item)
                try:
                    if body is None:
                        raise ValueError('no closed template body')
                    keys = template_root_keys(body)
                except ValueError as recovery_error:
                    skipped_item['root_key_recovery'] = str(recovery_error)
                    continue
                stem = re.sub(r'\W', '_', pathlib.PurePosixPath(entry['file']).stem)
                test_name = f'test_{stem}_root_keys'
                if test_name in generated:
                    test_name += '_' + str(block_index)
                generated.append(test_name)
                skipped_item['coverage'] = 'partial: root keys only; remaining template checks uncovered'
                partial_json_rules.append({'file': entry['file'], 'required_keys': keys,
                                           'line_start': block['line_start'], 'line_end': block['line_end'],
                                           'source_raw': block['raw'], 'test': test_name,
                                           'uncovered_reason': str(exc)})
                source += [f'# Partial template coverage: lines {block["line_start"]}-{block["line_end"]}',
                           f'def {test_name}():', f'    data = _load({entry["file"]!r})',
                           '    assert isinstance(data, dict), "Expected JSON root object"',
                           f'    required_keys = {keys!r}',
                           '    for key in required_keys:',
                           '        assert key in data, f"Missing key: {key}"', '']
    for entry in contracts['files']:
        if entry['format'] != 'csv':
            continue
        candidates = []
        ambiguous_tables = []
        for block_index in entry['block_indices']:
            block = contracts['blocks'][block_index]
            raw = block['raw']
            if block['kind'] == 'schema_table':
                try:
                    columns = markdown_csv_columns(raw)
                except ValueError as exc:
                    ambiguous_tables.append({'line_start': block['line_start'], 'reason': str(exc)})
                else:
                    candidates.append((columns, block))
                continue
            if block['kind'] == 'fenced_structure':
                raw_lines = raw.splitlines()
                if len(raw_lines) < 3 or not re.fullmatch(r'\s*(`{3,}|~{3,})\s*', raw_lines[-1]):
                    continue
                header = raw_lines[1]
            elif block['kind'] == 'indented_csv':
                header = re.sub(r'^(?: {4}|\t)', '', raw.splitlines()[0])
            elif block['kind'] == 'inline_csv':
                header = raw[1:-1]
            else:
                continue
            try:
                columns = next(csv.reader([header], skipinitialspace=True, strict=True))
            except (csv.Error, StopIteration):
                continue
            if template_structures:
                ellipsis = [i for i, name in enumerate(columns) if name in ('...', '…')]
                literal_columns = [name for name in columns if name not in ('...', '…')]
                if (not literal_columns or any(not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.+-]*', name)
                                               for name in literal_columns)):
                    csv_uncovered.append({'file': entry['file'], 'line_start': block['line_start'],
                                          'line_end': block['line_end'], 'source_raw': block['raw'],
                                          'reason': 'copied CSV candidate is not an unambiguous literal header; no check generated'})
                    continue
                if ellipsis:
                    csv_uncovered.append({'file': entry['file'], 'line_start': block['line_start'],
                                          'line_end': block['line_end'], 'source_raw': block['raw'],
                                          'reason': 'CSV header ellipsis: omitted column names and positions are uncovered; no sequence expansion'})
                    columns = literal_columns
                    block = {**block, 'partial_header': True}
            if (not columns or any(not name or '<' in name or '>' in name or '...' in name for name in columns)
                    or len(set(columns)) != len(columns)):
                continue
            candidates.append((columns, block))
        unique = {tuple(columns) for columns, _ in candidates}
        if ambiguous_tables:
            csv_uncovered.append({'file': entry['file'], 'reason': 'ambiguous copied Markdown column table',
                                  'sources': ambiguous_tables})
            continue
        if len(unique) != 1:
            csv_uncovered.append({'file': entry['file'], 'reason':
                                  'no unambiguous literal CSV header' if not unique else 'conflicting copied CSV headers'})
            continue
        columns, block = candidates[0]
        test_name = 'test_' + re.sub(r'\W', '_', pathlib.PurePosixPath(entry['file']).stem) + '_csv_header'
        if test_name in generated:
            test_name += '_' + str(len(generated))
        generated.append(test_name)
        mode = block.get('header_context', {}).get('mode', 'required') if template_structures else 'required'
        if block.get('partial_header'):
            mode = 'required'
        csv_rules.append({'file': entry['file'], 'columns': columns, 'mode': mode,
                          **({'header_context': block['header_context']} if 'header_context' in block else {}),
                          'line_start': block['line_start'], 'line_end': block['line_end'],
                          'source_raw': block['raw'], 'test': test_name})
        source += [f'# Copied instruction structure: lines {block["line_start"]}-{block["line_end"]}',
                   f'def {test_name}():', '    import csv',
                   f'    path = OUTPUT_DIR / {entry["file"]!r}',
                   '    assert path.is_file(), f"Missing {path}"',
                   '    with path.open(newline="", encoding="utf-8-sig") as handle:',
                   '        header = next(csv.reader(handle, strict=True), [])',
                   f'    required = {columns!r}',
                   '    missing = [column for column in required if column not in header]',
                   '    assert not missing, f"{path.name}: missing columns {missing}; actual header {header}"', '']
        if mode == 'exact':
            source += ['    assert header == required, f"{path.name}: expected exact columns/order {required}; actual header {header}"', '']
    template_rules, template_uncovered = (add_template_structure_tests(directory, contracts, source, generated)
                                           if template_structures else ([], []))
    array_length_rules = add_array_length_tests(contracts, source, generated) if template_structures else []
    text = '\n'.join(source) + '\n'
    (directory / suite_name).write_text(text)
    report = {'generated_tests': generated, 'skipped_templates': skipped,
              'csv_header_rules': csv_rules, 'csv_uncovered': csv_uncovered,
              'partial_json_rules': partial_json_rules,
              'legacy_type_replacements': legacy_type_replacements,
              'array_length_rules': array_length_rules,
              'array_length_uncovered': contracts.get('array_length_uncovered', []),
              'template_structure_rules': template_rules, 'template_uncovered': template_uncovered,
              'scope': 'JSON root keys/types, nested required keys and literal CSV required columns; no value checks'}
    if template_structures:
        report['legacy_skipped_templates'] = skipped
        recovered = {(rule['file'], rule['line_start']) for rule in template_rules}
        report['skipped_templates'] = [item for item in skipped
                                       if (item['file'], item['line_start']) not in recovered]
        report['scope'] += '; v8.3 recursive parallel-example types and keys; no inferred length/range constraints'
        if array_length_rules:
            report['scope'] += '; explicit sourced array lengths'
    (directory / report_name).write_text(json.dumps(report, indent=2))
    return report


def generate_structural_validity_pytest(directory, contracts):
    report = generate_json_pytest(
        directory, contracts, template_structures=True,
        suite_name='structural_validity_test.py', report_name='structural_validity.json')
    report.update(layer=2, name='Structural validity', scopes=['structural_validity'])
    (pathlib.Path(directory) / 'structural_validity.json').write_text(json.dumps(report, indent=2))
    return report
