using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using BepInEx;
using BepInEx.Configuration;
using BepInEx.Logging;
using BepInEx.Unity.IL2CPP;
using HarmonyLib;
using MoonSharp.Interpreter;
using StoryKo;

namespace StoryKoMod
{
    [BepInPlugin(PluginGuid, PluginName, PluginVersion)]
    public sealed class Plugin : BasePlugin
    {
        public const string PluginGuid = "ff7ec.ko.storyko";
        public const string PluginName = "StoryKo";
        public const string PluginVersion = "1.0.0";

        internal const string DataFileName = "story_ko.tsv";

        internal static ManualLogSource Lg;
        internal static ConfigEntry<bool> EnabledCfg;
        internal static ConfigEntry<bool> LogDetailCfg;
        internal static Dictionary<string, string> Dict;
        internal static int MissingLogged;

        public override void Load()
        {
            Lg = Log;

            EnabledCfg = Config.Bind("General", "Enabled", true,
                "true면 MoonSharp 청크 실행 직전에 TXT_ 대사 리터럴을 한국어로 치환한다.");
            LogDetailCfg = Config.Bind("Debug", "LogDetail", true,
                "true면 청크마다 'codeFriendlyName, TXT줄 수, 치환 수, 누락 수'를 한 줄씩 로그한다.");

            if (!EnabledCfg.Value)
            {
                Lg.LogInfo("StoryKo " + PluginVersion + " disabled by config.");
                return;
            }

            string dir = Path.GetDirectoryName(typeof(Plugin).Assembly.Location);
            string dataPath = Path.Combine(dir, DataFileName);
            if (!File.Exists(dataPath))
            {
                Lg.LogWarning("StoryKo: " + DataFileName + " not found next to plugin (" + dataPath + "). StoryKo disabled.");
                return;
            }

            try
            {
                Dict = StoryKoReplacer.LoadFile(dataPath);
                Lg.LogInfo("StoryKo: loaded " + Dict.Count + " keys from " + DataFileName + ".");
            }
            catch (Exception e)
            {
                Lg.LogError("StoryKo: failed to read " + DataFileName + ": " + e);
                return;
            }

            try
            {
                MethodInfo target = typeof(Script).GetMethod(
                    "DoString",
                    BindingFlags.Public | BindingFlags.Instance,
                    null,
                    new[] { typeof(string), typeof(Table), typeof(string) },
                    null);

                if (target == null)
                {
                    Lg.LogError("StoryKo: Script.DoString(string, Table, string) not found. Candidates:");
                    foreach (MethodInfo m in typeof(Script).GetMethods(
                        BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static))
                    {
                        if (m.Name != "DoString") continue;
                        Lg.LogError("  " + m.ReturnType.Name + " DoString("
                            + string.Join(", ", Array.ConvertAll(m.GetParameters(), p => p.ParameterType.Name + " " + p.Name)) + ")");
                    }
                    return;
                }

                MethodInfo prefix = typeof(DoStringPatch).GetMethod(nameof(DoStringPatch.Prefix), BindingFlags.Static | BindingFlags.NonPublic | BindingFlags.Public);
                new Harmony(PluginGuid).Patch(target, prefix: new HarmonyMethod(prefix));
                Lg.LogInfo("StoryKo: patched Script.DoString(" + string.Join(", ", Array.ConvertAll(target.GetParameters(), p => p.ParameterType.Name)) + ").");
            }
            catch (Exception e)
            {
                Lg.LogError("StoryKo: Harmony patch failed: " + e);
            }
        }
    }

    internal static class DoStringPatch
    {
        private const int MaxWarnings = 5;
        private const int MaxMissingLog = 20;
        private static int _warnings;

        // Harmony: 매개변수 이름으로 바인딩된다. code는 치환 대상, codeFriendlyName은 청크 이름.
        internal static void Prefix(ref string code, string codeFriendlyName)
        {
            try
            {
                if (!Plugin.EnabledCfg.Value) return;
                if (Plugin.Dict == null || code == null) return;
                if (code.IndexOf("TXT_", StringComparison.Ordinal) < 0) return;

                var result = new StoryKoReplacer.Result();
                code = StoryKoReplacer.Apply(code, Plugin.Dict, result);

                if (Plugin.LogDetailCfg.Value)
                {
                    Plugin.Lg.LogInfo("StoryKo: " + codeFriendlyName + ", TXT=" + result.TxtLines
                        + ", replaced=" + result.Replaced + ", missing=" + result.Missing);
                }

                for (int i = 0; i < result.MissingKeys.Count && Plugin.MissingLogged < MaxMissingLog; i++)
                {
                    Plugin.MissingLogged++;
                    Plugin.Lg.LogInfo("StoryKo: missing key " + result.MissingKeys[i] + " (" + codeFriendlyName + ")");
                }
            }
            catch (Exception e)
            {
                if (_warnings++ < MaxWarnings)
                    Plugin.Lg.LogWarning("StoryKo: replace failed for " + codeFriendlyName + ", original text kept: " + e);
            }
        }
    }
}
