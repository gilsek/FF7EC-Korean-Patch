using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using StoryKo;

internal static class Program
{
    private static readonly string Root = Environment.GetEnvironmentVariable("FF7EC_KO_ROOT") ?? ".";
    private static readonly string DataPath = Path.Combine(Root, "work", "storyko", "story_ko.tsv");
    private static readonly string ChunkPath = Path.Combine(Root, "work", "story_lua", "data", "dungeoncontentluascript", "0001",
        "en", "dat_asset_lua_script_map_0001_content_002.a", "lua_localize_ff7_main_01_010001_01_en.lua");
    private static readonly string OutPath = Path.Combine(Root, "work", "storyko", "test_out.lua");

    private static int _fail;
    private static int _pass;

    private static void Check(bool ok, string name)
    {
        if (ok) { _pass++; Console.WriteLine("PASS " + name); }
        else { _fail++; Console.WriteLine("FAIL " + name); }
    }

    private static int Main()
    {
        UnitTests();
        int realRc = RealChunkTest();

        Console.WriteLine();
        Console.WriteLine("unit+real: pass=" + _pass + " fail=" + _fail);
        return (_fail == 0 && realRc == 0) ? 0 : 1;
    }

    private static void UnitTests()
    {
        var dict = StoryKoReplacer.ParseLines(new[]
        {
            "\uFEFFTXT_A_1\t가\n나",
            "",
            "TXT_B\t",            // 빈 ko: 제외
            "TXT_C\t첫번째\r",    // CR 제거
            "TXT_C\t두번째",      // 중복: 첫 값만
            "TXT_D\t\\\"따옴표\\\"",
        });
        Check(dict.Count == 3, "ParseLines: BOM/빈 ko/중복 처리 (count=" + dict.Count + ")");
        Check(dict["TXT_A_1"] == "가\n나", "ParseLines: BOM 제거 후 키 인식");
        Check(dict["TXT_C"] == "첫번째", "ParseLines: CR 제거, 첫 값 우선");
        Check(!dict.ContainsKey("TXT_B"), "ParseLines: 빈 ko 제외");

        // 1) 기본 치환 + CRLF 보존 + 다른 줄 보존
        var r1 = new StoryKoReplacer.Result();
        string src1 = "local x = 1\nTXT_A_1 = \"ja text\"\r\nTXT_Z = \"keep\"\r\n";
        string out1 = StoryKoReplacer.Apply(src1, dict, r1);
        Check(out1 == "local x = 1\nTXT_A_1 = \"가\n나\"\r\nTXT_Z = \"keep\"\r\n", "치환: 기본 줄, CRLF 보존");
        Check(r1.TxtLines == 2 && r1.Replaced == 1 && r1.Missing == 1, "치환: 카운트 TXT=2 replaced=1 missing=1");
        Check(r1.MissingKeys.Count == 1 && r1.MissingKeys[0] == "TXT_Z", "치환: 누락 키 이름 기록");

        // 2) 들여쓰기와 = 주변 공백 보존
        var r2 = new StoryKoReplacer.Result();
        string out2 = StoryKoReplacer.Apply("    TXT_C   =    \"x\"\n", dict, r2);
        Check(out2 == "    TXT_C   =    \"첫번째\"\n", "치환: 들여쓰기/공백 보존");

        // 3) 원문의 이스케이프된 따옴표가 있어도 리터럴 전체를 교체
        string out3 = StoryKoReplacer.Apply("TXT_A_1 = \"say \\\"hi\\\"\"\n", dict, null);
        Check(out3 == "TXT_A_1 = \"가\n나\"\n", "치환: 원문 이스케이프 따옴표 포함 리터럴 교체");

        // 4) 줄 시작이 아니거나 리터럴이 아니면 건드리지 않음
        string src4 = "foo(TXT_A_1 = \"x\")\nTXT_A_1 = foo\nlocal TXT_A_1 = \"x\"\n";
        string out4 = StoryKoReplacer.Apply(src4, dict, null);
        Check(out4 == src4, "치환: 비대상 줄 보존");

        // 5) TXT_ 없는 코드는 같은 참조 그대로
        string src5 = "print('hi')";
        Check(ReferenceEquals(StoryKoReplacer.Apply(src5, dict, null), src5), "치환: TXT_ 없으면 원본 참조 반환");

        // 6) 줄 끝 CRLF 뒤에 바로 다음 TXT 줄이 와도 서로 붙지 않음
        string out6 = StoryKoReplacer.Apply("TXT_A_1 = \"a\"\r\nTXT_C = \"b\"\r\n", dict, null);
        Check(out6 == "TXT_A_1 = \"가\n나\"\r\nTXT_C = \"첫번째\"\r\n", "치환: 연속 TXT 줄");

        // 7) 치환 값에 $ 와 역참조 기호가 있어도 그대로
        var d7 = new Dictionary<string, string> { { "TXT_S", "$1 $& $$" } };
        Check(StoryKoReplacer.Apply("TXT_S = \"x\"", d7, null) == "TXT_S = \"$1 $& $$\"", "치환: $ 기호 안전");
    }

    private static int RealChunkTest()
    {
        if (!File.Exists(DataPath) || !File.Exists(ChunkPath))
        {
            Console.WriteLine("FAIL real: 입력 파일 없음 " + DataPath + " / " + ChunkPath);
            _fail++;
            return 1;
        }

        var dict = StoryKoReplacer.LoadFile(DataPath);
        string src = File.ReadAllText(ChunkPath, new UTF8Encoding(false));

        var lineRe = new Regex(@"^(\s*)(TXT_[A-Za-z0-9_]+)(\s*=\s*)""((?:[^""\\]|\\.)*)""", RegexOptions.Multiline);
        var srcTxt = lineRe.Matches(src).Cast<Match>().ToList();
        int expectReplace = srcTxt.Count(m => dict.ContainsKey(m.Groups[2].Value));
        int expectMissing = srcTxt.Count - expectReplace;

        var result = new StoryKoReplacer.Result();
        string output = StoryKoReplacer.Apply(src, dict, result);
        File.WriteAllText(OutPath, output, new UTF8Encoding(false));

        int rc = 0;
        void Real(bool ok, string name)
        {
            if (ok) { _pass++; Console.WriteLine("PASS " + name); }
            else { _fail++; rc = 1; Console.WriteLine("FAIL " + name); }
        }

        Console.WriteLine("real chunk: " + Path.GetFileName(ChunkPath) + " TXT lines=" + srcTxt.Count
            + " replaced=" + result.Replaced + " missing=" + result.Missing + " -> " + OutPath);

        Real(srcTxt.Count > 0, "real: TXT 줄 존재");
        Real(result.TxtLines == srcTxt.Count, "real: TXT 줄 수 일치 (" + result.TxtLines + ")");
        Real(result.Replaced == expectReplace, "real: 치환 수 = 사전 보유 키 수 (" + result.Replaced + ")");
        Real(result.Missing == expectMissing, "real: 누락 수 일치 (" + result.Missing + ")");

        string[] srcLines = src.Split('\n');
        string[] outLines = output.Split('\n');
        Real(srcLines.Length == outLines.Length, "real: 줄 수 동일 (" + outLines.Length + ")");

        // 치환 후 TXT 줄은 모두 따옴표 균형이 맞는 Lua 짧은 문자열 형태여야 한다
        var strictLine = new Regex(@"^TXT_[A-Za-z0-9_]+\s*=\s*""(?:[^""\\]|\\.)*""\r?$");
        int bad = 0, txtOut = 0;
        for (int i = 0; i < outLines.Length; i++)
        {
            if (!outLines[i].StartsWith("TXT_", StringComparison.Ordinal)) continue;
            txtOut++;
            if (!strictLine.IsMatch(outLines[i])) bad++;
        }
        Real(bad == 0, "real: 출력 TXT 줄 따옴표 균형 (bad=" + bad + ", txt=" + txtOut + ")");

        // 치환되지 않은 줄(사전 미보유)은 원문과 바이트 동일
        bool unchangedOk = true;
        for (int i = 0; i < srcLines.Length && i < outLines.Length; i++)
        {
            var m = lineRe.Match(srcLines[i]);
            if (m.Success && !dict.ContainsKey(m.Groups[2].Value) && srcLines[i] != outLines[i]) unchangedOk = false;
            if (!m.Success && srcLines[i] != outLines[i]) unchangedOk = false;
        }
        Real(unchangedOk, "real: 비치환 줄 원문 동일");

        // 치환된 줄에 한글이 들어갔는지(샘플)
        var sample = outLines.FirstOrDefault(l => l.StartsWith("TXT_FF7_MAIN_01_010001_01_001", StringComparison.Ordinal));
        Real(sample != null && sample.Contains("간다") , "real: 샘플 줄 한국어 치환 확인 (" + (sample ?? "null") + ")");

        Real(output.Contains("\r\n") && !output.Contains("\r\r"), "real: CRLF 유지");
        return rc;
    }
}
