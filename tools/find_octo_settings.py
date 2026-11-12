"""Scan data.unity3d for MonoBehaviours whose script looks like Octo settings and dump their typetree."""
import UnityPy, sys, json

env = UnityPy.load(r"C:\Program Files (x86)\Steam\steamapps\common\FF7EC\FF7EC_Data\data.unity3d")
for obj in env.objects:
    if obj.type.name != 'MonoBehaviour':
        continue
    try:
        mb = obj.read()
        script = mb.m_Script.read() if mb.m_Script else None
        name = script.m_ClassName if script else '?'
    except Exception:
        continue
    if 'octo' in name.lower() or 'octo' in (getattr(mb, 'm_Name', '') or '').lower():
        print('==', name, getattr(mb, 'm_Name', ''), obj.path_id)
        raw = obj.get_raw_data()
        print(raw[:600])
