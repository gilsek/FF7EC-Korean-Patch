"""Swap the second copy of FOT-SkipProN-D that lives in FF7EC_Data/data.unity3d (sharedassets0.assets).
Battle HUD text (character names, buttons) uses this copy, so Hangul showed as tofu there.
Always starts from the pristine backup/orig/data.unity3d (made on first run).
usage: python font_swap_data.py FONT.(otf|ttf) [OUT]   (OUT defaults to the game file)"""
import os, shutil, sys
import UnityPy

HERE = os.path.dirname(os.path.abspath(__file__))
DST = r"C:\Program Files (x86)\Steam\steamapps\common\FF7EC\FF7EC_Data\data.unity3d"
ORIG = os.path.join(HERE, '..', 'backup', 'orig', 'data.unity3d')


def main(font, out=DST):
    if not os.path.exists(ORIG):
        shutil.copy2(DST, ORIG)
    env = UnityPy.load(ORIG)
    n = 0
    for o in env.objects:
        if o.type.name == 'Font':
            f = o.read()
            if f.m_Name != 'FOT-SkipProN-D':
                continue
            f.m_FontData = list(open(font, 'rb').read())
            f.save(); n += 1
    assert n == 1, n
    data = env.file.save(packer='lz4')
    open(out, 'wb').write(data)
    print('swapped ->', os.path.basename(font), len(data), 'bytes ->', out)


if __name__ == '__main__':
    main(*sys.argv[1:3])
