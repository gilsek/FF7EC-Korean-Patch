using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Windows.Forms;

namespace FF7ECKo
{
    internal static class Program
    {
        private const string ServerExeName = "FF7ECServer.exe";
        private const string ServerProcessName = "FF7ECServer";
        private const string GameProcessName = "FF7EC";
        private const string ServerLogName = "ff7ec_ko_server.log";
        private const string LauncherLogName = "ff7ec_ko_launcher.log";
        private const string Caption = "FF7EC 한글패치 실행기";

        private const int StartupTimeoutMs = 180000;
        private const int PollIntervalMs = 500;
        private const int GracefulWaitMs = 30000;
        private const int BreakWaitMs = 15000;
        private const int KillWaitMs = 5000;

        private const uint CTRL_C_EVENT = 0;
        private const uint CTRL_BREAK_EVENT = 1;

        private static string baseDir;
        private static LogFile log;

        [STAThread]
        private static void Main(string[] args)
        {
            baseDir = AppDomain.CurrentDomain.BaseDirectory;
            log = new LogFile(Path.Combine(baseDir, LauncherLogName));
            try
            {
                Run(args);
            }
            catch (Exception ex)
            {
                log.Error("예외 발생: " + ex);
                Alert("실행기 오류:\n" + ex.Message + "\n\n자세한 내용은 ff7ec_ko_launcher.log를 확인하세요.", MessageBoxIcon.Error);
            }
            finally
            {
                log.Info("실행기 종료");
                log.Dispose();
            }
        }

        private static void Run(string[] args)
        {
            log.Info("실행기 시작. 폴더=" + baseDir + ", 인자=[" + string.Join(" ", args) + "]");

            string serverPath = Path.Combine(baseDir, ServerExeName);
            if (!File.Exists(serverPath))
            {
                log.Error("서버 파일 없음: " + serverPath);
                Alert("FF7ECServer.exe를 찾을 수 없습니다.\n이 실행기는 게임 폴더(FF7ECServer.exe와 같은 위치)에 두고 실행하세요.", MessageBoxIcon.Error);
                return;
            }

            if (IsRunning(ServerProcessName) || IsRunning(GameProcessName))
            {
                log.Warn("이미 실행 중인 FF7ECServer 또는 FF7EC 프로세스가 있어 종료합니다.");
                Alert("이미 실행 중입니다.\n(FF7ECServer 또는 FF7EC 프로세스가 떠 있습니다.)", MessageBoxIcon.Warning);
                return;
            }

            if (!EnsureFontPatched())
            {
                return;
            }

            LogFile serverOut = new LogFile(Path.Combine(baseDir, ServerLogName));
            Process server = null;
            try
            {
                server = StartServer(serverPath, args, serverOut);
                if (server == null)
                {
                    Alert("서버를 시작하지 못했습니다.\nff7ec_ko_launcher.log를 확인하세요.", MessageBoxIcon.Error);
                    return;
                }

                Process game = WaitForGame(server);
                if (game == null)
                {
                    // WaitForGame already showed the reason to the user.
                    return;
                }

                MonitorUntilGameExits(server, game);
            }
            finally
            {
                if (server != null)
                {
                    try
                    {
                        // Waits until redirected output has been fully read, so the server log is complete.
                        if (server.HasExited) server.WaitForExit();
                    }
                    catch (Exception ex)
                    {
                        log.Warn("서버 출력 정리 중 예외: " + ex.Message);
                    }
                    server.Dispose();
                }
                serverOut.Dispose();
            }
        }

        // Runs ko_patch\FontPatch.exe, which swaps the game's Japanese font data for a Hangul font
        // (and does nothing when it is already patched). Returns false when the game should not start.
        private static bool EnsureFontPatched()
        {
            string exe = Path.Combine(baseDir, "ko_patch", "FontPatch.exe");
            if (!File.Exists(exe))
            {
                log.Warn("폰트 패치기 없음, 건너뜀: " + exe);
                return true;
            }

            ProcessStartInfo psi = new ProcessStartInfo
            {
                FileName = exe,
                Arguments = "--game " + QuoteArg(baseDir.TrimEnd('\\')),
                WorkingDirectory = Path.GetDirectoryName(exe),
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                StandardOutputEncoding = Encoding.UTF8,
                StandardErrorEncoding = Encoding.UTF8
            };
            try
            {
                using (Process p = Process.Start(psi))
                {
                    var errTask = p.StandardError.ReadToEndAsync();
                    var outTask = p.StandardOutput.ReadToEndAsync();
                    if (!p.WaitForExit(600000))
                    {
                        try { p.Kill(); } catch { }
                        log.Error("폰트 패치 시간 초과");
                        Alert("한글 폰트 적용이 끝나지 않았습니다.\nko_patch\\fontpatch.log를 확인하세요.", MessageBoxIcon.Error);
                        return false;
                    }
                    foreach (string line in (outTask.Result + errTask.Result).Split('\n'))
                    {
                        if (line.Trim().Length > 0) log.Info("[FontPatch] " + line.TrimEnd('\r'));
                    }
                    if (p.ExitCode != 0)
                    {
                        log.Error("폰트 패치 실패, 종료 코드 " + p.ExitCode);
                        Alert("한글 폰트를 적용하지 못했습니다.\nko_patch\\fontpatch.log를 확인하세요.\n\n(그대로 실행하면 한글이 □로 보입니다.)", MessageBoxIcon.Error);
                        return false;
                    }
                }
            }
            catch (Exception ex)
            {
                log.Error("폰트 패치기 실행 실패: " + ex.Message);
                Alert("폰트 패치기를 실행하지 못했습니다:\n" + ex.Message, MessageBoxIcon.Error);
                return false;
            }
            return true;
        }

        private static Process StartServer(string serverPath, string[] args, LogFile serverOut)
        {
            ProcessStartInfo psi = new ProcessStartInfo
            {
                FileName = serverPath,
                Arguments = JoinArgs(args),
                WorkingDirectory = baseDir,
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardInput = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                StandardOutputEncoding = Encoding.UTF8,
                StandardErrorEncoding = Encoding.UTF8
            };

            Process server = new Process { StartInfo = psi, EnableRaisingEvents = true };
            server.OutputDataReceived += (s, e) =>
            {
                if (e.Data != null) serverOut.Line(e.Data);
            };
            server.ErrorDataReceived += (s, e) =>
            {
                if (e.Data != null) serverOut.Line("[ERR] " + e.Data);
            };

            try
            {
                log.Info("서버 시작: " + serverPath + " 인자=[" + psi.Arguments + "]");
                server.Start();
            }
            catch (Exception ex)
            {
                log.Error("서버 시작 실패: " + ex.Message);
                server.Dispose();
                return null;
            }

            log.Info("서버 PID=" + server.Id);
            server.BeginOutputReadLine();
            server.BeginErrorReadLine();
            return server;
        }

        // Returns the game process, or null when the launcher should exit (message already shown).
        private static Process WaitForGame(Process server)
        {
            log.Info("게임 프로세스(" + GameProcessName + ") 대기 시작. 최대 " + (StartupTimeoutMs / 1000) + "초");
            Stopwatch sw = Stopwatch.StartNew();

            while (true)
            {
                if (server.HasExited)
                {
                    server.WaitForExit();
                    int code = server.ExitCode;
                    log.Error("서버가 시작 직후 종료됨. 종료 코드=" + code);
                    Alert("서버가 시작 직후 종료됨 (종료 코드 " + code + ").\nff7ec_ko_server.log를 확인하세요.", MessageBoxIcon.Error);
                    return null;
                }

                Process game = FindProcess(GameProcessName);
                if (game != null)
                {
                    log.Info("게임 프로세스 감지. PID=" + game.Id + ", 경과 " + sw.ElapsedMilliseconds + "ms");
                    return game;
                }

                if (sw.ElapsedMilliseconds >= StartupTimeoutMs)
                {
                    log.Error("180초 안에 게임이 실행되지 않음. 서버 정상 종료 시도");
                    StopServer(server);
                    Alert("180초 안에 게임이 실행되지 않아 서버를 종료했습니다.\nUAC 창을 승인했는지, ff7ec_ko_server.log를 확인하세요.", MessageBoxIcon.Warning);
                    return null;
                }

                Thread.Sleep(PollIntervalMs);
            }
        }

        private static void MonitorUntilGameExits(Process server, Process game)
        {
            while (true)
            {
                if (server.HasExited)
                {
                    server.WaitForExit();
                    log.Info("서버가 게임보다 먼저 종료됨. 종료 코드=" + server.ExitCode + ". 실행기도 종료");
                    return;
                }

                if (HasExited(game))
                {
                    break;
                }

                Thread.Sleep(PollIntervalMs);
            }

            log.Info("게임 프로세스 종료 감지. 서버 정상 종료 시작");
            StopServer(server);
        }

        // Sends Ctrl+C (then Ctrl+Break) to the server's console so it can restore the hosts file.
        // Kills it only as a last resort.
        private static void StopServer(Process server)
        {
            if (HasExited(server))
            {
                log.Info("서버가 이미 종료된 상태");
                return;
            }

            int pid = server.Id;
            bool exitedGracefully = false;
            bool attached = false;

            try
            {
                FreeConsole();
                SetConsoleCtrlHandler(IntPtr.Zero, true); // ignore Ctrl+C in this launcher itself

                if (AttachConsole((uint)pid))
                {
                    attached = true;
                    log.Info("서버 콘솔 연결 성공. PID=" + pid);
                }
                else
                {
                    int err = Marshal.GetLastWin32Error();
                    log.Error("AttachConsole 실패. PID=" + pid + ", 오류 코드=" + err);
                }

                if (attached)
                {
                    SendCtrlEvent(CTRL_C_EVENT, "CTRL_C_EVENT");
                    exitedGracefully = WaitServerExit(server, GracefulWaitMs);

                    if (!exitedGracefully)
                    {
                        log.Warn("CTRL_C 후 " + (GracefulWaitMs / 1000) + "초 내 미종료. CTRL_BREAK_EVENT 전송");
                        SendCtrlEvent(CTRL_BREAK_EVENT, "CTRL_BREAK_EVENT");
                        exitedGracefully = WaitServerExit(server, BreakWaitMs);
                    }
                }
            }
            finally
            {
                // The server may still be running here; if so, it is killed below.
                try { FreeConsole(); } catch { }
                SetConsoleCtrlHandler(IntPtr.Zero, false);
            }

            if (exitedGracefully)
            {
                log.Info("서버 정상 종료 확인");
                return;
            }

            if (HasExited(server))
            {
                log.Info("서버 종료 확인(콘솔 해제 후)");
                return;
            }

            log.Error("서버가 정상 종료되지 않아 강제 종료(Kill)합니다. hosts 파일이 원복되지 않았을 수 있음");
            try
            {
                server.Kill();
                server.WaitForExit(KillWaitMs);
            }
            catch (Exception ex)
            {
                log.Error("서버 Kill 실패: " + ex.Message);
            }

            Alert("서버가 정상 종료되지 않아 강제 종료했습니다.\nhosts 파일이 원복되지 않았을 수 있습니다. 확인하세요.\n(ff7ec_ko_server.log 참고)", MessageBoxIcon.Warning);
        }

        private static bool WaitServerExit(Process server, int timeoutMs)
        {
            try
            {
                return server.WaitForExit(timeoutMs);
            }
            catch (Exception ex)
            {
                log.Warn("서버 대기 중 예외: " + ex.Message);
                return HasExited(server);
            }
        }

        private static void SendCtrlEvent(uint evt, string name)
        {
            if (GenerateConsoleCtrlEvent(evt, 0))
            {
                log.Info(name + " 전송 성공");
            }
            else
            {
                int err = Marshal.GetLastWin32Error();
                log.Error(name + " 전송 실패. 오류 코드=" + err);
            }
        }

        private static bool IsRunning(string processName)
        {
            Process[] list = Process.GetProcessesByName(processName);
            bool any = list.Length > 0;
            foreach (Process p in list) p.Dispose();
            return any;
        }

        private static Process FindProcess(string processName)
        {
            Process[] list = Process.GetProcessesByName(processName);
            Process first = list.FirstOrDefault();
            foreach (Process p in list)
            {
                if (p != first) p.Dispose();
            }
            return first;
        }

        private static bool HasExited(Process p)
        {
            try
            {
                return p.HasExited;
            }
            catch (Exception ex)
            {
                // Treat an unreadable process as gone so the launcher does not hang forever.
                log.Warn("프로세스 상태 조회 실패(종료로 간주). PID=" + SafeId(p) + ", " + ex.Message);
                return true;
            }
        }

        private static string SafeId(Process p)
        {
            try { return p.Id.ToString(); } catch { return "?"; }
        }

        private static string JoinArgs(string[] args)
        {
            return string.Join(" ", args.Select(QuoteArg));
        }

        private static string QuoteArg(string arg)
        {
            if (arg.Length > 0 && arg.IndexOfAny(new[] { ' ', '\t', '"' }) < 0)
            {
                return arg;
            }
            return "\"" + arg.Replace("\"", "\\\"") + "\"";
        }

        private static void Alert(string text, MessageBoxIcon icon)
        {
            MessageBox.Show(text, Caption, MessageBoxButtons.OK, icon);
        }

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool FreeConsole();

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool AttachConsole(uint dwProcessId);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool SetConsoleCtrlHandler(IntPtr handlerRoutine, bool add);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool GenerateConsoleCtrlEvent(uint dwCtrlEvent, uint dwProcessGroupId);

        // Thread-safe, UTF-8 (no BOM), flushes every line. Never throws on write failure.
        private sealed class LogFile : IDisposable
        {
            private readonly object _lock = new object();
            private StreamWriter _writer;

            public LogFile(string path)
            {
                try
                {
                    FileStream fs = new FileStream(path, FileMode.Create, FileAccess.Write, FileShare.Read);
                    _writer = new StreamWriter(fs, new UTF8Encoding(false)) { AutoFlush = true };
                }
                catch (Exception ex)
                {
                    _writer = null;
                    MessageBox.Show("로그 파일을 열 수 없습니다: " + path + "\n" + ex.Message, Caption, MessageBoxButtons.OK, MessageBoxIcon.Warning);
                }
            }

            // Raw line (no timestamp), used for server output.
            public void Line(string text)
            {
                lock (_lock)
                {
                    try
                    {
                        if (_writer != null) _writer.WriteLine(text);
                    }
                    catch
                    {
                        // Logging must never take the launcher down.
                    }
                }
            }

            public void Info(string msg) { Line(Stamp("INFO", msg)); }
            public void Warn(string msg) { Line(Stamp("WARN", msg)); }
            public void Error(string msg) { Line(Stamp("ERROR", msg)); }

            private static string Stamp(string level, string msg)
            {
                return DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff") + " [" + level + "] " + msg;
            }

            public void Dispose()
            {
                lock (_lock)
                {
                    try
                    {
                        if (_writer != null) _writer.Dispose();
                    }
                    catch
                    {
                    }
                    _writer = null;
                }
            }
        }
    }
}
