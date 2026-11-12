using System;
using System.Collections.Generic;
using System.Reflection;
using System.Text.RegularExpressions;
using BepInEx;
using BepInEx.Configuration;
using BepInEx.Logging;
using BepInEx.Unity.IL2CPP;
using HarmonyLib;
using Il2CppInterop.Runtime;
using Il2CppInterop.Runtime.Injection;
using Il2CppInterop.Runtime.InteropTypes;
using TMPro;

namespace TypewriterFix
{
    [BepInPlugin(PluginGuid, PluginName, PluginVersion)]
    [BepInDependency("gravydevsupreme.xunity.autotranslator")]
    public sealed class Plugin : BasePlugin
    {
        public const string PluginGuid = "ff7ec.ko.typewriterfix";
        public const string PluginName = "TypewriterFix";
        public const string PluginVersion = "3.0.0";

        internal static ManualLogSource Lg;
        internal static ConfigEntry<bool> EnabledCfg;
        internal static ConfigEntry<string> ModeCfg;
        internal static ConfigEntry<float> BaseIntervalCfg;
        internal static ConfigEntry<int> PunctPauseLongCfg;
        internal static ConfigEntry<int> PunctPauseShortCfg;
        internal static ConfigEntry<int> DebugLogCountCfg;

        public override void Load()
        {
            Lg = Log;

            EnabledCfg = Config.Bind("General", "Enabled", true,
                "true면 번역된 텍스트의 타자기 연출을 번역문 기준으로 다시 계산한다.");
            ModeCfg = Config.Bind("General", "Mode", "Smooth",
                "Smooth: 한국어 음절 단위로 일정한 속도로 타이핑(기본). Scale: 원문 글자 수 기준 비율 스케일(v1 방식). Instant: 번역 텍스트는 항상 연출 없이 전부 표시(99999).");
            BaseIntervalCfg = Config.Bind("Smooth", "BaseInterval", 0.03f,
                "Smooth: 게임 원문 글자 1개당 기본 간격(초). 초기값이며, 게임의 실제 틱 간격을 측정해 갱신한다.");
            PunctPauseLongCfg = Config.Bind("Smooth", "PunctPauseLong", 6,
                "Smooth: 방금 표시한 글자가 . ! ? 。 ！ ？ … 이면 다음 글자까지 기다리는 시간을 간격의 이 배수로 한다.");
            PunctPauseShortCfg = Config.Bind("Smooth", "PunctPauseShort", 3,
                "Smooth: 방금 표시한 글자가 , 、 ， 이면 다음 글자까지 기다리는 시간을 간격의 이 배수로 한다.");
            DebugLogCountCfg = Config.Bind("Debug", "DebugLogCount", 30,
                "처음 N번의 연출 이벤트를 Info 로그로 출력한다. 0이면 끔.");

            try
            {
                new Harmony(PluginGuid).PatchAll(typeof(Plugin).Assembly);
            }
            catch (Exception e)
            {
                Lg.LogError("TypewriterFix: Harmony patch failed: " + e);
            }

            try
            {
                ClassInjector.RegisterTypeInIl2Cpp<TypewriterDriver>();
                AddComponent<TypewriterDriver>();
                TypewriterScaler.DriverOk = true;
            }
            catch (Exception e)
            {
                Lg.LogError("TypewriterFix: driver start failed, Smooth falls back to Scale: " + e);
            }

            Lg.LogInfo("TypewriterFix " + PluginVersion + " loaded (mode=" + ModeCfg.Value
                + ", enabled=" + EnabledCfg.Value + ", driver=" + TypewriterScaler.DriverOk + ").");
        }
    }

    /// <summary>매 프레임 TypewriterScaler.Tick()을 호출하는 MonoBehaviour.</summary>
    public class TypewriterDriver : UnityEngine.MonoBehaviour
    {
        public TypewriterDriver(IntPtr handle) : base(handle)
        {
        }

        private void Update()
        {
            TypewriterScaler.Tick();
        }
    }

    [HarmonyPatch(typeof(TMP_Text), "maxVisibleCharacters", MethodType.Setter)]
    internal static class MaxVisibleCharactersSetterPatch
    {
        static void Prefix(TMP_Text __instance, ref int value)
        {
            TypewriterScaler.OnSetMaxVisible(__instance, ref value);
        }
    }

    [HarmonyPatch(typeof(TMP_Text), "maxVisibleCharacters", MethodType.Getter)]
    internal static class MaxVisibleCharactersGetterPatch
    {
        static void Postfix(TMP_Text __instance, ref int __result)
        {
            TypewriterScaler.OnGetMaxVisible(__instance, ref __result);
        }
    }

    internal static class TypewriterScaler
    {
        private const string AtAssemblyName = "XUnity.AutoTranslator.Plugin.Core";
        private const string AtExtensionsTypeName = "XUnity.AutoTranslator.Plugin.Core.Extensions.ComponentExtensions";
        private const int MaxWarnings = 5;
        private const int ResolveRetryMs = 1000;

        // Smooth 상수
        private const int SkipJump = 3;            // 한 번에 이만큼 이상 뛰면 스킵으로 본다
        private const float GapMeasureMax = 0.3f;  // 이보다 긴 틱 간격은 문장부호 정지로 보고 측정에서 제외
        private const float GapMin = 0.005f;
        private const float GapMax = 0.5f;
        private const int LeadLimit = 12;          // 게임 raw 기준 목표보다 이만큼 앞서면 기다린다
        private const int LagThreshold = 3;        // 목표보다 이만큼 뒤처지면 간격을 절반으로

        private static readonly Regex TagRegex = new Regex("<[^<>]+>", RegexOptions.Compiled);

        // key: TMP_Text 네이티브 포인터, value: 게임이 설정한 원래(스케일 전) raw 값
        private static readonly Dictionary<IntPtr, int> RawValues = new Dictionary<IntPtr, int>();

        // key: TMP_Text 네이티브 포인터, value: 직전 O/T 입력과 그 매핑 레이아웃(성능 캐시)
        private static readonly Dictionary<IntPtr, LayoutEntry> LayoutCache = new Dictionary<IntPtr, LayoutEntry>();

        // Smooth 모드 상태: key TMP_Text 네이티브 포인터
        private static readonly Dictionary<IntPtr, Track> Tracks = new Dictionary<IntPtr, Track>();
        private static readonly List<IntPtr> KeyBuffer = new List<IntPtr>();

        internal static bool DriverOk;
        // Update에서 우리가 maxVisibleCharacters를 쓸 때 Prefix가 재매핑하지 않도록 막는 플래그
        private static bool _writing;

        private static int _warnCount;
        private static int _scaleLogCount;

        // AT 리플렉션 캐시
        private static bool _atResolved;
        private static long _nextResolveTick;
        private static MethodInfo _getInfo;
        private static PropertyInfo _isTranslatedProp;
        private static PropertyInfo _originalTextProp;
        private static PropertyInfo _translatedTextProp;

        private sealed class Track
        {
            public TMP_Text Ui;
            public MapLayout Layout;
            public int RawLast = -1;      // 마지막으로 본 게임 raw (-1: 아직 없음)
            public float LastIncTime;     // raw가 마지막으로 증가한 시각(unscaled)
            public float GapEma;          // 게임 raw 글자 1개당 간격 추정치(초)
            public int Shown;             // 표시 중인 번역 글자 수(비공백 기준)
            public int Target;            // 게임 raw 기준 목표 번역 글자 수
            public bool Finished;         // 게임 raw >= 원문 길이
            public float Wait;            // 다음 글자 표시까지 남은 시간
            public int Applied;           // 마지막으로 TMP에 반영한 Shown

            public void ResetText(MapLayout layout, float now)
            {
                Layout = layout;
                RawLast = -1;
                LastIncTime = now;
                Shown = 0;
                Target = 0;
                Finished = false;
                Wait = 0f;
                Applied = 0;
                // GapEma는 같은 TMP 객체에서 학습된 값이므로 유지한다
            }
        }

        public static void OnSetMaxVisible(TMP_Text ui, ref int value)
        {
            if (_writing)
            {
                return;
            }

            IntPtr key = IntPtr.Zero;
            try
            {
                key = ((Il2CppObjectBase)ui).Pointer;

                bool smooth = IsSmoothMode();
                if (!Plugin.EnabledCfg.Value || value < 0 || (value == 0 && !smooth))
                {
                    Forget(key);
                    return;
                }

                object info = GetInfo(ui);
                if (info == null || !IsTranslated(info))
                {
                    Forget(key);
                    return;
                }

                string originalText = _originalTextProp.GetValue(info) as string ?? string.Empty;
                string translatedText = _translatedTextProp.GetValue(info) as string ?? ui.text ?? string.Empty;

                MapLayout layout = GetLayout(key, originalText, translatedText);
                if (layout.N0 <= 0 || layout.N1 <= 0)
                {
                    Forget(key);
                    return;
                }

                int raw = value;

                if (smooth)
                {
                    SmoothSet(ui, key, layout, raw, ref value);
                    return;
                }

                bool instant = string.Equals(Plugin.ModeCfg.Value?.Trim(), "Instant", StringComparison.OrdinalIgnoreCase);

                int n0;
                int n1;
                int mapped = layout.Map(raw, out n0, out n1);
                int newValue = (instant || raw >= layout.O.Length) ? 99999 : mapped;

                RawValues[key] = raw;
                value = newValue;

                if (_scaleLogCount < Plugin.DebugLogCountCfg.Value)
                {
                    _scaleLogCount++;
                    Plugin.Lg.LogInfo("TypewriterFix: raw " + raw + " -> " + newValue
                        + " n0=" + n0 + " n1=" + n1 + " N0=" + layout.N0 + " N1=" + layout.N1
                        + " \"" + Head(layout.O, 10) + "\"");
                }
            }
            catch (Exception e)
            {
                Forget(key);
                Warn("OnSetMaxVisible failed", e);
            }
        }

        private static bool IsSmoothMode()
        {
            if (!DriverOk)
            {
                return false;
            }
            string m = Plugin.ModeCfg.Value?.Trim();
            return !string.Equals(m, "Scale", StringComparison.OrdinalIgnoreCase)
                && !string.Equals(m, "Instant", StringComparison.OrdinalIgnoreCase);
        }

        /// <summary>
        /// Smooth 모드의 setter 처리. 게터는 raw를 돌려주고(RawValues), TMP에 넣을 값은 현재 표시 글자 수 기준이다.
        /// 실제 글자 증가는 Tick()이 담당한다.
        /// </summary>
        private static void SmoothSet(TMP_Text ui, IntPtr key, MapLayout layout, int raw, ref int value)
        {
            float now = UnityEngine.Time.unscaledTime;

            Track t;
            if (!Tracks.TryGetValue(key, out t))
            {
                t = new Track { GapEma = Plugin.BaseIntervalCfg.Value };
                Tracks[key] = t;
            }
            t.Ui = ui;

            // 텍스트가 바뀌었거나 raw가 줄었으면(새 대사) 표시 상태를 리셋
            if (!ReferenceEquals(t.Layout, layout) || raw < t.RawLast)
            {
                t.ResetText(layout, now);
            }

            RawValues[key] = raw;

            bool skip = raw >= 99999 || (t.RawLast >= 0 && raw - t.RawLast >= SkipJump);
            if (skip)
            {
                // 스킵: 즉시 전부 표시
                t.Shown = layout.N1;
                t.Target = layout.N1;
                t.Finished = true;
                t.Wait = 0f;
            }
            else
            {
                if (raw > t.RawLast)
                {
                    if (t.RawLast >= 0 && raw == t.RawLast + 1)
                    {
                        float dt = now - t.LastIncTime;
                        if (dt > 0f && dt <= GapMeasureMax)
                        {
                            float g = 0.7f * t.GapEma + 0.3f * dt;
                            t.GapEma = Math.Min(Math.Max(g, GapMin), GapMax);
                        }
                    }
                    t.LastIncTime = now;
                }

                t.Finished = raw >= layout.O.Length;
                t.Target = layout.TargetFor(raw);
            }

            t.RawLast = raw;
            value = layout.ValueFor(t.Shown);
            t.Applied = t.Shown;

            if (_scaleLogCount < Plugin.DebugLogCountCfg.Value)
            {
                _scaleLogCount++;
                Plugin.Lg.LogInfo("TypewriterFix[smooth]: raw " + raw + " target " + t.Target
                    + " shown " + t.Shown + " g " + t.GapEma.ToString("F4") + " N0=" + layout.N0 + " N1=" + layout.N1
                    + " \"" + Head(layout.O, 10) + "\"");
            }
        }

        /// <summary>프레임마다 호출(TypewriterDriver.Update). Smooth 상태의 표시 글자 수를 시간 기반으로 진행한다.</summary>
        internal static void Tick()
        {
            if (Tracks.Count == 0)
            {
                return;
            }

            if (!Plugin.EnabledCfg.Value)
            {
                KeyBuffer.Clear();
                KeyBuffer.AddRange(Tracks.Keys);
                foreach (IntPtr k in KeyBuffer)
                {
                    Forget(k);
                }
                return;
            }

            float dt = UnityEngine.Time.unscaledDeltaTime;

            KeyBuffer.Clear();
            KeyBuffer.AddRange(Tracks.Keys);
            foreach (IntPtr key in KeyBuffer)
            {
                Track t;
                if (!Tracks.TryGetValue(key, out t))
                {
                    continue;
                }

                if (!IsAlive(t.Ui))
                {
                    Forget(key);
                    continue;
                }

                Advance(t, dt);

                if (t.Shown != t.Applied)
                {
                    ApplyToUi(t);
                }
            }
        }

        private static void Advance(Track t, float dt)
        {
            MapLayout l = t.Layout;
            if (l == null)
            {
                return;
            }

            t.Wait -= dt;
            int guard = 0;
            while (t.Wait <= 0f)
            {
                if (t.Shown >= l.N1)
                {
                    t.Wait = 0f;
                    break;
                }
                // 게임 raw가 아직 끝나지 않았는데 너무 앞서 있으면 기다린다
                if (!t.Finished && t.Shown >= t.Target + LeadLimit)
                {
                    t.Wait = 0f;
                    break;
                }

                t.Shown++;
                char c = l.LetterAt(t.Shown);

                float iv = t.GapEma * l.N0 / l.N1;
                if (t.Shown < t.Target - LagThreshold)
                {
                    iv *= 0.5f; // 따라잡기
                }

                t.Wait += iv * PunctMultiplier(c);

                if (++guard > 1000)
                {
                    t.Wait = 0f;
                    break;
                }
            }
        }

        private static float PunctMultiplier(char c)
        {
            switch (c)
            {
                case '.':
                case '!':
                case '?':
                case '。':
                case '！':
                case '？':
                case '…':
                    return Plugin.PunctPauseLongCfg.Value;
                case ',':
                case '、':
                case '，':
                    return Plugin.PunctPauseShortCfg.Value;
                default:
                    return 1f;
            }
        }

        private static void ApplyToUi(Track t)
        {
            int v = t.Layout.ValueFor(t.Shown);
            _writing = true;
            try
            {
                t.Ui.maxVisibleCharacters = v;
            }
            catch (Exception e)
            {
                Warn("apply failed", e);
            }
            finally
            {
                _writing = false;
                t.Applied = t.Shown;
            }
        }

        private static bool IsAlive(TMP_Text ui)
        {
            try
            {
                if (ui == null)
                {
                    return false;
                }
                return !((Il2CppObjectBase)ui).WasCollected;
            }
            catch (Exception)
            {
                return false;
            }
        }

        private static void Forget(IntPtr key)
        {
            RawValues.Remove(key);
            LayoutCache.Remove(key);
            Tracks.Remove(key);
        }

        private static MapLayout GetLayout(IntPtr key, string rawO, string rawT)
        {
            LayoutEntry entry;
            if (LayoutCache.TryGetValue(key, out entry)
                && string.Equals(entry.RawO, rawO, StringComparison.Ordinal)
                && string.Equals(entry.RawT, rawT, StringComparison.Ordinal))
            {
                return entry.Layout;
            }

            MapLayout layout = new MapLayout(StripTags(rawO), StripTags(rawT));
            LayoutCache[key] = new LayoutEntry { RawO = rawO, RawT = rawT, Layout = layout };
            return layout;
        }

        /// <summary>
        /// 순수 함수: 원문 O(태그 제거됨), 번역문 T(태그 제거됨), 게임 원래 raw 값 -> 번역문용 maxVisibleCharacters.
        /// 공백이 아닌 문자(글자) 기준으로 비율 매핑한다. N0 또는 N1이 0이면 호출하지 말 것.
        /// </summary>
        internal static int MapValue(string o, string t, int raw)
        {
            int n0;
            int n1;
            return new MapLayout(o, t).Map(raw, out n0, out n1);
        }

        private sealed class LayoutEntry
        {
            public string RawO;
            public string RawT;
            public MapLayout Layout;
        }

        /// <summary>O/T의 글자 위치 정보를 미리 계산해 두는 레이아웃. 글자 = char.IsWhiteSpace가 아닌 문자.</summary>
        internal sealed class MapLayout
        {
            public readonly string O;
            public readonly string T;
            public readonly int N0;
            public readonly int N1;

            // _prefixO[i] = O의 앞 i개 문자 중 글자 수 (길이 O.Length + 1)
            private readonly int[] _prefixO;
            // _endT[k] = T에서 k번째 글자 바로 다음 인덱스 (k = 1..N1), _endT[0] = T 첫 글자 앞 공백 수
            private readonly int[] _endT;

            public MapLayout(string o, string t)
            {
                O = o ?? string.Empty;
                T = t ?? string.Empty;

                _prefixO = new int[O.Length + 1];
                for (int i = 0; i < O.Length; i++)
                {
                    _prefixO[i + 1] = _prefixO[i] + (char.IsWhiteSpace(O[i]) ? 0 : 1);
                }
                N0 = _prefixO[O.Length];

                List<int> ends = new List<int>();
                int firstLetter = -1;
                for (int i = 0; i < T.Length; i++)
                {
                    if (char.IsWhiteSpace(T[i]))
                    {
                        continue;
                    }
                    if (firstLetter < 0)
                    {
                        firstLetter = i;
                    }
                    ends.Add(i + 1);
                }
                N1 = ends.Count;

                _endT = new int[N1 + 1];
                _endT[0] = firstLetter < 0 ? 0 : firstLetter;
                for (int k = 0; k < N1; k++)
                {
                    _endT[k + 1] = ends[k];
                }
            }

            public int Map(int raw, out int n0, out int n1)
            {
                if (raw >= O.Length)
                {
                    n0 = N0;
                    n1 = N1;
                    return 99999;
                }
                if (raw <= 0 || N0 <= 0 || N1 <= 0)
                {
                    n0 = 0;
                    n1 = 0;
                    return 0;
                }

                n0 = _prefixO[raw];
                if (n0 <= 0)
                {
                    n1 = 0;
                }
                else
                {
                    long r = (long)Math.Round((double)n0 * N1 / N0, MidpointRounding.AwayFromZero);
                    n1 = (int)Math.Min(Math.Max(r, 1L), (long)N1);
                }

                return _endT[n1];
            }

            /// <summary>게임 raw 기준 목표 번역 글자 수: round(n0 * N1 / N0). raw가 원문 끝이면 N1.</summary>
            public int TargetFor(int raw)
            {
                if (raw >= O.Length)
                {
                    return N1;
                }
                if (raw <= 0 || N0 <= 0 || N1 <= 0)
                {
                    return 0;
                }
                int n0 = _prefixO[raw];
                if (n0 <= 0)
                {
                    return 0;
                }
                long r = (long)Math.Round((double)n0 * N1 / N0, MidpointRounding.AwayFromZero);
                return (int)Math.Min(Math.Max(r, 0L), (long)N1);
            }

            /// <summary>표시 글자 수(shown)를 TMP maxVisibleCharacters 값으로 바꾼다. 전부 표시면 99999.</summary>
            public int ValueFor(int shown)
            {
                if (shown <= 0)
                {
                    return 0;
                }
                if (shown >= N1)
                {
                    return 99999;
                }
                return _endT[shown];
            }

            /// <summary>k번째(1부터) 글자 문자. 1 <= k <= N1.</summary>
            public char LetterAt(int k)
            {
                return T[_endT[k] - 1];
            }
        }

        public static void OnGetMaxVisible(TMP_Text ui, ref int result)
        {
            try
            {
                IntPtr key = ((Il2CppObjectBase)ui).Pointer;
                if (!RawValues.TryGetValue(key, out int raw))
                {
                    return;
                }

                object info = GetInfo(ui);
                if (info == null || !IsTranslated(info))
                {
                    return;
                }

                result = raw;
            }
            catch (Exception e)
            {
                Warn("OnGetMaxVisible failed", e);
            }
        }

        private static bool IsTranslated(object info)
        {
            return (bool)_isTranslatedProp.GetValue(info);
        }

        private static object GetInfo(object ui)
        {
            if (!EnsureAutoTranslator())
            {
                return null;
            }
            return _getInfo.Invoke(null, new object[] { ui });
        }

        private static bool EnsureAutoTranslator()
        {
            if (_atResolved)
            {
                return true;
            }

            long now = Environment.TickCount64;
            if (now < _nextResolveTick)
            {
                return false;
            }
            _nextResolveTick = now + ResolveRetryMs;

            try
            {
                Assembly atAssembly = null;
                foreach (Assembly a in AppDomain.CurrentDomain.GetAssemblies())
                {
                    if (a.GetName().Name == AtAssemblyName)
                    {
                        atAssembly = a;
                        break;
                    }
                }
                if (atAssembly == null)
                {
                    return false;
                }

                Type extType = atAssembly.GetType(AtExtensionsTypeName, false);
                if (extType == null)
                {
                    Warn("AT ComponentExtensions type not found", null);
                    return false;
                }

                MethodInfo getInfo = extType.GetMethod(
                    "GetTextTranslationInfo",
                    BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static,
                    null,
                    new Type[] { typeof(object) },
                    null);
                if (getInfo == null)
                {
                    Warn("AT GetTextTranslationInfo(object) not found", null);
                    return false;
                }

                Type infoType = getInfo.ReturnType;
                const BindingFlags instanceFlags = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance;
                PropertyInfo isTranslated = infoType.GetProperty("IsTranslated", instanceFlags);
                PropertyInfo original = infoType.GetProperty("OriginalText", instanceFlags);
                PropertyInfo translated = infoType.GetProperty("TranslatedText", instanceFlags);
                if (isTranslated == null || original == null || translated == null)
                {
                    Warn("AT TextTranslationInfo properties not found", null);
                    return false;
                }

                _getInfo = getInfo;
                _isTranslatedProp = isTranslated;
                _originalTextProp = original;
                _translatedTextProp = translated;
                _atResolved = true;
                return true;
            }
            catch (Exception e)
            {
                Warn("AT reflection resolve failed", e);
                return false;
            }
        }

        private static string StripTags(string s)
        {
            if (string.IsNullOrEmpty(s))
            {
                return string.Empty;
            }
            return TagRegex.Replace(s, string.Empty);
        }

        private static string Head(string s, int n)
        {
            if (s == null)
            {
                return string.Empty;
            }
            return s.Length <= n ? s : s.Substring(0, n);
        }

        private static void Warn(string message, Exception e)
        {
            if (_warnCount >= MaxWarnings)
            {
                return;
            }
            _warnCount++;
            Plugin.Lg.LogWarning("TypewriterFix: " + message + (e != null ? ": " + e.Message : string.Empty));
        }
    }
}
