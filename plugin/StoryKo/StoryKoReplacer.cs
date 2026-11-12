using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;

namespace StoryKo
{
    /// <summary>
    /// 순수 로직(게임/BepInEx 의존 없음). 플러그인과 오프라인 테스트가 같은 코드를 쓴다.
    /// </summary>
    public static class StoryKoReplacer
    {
        // 그룹: 1=들여쓰기, 2=TXT 키, 3=" = " 부분, 4=따옴표 안 리터럴(Lua 이스케이프 상태)
        public static readonly Regex LineRegex = new Regex(
            @"^(\s*)(TXT_[A-Za-z0-9_]+)(\s*=\s*)""((?:[^""\\]|\\.)*)""",
            RegexOptions.Multiline | RegexOptions.CultureInvariant);

        public sealed class Result
        {
            public int TxtLines;
            public int Replaced;
            public int Missing;
            public readonly List<string> MissingKeys = new List<string>();
        }

        /// <summary>KEY&lt;TAB&gt;KO 형식 줄들을 사전으로 읽는다. 첫 값만 사용, 빈 KO 제외.</summary>
        public static Dictionary<string, string> ParseLines(IEnumerable<string> lines)
        {
            var dict = new Dictionary<string, string>(StringComparer.Ordinal);
            bool first = true;
            foreach (var raw in lines)
            {
                string line = raw;
                if (first)
                {
                    line = line.TrimStart('﻿');
                    first = false;
                }
                line = line.TrimEnd('\r');
                if (line.Length == 0) continue;

                int tab = line.IndexOf('\t');
                if (tab <= 0) continue;

                string key = line.Substring(0, tab);
                string ko = line.Substring(tab + 1);
                if (ko.Length == 0) continue;
                if (!dict.ContainsKey(key)) dict[key] = ko;
            }
            return dict;
        }

        public static Dictionary<string, string> LoadFile(string path)
        {
            return ParseLines(File.ReadAllLines(path, Encoding.UTF8));
        }

        /// <summary>
        /// code 안의 `TXT_KEY = "..."` 줄에서 리터럴을 사전 값으로 바꾼다.
        /// 사전에 없으면 원문 유지. 줄 끝/나머지 텍스트는 그대로 둔다.
        /// </summary>
        public static string Apply(string code, IDictionary<string, string> dict, Result result)
        {
            if (code == null || dict == null) return code;
            if (code.IndexOf("TXT_", StringComparison.Ordinal) < 0) return code;

            return LineRegex.Replace(code, m =>
            {
                if (result != null) result.TxtLines++;

                string key = m.Groups[2].Value;
                if (!dict.TryGetValue(key, out string ko))
                {
                    if (result != null)
                    {
                        result.Missing++;
                        if (result.MissingKeys.Count < 20) result.MissingKeys.Add(key);
                    }
                    return m.Value;
                }

                if (result != null) result.Replaced++;

                // 매치는 닫는 따옴표로 끝나므로 그룹 4 바로 뒤가 닫는 따옴표다.
                int g4Start = m.Groups[4].Index - m.Index;
                int g4End = g4Start + m.Groups[4].Length;
                return m.Value.Substring(0, g4Start) + ko + m.Value.Substring(g4End);
            });
        }
    }
}
