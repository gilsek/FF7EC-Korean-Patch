"""Build work/tl/speakers.tsv (key, speaker) for story TXT_ keys.

Method (see work/speaker_research.md):
  - Lua dumps from tools/dump_lua_full.py in work/story_lua/**.lua
  - Dialogue calls: any talk* function with a TXT key (actor is the first argument, e.g. talk2d, talk3d,
    talkSimple3dNoWait, talkCustom2d). talkNarration and first arg "" have no speaker (left blank).
  - Actor variable is bound by `local x=getCharacter(N)` (or `x=getCharacter(N)`), tracked in text
    order inside each `function` block.
  - N is the Lua character id = field 0 of master CharacterNovelSet (work/master/CharacterNovelSet.bin).
  - Name = English text of that CharacterNovelSet row in work/tl/ui.tsv (file == CharacterNovelSet).
usage: python build_speakers.py [lua_dir]
"""
import collections, csv, glob, os, re, sys
import msgpack

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
LUA_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'work', 'story_lua')
MASTER = os.path.join(ROOT, 'work', 'master', 'CharacterNovelSet.bin')
UI = os.path.join(ROOT, 'work', 'tl', 'ui.tsv')
STORY = os.path.join(ROOT, 'work', 'tl', 'story.tsv')
OUT = os.path.join(ROOT, 'work', 'tl', 'speakers.tsv')
REPORT_STATS = os.path.join(ROOT, 'work', 'speakers_stats.txt')

ASSIGN = re.compile(r'(?<![\w.])(?:local\s+)?(\w+)\s*=\s*getCharacter\(\s*(\d+)\s*[,)]')
CALL = re.compile(r'(?<![\w.])(talk\w*)\(([^()]*)\)')
FUNC = re.compile(r'(?<![\w.])function\b')
KEY = re.compile(r'\bTXT_[A-Za-z0-9_]+')


def load_novelset_names():
    rows = msgpack.unpackb(open(MASTER, 'rb').read(), raw=False, strict_map_key=False)
    lua2nov = {}
    for r in rows:
        lua_id, nov_id = r[0], str(r[1])
        lua2nov.setdefault(lua_id, nov_id)
    nov2name = {}
    with open(UI, encoding='utf-8') as f:
        for rec in csv.DictReader(f, delimiter='\t'):
            if rec['file'] == 'CharacterNovelSet' and rec['en']:
                nov2name.setdefault(rec['id'], rec['en'])
    return lua2nov, nov2name


SIMPLE = re.compile(r'(?<![\w.])local\s+([\w\s,]+?)\s*=\s*simpleSetting\(([^()]*)\)')
TABLE = re.compile(r'(?<![\w.])(?:local\s+)?(\w+)\s*=\s*\{([^{}]*)\}')


def scan_file(text):
    """yield (key, lua_id or None, kind) for each talk* call with a TXT key.
    kind: literal | var (bound by getCharacter) | simple (bound by simpleSetting(tables...) return order,
    inferred) | narration | unbound."""
    events = []
    for m in ASSIGN.finditer(text):
        events.append((m.start(), 'a', m.group(1), m.group(2)))
    for m in TABLE.finditer(text):
        ids = [x.strip() for x in m.group(2).split(',') if x.strip()]
        if ids and all(x.isdigit() for x in ids):
            events.append((m.start(), 't', m.group(1), ids))
    for m in SIMPLE.finditer(text):
        events.append((m.start(), 's', m.group(1), m.group(2)))
    for m in FUNC.finditer(text):
        events.append((m.start(), 'f', None, None))
    for m in CALL.finditer(text):
        events.append((m.start(), 'c', m.group(1), m.group(2)))
    events.sort(key=lambda e: e[0])
    bind = {}     # var -> (lua id, kind)
    tables = {}   # var -> [ids]
    for _, kind, a, b in events:
        if kind == 'f':
            bind = {}
            tables = {}
        elif kind == 'a':
            bind[a] = (b, 'var')
        elif kind == 't':
            tables[a] = b
        elif kind == 's':
            # simpleSetting(t1, t2, camera, t3) returns one actor per id, in table order
            names = [x.strip() for x in a.split(',') if x.strip()]
            flat = []
            for arg in [x.strip() for x in b.split(',')]:
                if arg in tables:
                    flat += tables[arg]
            if flat and len(flat) == len(names):
                for n, lid in zip(names, flat):
                    bind[n] = (lid, 'simple')
            else:
                for n in names:
                    bind.pop(n, None)
        else:
            fn = a
            if not fn.startswith('talk'):
                continue
            args = [x.strip() for x in b.split(',')]
            keys = [x for x in args if KEY.fullmatch(x)]
            if not keys:
                continue
            actor = args[0]
            if fn == 'talkNarration' or actor == '""':
                yield keys[0], None, 'narration'
                continue
            if actor.isdigit():
                yield keys[0], actor, 'literal'
            elif actor in bind:
                lid, k2 = bind[actor]
                yield keys[0], lid, k2
            else:
                yield keys[0], None, 'unbound'


def main():
    lua2nov, nov2name = load_novelset_names()
    keys_in_story = []
    with open(STORY, encoding='utf-8') as f:
        for rec in csv.DictReader(f, delimiter='\t'):
            keys_in_story.append(rec['key'])
    story_set = set(keys_in_story)

    found = {}          # key -> (speaker name, lua id)
    conflicts = collections.Counter()
    kinds = collections.Counter()
    unresolved_ids = collections.Counter()
    no_name_ids = collections.Counter()
    for p in glob.glob(os.path.join(LUA_DIR, '**', '*.lua'), recursive=True):
        with open(p, encoding='utf-8') as f:
            text = f.read()
        for key, lid, kind in scan_file(text):
            kinds[kind] += 1
            if kind == 'narration' or lid is None:
                name = ''
            else:
                nov = lua2nov.get(int(lid))
                if nov is None:
                    unresolved_ids[lid] += 1
                    name = ''
                else:
                    name = nov2name.get(nov, '')
                    if not name:
                        no_name_ids[lid] += 1
            if key in found:
                if found[key][0] != name:
                    conflicts[key] += 1
                if found[key][0] == '' and name:
                    found[key] = (name, lid)
            else:
                found[key] = (name, lid)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
        w.writerow(['key', 'speaker'])
        for k in keys_in_story:
            w.writerow([k, found.get(k, ('', None))[0]])

    total = len(keys_in_story)
    with_sp = sum(1 for k in keys_in_story if found.get(k, ('',))[0])
    seen = sum(1 for k in keys_in_story if k in found)
    extra = [k for k in found if k not in story_set]
    spk = collections.Counter(found[k][0] for k in keys_in_story if found.get(k, ('',))[0])
    lines = [
        f'story keys: {total}',
        f'keys referenced by a dialogue call in Lua: {seen}',
        f'keys with speaker name: {with_sp}',
        f'keys referenced but not in story.tsv: {len(extra)}',
        f'call kinds: {dict(kinds)}',
        f'keys with conflicting speakers across calls: {len(conflicts)}',
        f'calls with unbound actor (no getCharacter in scope): {kinds.get("unbound", 0)}',
        f'lua ids not in CharacterNovelSet: {dict(unresolved_ids)}',
        f'lua ids with no English name: {dict(no_name_ids)}',
        'top speakers:',
    ]
    lines += [f'  {n}\t{c}' for n, c in spk.most_common(15)]
    txt = '\n'.join(lines) + '\n'
    with open(REPORT_STATS, 'w', encoding='utf-8') as f:
        f.write(txt)
    print(txt)


if __name__ == '__main__':
    main()
