// FontPatch: swaps the game's Japanese-only font data (FOT-SkipProN-D) for a Hangul font on the user's PC,
// so the Korean patch never has to ship game files. Same steps as tools/font_swap.py, font_swap_data.py
// and the catalog CRC edit in tools/ko_test.py.
// usage: FontPatch.exe [--game DIR] [--font FILE] [--hud-font FILE] [--check] [--restore]
// Main UI/story font (aa bundle) = bundled Pretendard-Medium; battle HUD (data.unity3d) = Malgun Gothic
// read from the PC's own Windows fonts folder (not redistributable, so never shipped).
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using AssetsTools.NET;
using AssetsTools.NET.Extra;

namespace FontPatch
{
    internal static class Program
    {
        const string FontHash = "81246fb8f207e1016fff88f97a64e241";
        const string AaBundle = @"FF7EC_Data\StreamingAssets\aa\StandaloneWindows64\font_assets_assets\command\internalassets\font\fot-skippron-d.otf_" + FontHash + ".bundle";
        const string DataBundle = @"FF7EC_Data\data.unity3d";
        const string Catalog = @"FF7EC_Data\StreamingAssets\aa\catalog.json";
        const string FontName = "FOT-SkipProN-D";
        static readonly string[] Targets = { AaBundle, DataBundle, Catalog };

        static string game, patchDir, tpk, logPath;
        static byte[] font, hudFont;

        static int Main(string[] args)
        {
            Console.OutputEncoding = new UTF8Encoding(false);
            string exeDir = AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\');
            game = Path.GetDirectoryName(exeDir);
            string fontPath = Path.Combine(exeDir, "Pretendard-Medium.otf");
            string hudFontPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Fonts), "malgun.ttf");
            bool check = false, restore = false;
            for (int i = 0; i < args.Length; i++)
            {
                switch (args[i])
                {
                    case "--game": game = Path.GetFullPath(args[++i]); break;
                    case "--font": fontPath = Path.GetFullPath(args[++i]); break;
                    case "--hud-font": hudFontPath = Path.GetFullPath(args[++i]); break;
                    case "--check": check = true; break;
                    case "--restore": restore = true; break;
                    default: Console.WriteLine("unknown argument: " + args[i]); return 2;
                }
            }
            game = game.TrimEnd('\\');
            patchDir = Path.Combine(game, "ko_patch");
            tpk = Path.Combine(exeDir, "classdata.tpk");
            Directory.CreateDirectory(patchDir);
            logPath = Path.Combine(patchDir, "fontpatch.log");
            try
            {
                Log("시작 game=" + game + (check ? " --check" : "") + (restore ? " --restore" : ""));
                if (!File.Exists(Path.Combine(game, DataBundle))) throw new Exception("게임 폴더가 아닙니다(FF7EC_Data\\data.unity3d 없음): " + game);
                if (restore) return Restore();
                font = File.ReadAllBytes(fontPath);
                if (!File.Exists(hudFontPath)) throw new Exception("전투 HUD용 폰트가 없습니다: " + hudFontPath);
                hudFont = File.ReadAllBytes(hudFontPath);
                if (check) return Check();
                return Patch();
            }
            catch (Exception ex)
            {
                Log("오류: " + ex);
                return 2;
            }
        }

        // ---------- top level ----------

        static int Patch()
        {
            var state = LoadState();
            bool changed = false;
            foreach (string rel in Targets)
            {
                string path = Path.Combine(game, rel);
                if (!File.Exists(path)) throw new Exception("파일 없음: " + rel);
                if (state.TryGetValue(rel, out string h) && h == FileId(path)) { Log("이미 적용됨: " + rel); continue; }
                if (IsPatched(rel, path)) { Log("이미 적용됨(내용 확인): " + rel); state[rel] = FileId(path); changed = true; continue; }
                Backup(rel, path);
                string tmp = path + ".kotmp";
                if (rel == Catalog) PatchCatalog(path, tmp);
                else PatchBundle(path, tmp, rel == DataBundle ? FontName : null, FontFor(rel));
                if (!IsPatched(rel, tmp)) throw new Exception("패치 결과 검증 실패: " + rel);
                File.Copy(tmp, path, true);
                File.Delete(tmp);
                state[rel] = FileId(path); changed = true;
                Log("적용: " + rel + " (" + new FileInfo(path).Length + " bytes)");
            }
            if (changed) SaveState(state);
            Log("완료");
            return 0;
        }

        static int Check()
        {
            bool all = true;
            foreach (string rel in Targets)
            {
                string path = Path.Combine(game, rel);
                bool ok = File.Exists(path) && IsPatched(rel, path);
                all &= ok;
                Log((ok ? "적용됨: " : "미적용: ") + rel);
            }
            return all ? 0 : 1;
        }

        static int Restore()
        {
            foreach (string rel in Targets)
            {
                string bk = Path.Combine(patchDir, "backup", rel);
                if (!File.Exists(bk)) { Log("백업 없음, 건너뜀: " + rel); continue; }
                File.Copy(bk, Path.Combine(game, rel), true);
                Log("복구: " + rel);
            }
            string st = Path.Combine(patchDir, "font_state.txt");
            if (File.Exists(st)) File.Delete(st);
            Log("복구 완료");
            return 0;
        }

        // The first copy we see is the game's own file. Never overwrite an existing backup: the file in place
        // may already carry another font (an older test patch), and the service has ended, so no game updates.
        static void Backup(string rel, string path)
        {
            string bk = Path.Combine(patchDir, "backup", rel);
            if (File.Exists(bk)) return;
            Directory.CreateDirectory(Path.GetDirectoryName(bk));
            File.Copy(path, bk, true);
            Log("백업: " + rel);
        }

        static bool IsPatched(string rel, string path)
        {
            if (rel == Catalog) return CatalogCrc(File.ReadAllText(path, new UTF8Encoding(false)), out _, out _, out _) == "0";
            byte[] cur = ReadFontData(path, rel == DataBundle ? FontName : null);
            byte[] want = FontFor(rel);
            return cur != null && cur.Length == want.Length && cur.SequenceEqual(want);
        }

        static byte[] FontFor(string rel) => rel == DataBundle ? hudFont : font;

        // ---------- bundles ----------

        static AssetsManager NewManager()
        {
            var am = new AssetsManager();
            am.LoadClassPackage(tpk);
            return am;
        }

        // Finds the one Font to swap: the only Font in the bundle (name == null) or the one with that name.
        static List<(AssetsFileInstance inst, int dir, AssetFileInfo info, AssetTypeValueField bf)> FindFonts(AssetsManager am, BundleFileInstance bun, string name)
        {
            var hits = new List<(AssetsFileInstance, int, AssetFileInfo, AssetTypeValueField)>();
            am.LoadClassDatabaseFromPackage(bun.file.Header.EngineVersion);
            var dirs = bun.file.BlockAndDirInfo.DirectoryInfos;
            for (int i = 0; i < dirs.Count; i++)
            {
                if (!bun.file.IsAssetsFile(i)) continue;
                var inst = am.LoadAssetsFileFromBundle(bun, i, false);
                foreach (var info in inst.file.GetAssetsOfType(AssetClassID.Font))
                {
                    var bf = am.GetBaseField(inst, info);
                    if (name == null || bf["m_Name"].AsString == name) hits.Add((inst, i, info, bf));
                }
            }
            return hits;
        }

        static byte[] ReadFontData(string path, string name)
        {
            var am = NewManager();
            try
            {
                var bun = am.LoadBundleFile(path, true);
                var hits = FindFonts(am, bun, name);
                if (hits.Count != 1) throw new Exception("Font 개수 " + hits.Count + ": " + path);
                return GetBytes(hits[0].bf["m_FontData"]);
            }
            finally { am.UnloadAll(true); }
        }

        static void PatchBundle(string path, string tmp, string name, byte[] data)
        {
            var am = NewManager();
            string raw = tmp + ".raw";
            try
            {
                var bun = am.LoadBundleFile(path, true);
                var hits = FindFonts(am, bun, name);
                if (hits.Count != 1) throw new Exception("Font 개수 " + hits.Count + ": " + path);
                var (inst, dir, info, bf) = hits[0];
                SetBytes(bf["m_FontData"], data);
                info.SetNewData(bf);
                bun.file.BlockAndDirInfo.DirectoryInfos[dir].SetNewData(inst.file);
                using (var w = new AssetsFileWriter(raw)) bun.file.Write(w);
            }
            finally { am.UnloadAll(true); }
            var nb = new AssetBundleFile();
            using (var r = new AssetsFileReader(File.OpenRead(raw)))
            {
                nb.Read(r);
                using (var w = new AssetsFileWriter(tmp)) nb.Pack(w, AssetBundleCompressionType.LZ4);
                nb.Close();
            }
            File.Delete(raw);
        }

        // m_FontData is vector<char>; AssetsTools.NET reads it either as a byte array or as child fields.
        static byte[] GetBytes(AssetTypeValueField fd)
        {
            var arr = fd["Array"];
            if (arr.Value != null && arr.Value.ValueType == AssetValueType.ByteArray) return arr.AsByteArray;
            return arr.Children.Select(c => (byte)c.AsSByte).ToArray();
        }

        static void SetBytes(AssetTypeValueField fd, byte[] data)
        {
            var arr = fd["Array"];
            if (arr.Value != null && arr.Value.ValueType == AssetValueType.ByteArray) { arr.AsByteArray = data; return; }
            var elemTemplate = arr.TemplateField.Children[1];
            var kids = new List<AssetTypeValueField>(data.Length);
            foreach (byte b in data)
            {
                var c = ValueBuilder.DefaultValueFieldFromTemplate(elemTemplate);
                c.AsSByte = unchecked((sbyte)b);
                kids.Add(c);
            }
            arr.Children = kids;
            arr.AsArray = new AssetTypeArrayInfo(data.Length);
        }

        // ---------- addressables catalog ----------

        // Returns the CRC text of the font bundle inside m_ExtraDataString (digits, possibly space padded).
        static string CatalogCrc(string text, out int b64Start, out int b64End, out byte[] extra)
        {
            const string tag = "\"m_ExtraDataString\":\"";
            b64Start = text.IndexOf(tag, StringComparison.Ordinal);
            if (b64Start < 0) throw new Exception("catalog.json에 m_ExtraDataString 없음");
            b64Start += tag.Length;
            b64End = text.IndexOf('"', b64Start);
            extra = Convert.FromBase64String(text.Substring(b64Start, b64End - b64Start));
            byte[] key = Encoding.Unicode.GetBytes("\"m_Hash\":\"" + FontHash + "\",\"m_Crc\":");
            int i = IndexOf(extra, key, 0);
            if (i < 0) throw new Exception("catalog.json에 폰트 번들 CRC 없음");
            int j = i + key.Length;
            int k = IndexOf(extra, Encoding.Unicode.GetBytes(","), j);
            while ((k - j) % 2 != 0) k = IndexOf(extra, Encoding.Unicode.GetBytes(","), k + 1);
            return Encoding.Unicode.GetString(extra, j, k - j).Trim();
        }

        static void PatchCatalog(string path, string tmp)
        {
            var enc = new UTF8Encoding(false);
            byte[] rawBytes = File.ReadAllBytes(path);
            bool bom = rawBytes.Length >= 3 && rawBytes[0] == 0xEF && rawBytes[1] == 0xBB && rawBytes[2] == 0xBF;
            string text = enc.GetString(rawBytes, bom ? 3 : 0, rawBytes.Length - (bom ? 3 : 0));
            CatalogCrc(text, out int s, out int e, out byte[] extra);
            byte[] key = Encoding.Unicode.GetBytes("\"m_Hash\":\"" + FontHash + "\",\"m_Crc\":");
            int j = IndexOf(extra, key, 0) + key.Length;
            int k = IndexOf(extra, Encoding.Unicode.GetBytes(","), j);
            while ((k - j) % 2 != 0) k = IndexOf(extra, Encoding.Unicode.GetBytes(","), k + 1);
            int digits = (k - j) / 2;
            byte[] repl = Encoding.Unicode.GetBytes("0" + new string(' ', digits - 1));
            Buffer.BlockCopy(repl, 0, extra, j, repl.Length);
            string b64 = Convert.ToBase64String(extra);
            if (b64.Length != e - s) throw new Exception("base64 길이 변화");
            string outText = text.Substring(0, s) + b64 + text.Substring(e);
            using (var f = File.Create(tmp))
            {
                if (bom) f.Write(rawBytes, 0, 3);
                byte[] b = enc.GetBytes(outText);
                f.Write(b, 0, b.Length);
            }
        }

        static int IndexOf(byte[] hay, byte[] needle, int from)
        {
            for (int i = from; i <= hay.Length - needle.Length; i++)
            {
                int n = 0;
                while (n < needle.Length && hay[i + n] == needle[n]) n++;
                if (n == needle.Length) return i;
            }
            return -1;
        }

        // ---------- state / util ----------

        static Dictionary<string, string> LoadState()
        {
            var d = new Dictionary<string, string>();
            string p = Path.Combine(patchDir, "font_state.txt");
            if (!File.Exists(p)) return d;
            foreach (string line in File.ReadAllLines(p))
            {
                int t = line.IndexOf('\t');
                if (t > 0) d[line.Substring(0, t)] = line.Substring(t + 1);
            }
            return d;
        }

        static void SaveState(Dictionary<string, string> d)
        {
            File.WriteAllLines(Path.Combine(patchDir, "font_state.txt"), d.Select(kv => kv.Key + "\t" + kv.Value));
        }

        static string FileId(string path) => new FileInfo(path).Length + ":" + Sha(path);

        static string Sha(string path)
        {
            using (var s = File.OpenRead(path))
            using (var h = SHA256.Create())
                return BitConverter.ToString(h.ComputeHash(s)).Replace("-", "");
        }

        static void Log(string msg)
        {
            string line = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + " " + msg;
            Console.WriteLine(msg);
            try { File.AppendAllText(logPath, line + Environment.NewLine, new UTF8Encoding(false)); } catch { }
        }
    }
}
