// Read-only extractor: mounts FF7 Rebirth paks and writes raw package bytes under a path filter.
// usage: rebirth_extract <PaksDir> <OodleDll> <OutDir> <filter-substring> [--list]
using CUE4Parse.Compression;
using CUE4Parse.Encryption.Aes;
using CUE4Parse.FileProvider;
using CUE4Parse.UE4.Objects.Core.Misc;
using CUE4Parse.UE4.Versions;

var (paks, oodle, outDir, filter) = (args[0], args[1], args[2], args[3]);
bool listOnly = args.Contains("--list");
OodleHelper.Initialize(oodle);
var provider = new DefaultFileProvider(paks, SearchOption.TopDirectoryOnly,
    new VersionContainer(EGame.GAME_FinalFantasy7Rebirth), StringComparer.OrdinalIgnoreCase);
provider.Initialize();
provider.SubmitKey(new FGuid(), new FAesKey(new byte[32]));
Console.WriteLine($"files mounted: {provider.Files.Count}");
int n = 0;
foreach (var (path, file) in provider.Files)
{
    if (path.IndexOf(filter, StringComparison.OrdinalIgnoreCase) < 0) continue;
    n++;
    if (listOnly) { if (n <= 60) Console.WriteLine($"{path}\t{file.Size}"); continue; }
    var bytes = file.Read();
    var dst = Path.Combine(outDir, path.Replace('/', Path.DirectorySeparatorChar));
    Directory.CreateDirectory(Path.GetDirectoryName(dst)!);
    File.WriteAllBytes(dst, bytes);
}
Console.WriteLine($"matched: {n}");
