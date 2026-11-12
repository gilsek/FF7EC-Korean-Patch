"""Assemble the distributable Korean patch (unzip on top of a game folder that already has the offline server).
Takes the BepInEx/AutoTranslator framework from the installed game (list: backup/mod_installed_files.txt),
our plugins/translations from the repo's build outputs, and the font patcher from patcher/FontPatch.
Never ships game files: fonts are patched on the user's PC by ko_patch/FontPatch.exe (called by FF7EC_KO.exe).
usage: python -I tools/make_dist.py VERSION      -> dist/FF7EC_KO_<VERSION>/ and dist/FF7EC_KO_<VERSION>.zip"""
import hashlib, os, shutil, subprocess, sys, zipfile
sys.stdout.reconfigure(encoding='utf-8')
B = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
G = r"C:\Program Files (x86)\Steam\steamapps\common\FF7EC"
VER = sys.argv[1]
OUT = os.path.join(B, 'dist', 'FF7EC_KO_' + VER)
ZIP = OUT + '.zip'
FONT = os.path.join(B, 'fonts', 'pretendard', 'src', 'public', 'static', 'Pretendard-Medium.otf')
FONT_LICENSE = os.path.join(B, 'fonts', 'pretendard', 'src', 'LICENSE.txt')
FONTPATCH_BIN = os.path.join(B, 'patcher', 'FontPatch', 'bin', 'Release', 'net48')
LAUNCHER_BIN = os.path.join(B, 'launcher', 'bin', 'Release', 'net48')
DIST_DOCS = os.path.join(B, 'dist_files')      # README / uninstall / licenses kept in the repo
TEXT = r'BepInEx\Translation\ko\Text'

# our build outputs -> path inside the package
OURS = {
    r'work\at_out_v2_ja\story.txt': TEXT + r'\story.txt',
    r'work\at_ui_v2\ui.txt': TEXT + r'\ui.txt',
    r'work\at_ui_ja_v2\ui.txt': TEXT + r'\ui_ja.txt',
    r'work\moviesub\zz_moviesub.txt': TEXT + r'\zz_moviesub.txt',
    r'translations\zz_extra.txt': TEXT + r'\zz_extra.txt',
    r'translations\zz_tips.txt': TEXT + r'\zz_tips.txt',
    r'work\storyko_v2\story_ko.tsv': r'BepInEx\plugins\StoryKo\story_ko.tsv',
    r'plugin\StoryKo\bin\Release\net6.0\StoryKo.dll': r'BepInEx\plugins\StoryKo\StoryKo.dll',
    r'plugin\TypewriterFix\bin\Release\net6.0\TypewriterFix.dll': r'BepInEx\plugins\TypewriterFix\TypewriterFix.dll',
}
# config files: start from the installed copy, then force distribution values
CONFIGS = {
    r'BepInEx\config\AutoTranslatorConfig.ini': [('Endpoint=CustomTranslate', 'Endpoint='),
                                                  ('Url=http://127.0.0.1:5005/', 'Url=')],
    r'BepInEx\config\BepInEx.cfg': [],
    r'BepInEx\config\ff7ec.ko.storyko.cfg': [('LogDetail = true', 'LogDetail = false')],
    r'BepInEx\config\ff7ec.ko.typewriterfix.cfg': [],
}


def copy(src, rel):
    dst = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)


def main():
    if os.path.exists(OUT):
        sys.exit('already exists, remove it first: ' + OUT)
    # 1. third-party framework, exactly as installed and tested
    for line in open(os.path.join(B, 'backup', 'mod_installed_files.txt'), encoding='utf-8'):
        rel = line.strip().removeprefix('./').replace('/', '\\')
        if not rel or rel in CONFIGS:
            continue
        copy(os.path.join(G, rel), rel)
    # 2. configs with distribution values
    for rel, reps in CONFIGS.items():
        s = open(os.path.join(G, rel), encoding='utf-8-sig').read()
        for a, b in reps:
            assert a in s or any(l.rstrip('\r') == b for l in s.split('\n')), (rel, a)   # or already set
            s = s.replace(a, b)
        dst = os.path.join(OUT, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'w', encoding='utf-8', newline='').write(s)
    # 3. our plugins and translations
    for src, rel in OURS.items():
        copy(os.path.join(B, src), rel)
    for fn in ('_Preprocessors.txt', '_Postprocessors.txt', '_Substitutions.txt'):
        open(os.path.join(OUT, TEXT, fn), 'w', encoding='utf-8').write('')
    subprocess.run([sys.executable, '-I', os.path.join(B, 'tools', 'at_nows_variants.py'),
                    os.path.join(OUT, TEXT), os.path.join(OUT, TEXT, 'zz_nows.txt')], check=True)
    subprocess.run([sys.executable, '-I', os.path.join(B, 'tools', 'at_regex_variants.py'),
                    os.path.join(OUT, TEXT), os.path.join(OUT, TEXT, 'zz_regex.txt')], check=True)
    # 4. launcher and font patcher
    for fn in ('FF7EC_KO.exe', 'FF7EC_KO.exe.config'):
        copy(os.path.join(LAUNCHER_BIN, fn), fn)
    for root, _, files in os.walk(FONTPATCH_BIN):
        for fn in files:
            if fn.endswith(('.pdb', '.xml')):
                continue
            p = os.path.join(root, fn)
            copy(p, os.path.join('ko_patch', os.path.relpath(p, FONTPATCH_BIN)))
    copy(FONT, r'ko_patch\Pretendard-Medium.otf')
    copy(FONT_LICENSE, r'ko_patch\Pretendard-LICENSE.txt')
    # 5. docs, uninstaller, licenses
    for root, _, files in os.walk(DIST_DOCS):
        for fn in files:
            p = os.path.join(root, fn)
            copy(p, os.path.relpath(p, DIST_DOCS))
    # 6. file list (used by the uninstaller) + zip
    rels = []
    for root, _, files in os.walk(OUT):
        for fn in files:
            rels.append(os.path.relpath(os.path.join(root, fn), OUT))
    rels.sort()
    with open(os.path.join(OUT, 'ko_patch', 'files.txt'), 'w', encoding='utf-8', newline='\r\n') as f:
        f.write('\n'.join(rels + [r'ko_patch\files.txt']) + '\n')
    with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for root, _, files in os.walk(OUT):
            for fn in files:
                p = os.path.join(root, fn)
                z.write(p, os.path.relpath(p, OUT))
    total = sum(os.path.getsize(os.path.join(OUT, r)) for r in rels)
    h = hashlib.sha256(open(ZIP, 'rb').read()).hexdigest()
    print('files', len(rels) + 1, 'unpacked %.1f MB' % (total / 1e6), 'zip %.1f MB' % (os.path.getsize(ZIP) / 1e6))
    print('sha256', h)


if __name__ == '__main__':
    main()
