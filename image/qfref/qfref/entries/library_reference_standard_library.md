Python 3.13.15 is installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

# LibraryReference: Python standard library: local files, strict JSON and scalar mathematics

Setup:
```python
import csv, io, json, math, os, tempfile
from pathlib import Path
from datetime import datetime, timezone
folder=Path(tempfile.mkdtemp())
```

These examples use the standard library for local computation. Third-party numerical packages are not standard-library modules; an explicit standard-library-only requirement excludes them even when installed.

- `json.load(fp)` / `json.loads(s)` return Python objects; `json.dump(obj,fp,allow_nan=False)` / `json.dumps(obj,allow_nan=False)` return None / str. JSON null becomes None and true/false become bool. Standard json does not automatically serialize NumPy values or arrays.
```python
payload={'number':2.75,'missing':None,'valid':True}; encoded=json.dumps(payload,allow_nan=False); assert json.loads(encoded)==payload
with open(folder/'sample.json','w',encoding='utf-8') as stream: json.dump(payload,stream,allow_nan=False)
with open(folder/'sample.json',encoding='utf-8') as stream: assert json.load(stream)==payload
```
- `csv.DictReader(f)` iterates row dictionaries; numbers are strings by default. `csv.DictWriter(f,fieldnames=...)` returns a writer; writeheader/writerow return the underlying write result. Open files with newline='' to avoid extra platform-dependent blank lines. Do not split quoted CSV fields manually at commas.
```python
text=io.StringIO(newline=''); writer=csv.DictWriter(text,fieldnames=['kind','amount']); writer.writeheader(); writer.writerow({'kind':'quoted, sample','amount':2.75}); text.seek(0); row=next(csv.DictReader(text)); assert row['kind']=='quoted, sample' and float(row['amount'])==2.75
```
- `math.log/exp/sqrt/log1p/floor/ceil/atanh` operate on scalars; floor/ceil return int. log1p is stable near zero. atanh requires (-1,1); handle correlations at the endpoints according to the definition rather than clipping arbitrarily. `math.isfinite(x)` returns bool.
```python
assert math.isclose(math.exp(math.log(3.)),3.); assert math.sqrt(9.)==3.; assert math.floor(-1.2)==-2 and math.ceil(-1.2)==-1; assert math.isclose(math.log1p(1e-12),1e-12,rel_tol=1e-10); assert math.isfinite(math.atanh(.4))
```
- `os.environ.get(key,default=None)` returns a string or default; convert numerical settings explicitly. `os.makedirs(name,exist_ok=False)` returns None and recursively creates directories; use exist_ok=True for repeated creation. `open(file,mode='r',encoding=...)` returns a file object; close it with a with block.
```python
os.makedirs(folder/'nested',exist_ok=True); assert (folder/'nested').is_dir(); assert os.environ.get('__LIBREF_MISSING_VARIABLE__','fallback')=='fallback'
```
- `itertools.combinations(iterable,r)` returns an iterator of tuples selecting r distinct input positions while preserving input order. It is not a permutation and does not produce reversed duplicate pairs. Repeated input values can still produce equal-valued tuples from different positions; do not first convert to a set and destroy required ordering.
```python
from itertools import combinations
pairs=list(combinations(['west','north','east'],2)); assert pairs==[('west','north'),('west','east'),('north','east')]
```
- `xml.etree.ElementTree.parse(source)` returns ElementTree; `.getroot()` returns Element; `fromstring(text)` returns Element. `Element.find/findall/findtext(path,namespaces=None)` return the first Element, a list of elements, or text/default respectively. Use a namespace-prefix mapping or `{URI}tag`; do not assume namespace-free XML. A missing find returns None; check identity rather than element truthiness. The standard library does not implement full XPath.
```python
import xml.etree.ElementTree as ET
xml_text='<root xmlns="urn:demo"><item code="x"><amount>2.75</amount></item><item code="y" /></root>'; xml_path=folder/'sample.xml'; xml_path.write_text(xml_text,encoding='utf-8'); tree=ET.parse(xml_path); root=tree.getroot(); ns={'d':'urn:demo'}; assert len(root.findall('d:item',ns))==2; first=root.find('d:item',ns); assert first is not None and first.get('code')=='x'; assert float(first.findtext('d:amount',namespaces=ns))==2.75; assert root.find('item') is None; assert ET.fromstring(xml_text).tag=='{urn:demo}root'
```
Parse XML references, footnotes, dates and amounts into structure before applying definitions. Do not replace tree parsing with regex or treat missing elements as zero amounts. Read local inputs only; XML identifiers do not authorize guessing external files or network locations.

- `datetime.date()` returns datetime.date; convert to the business timezone before extracting the date. Python built-ins sum/min/max/abs operate on iterables or scalars. For axis-based reductions over multidimensional NumPy arrays, explicitly use array APIs.
```python
stamp=datetime(2022,7,9,8,tzinfo=timezone.utc); assert stamp.date().isoformat()=='2022-07-09'; assert sum([2,3])==5 and min(2,3)==2 and max(2,3)==3 and abs(-2)==2
```

## Version check: forms that fail in this version

### Removed or renamed forms
None among the verified calls shown.

### Unavailable or wrong-object forms
None among the verified calls shown.
