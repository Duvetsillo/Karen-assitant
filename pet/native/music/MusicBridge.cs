// Small .NET Framework bridge: only Windows assemblies, event-driven GSMTC.
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using System.Diagnostics;
using System.Runtime.InteropServices;
using Microsoft.Win32;
using Windows.Foundation;
using Windows.Media;
using Windows.Media.Control;
using Windows.Storage.Streams;

class MusicBridge {
    [DllImport("shell32.dll")] static extern int SHQueryUserNotificationState(out int state);
    [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr window, out uint pid);
    [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr window, out Rect rect);
    [DllImport("user32.dll")] static extern IntPtr MonitorFromWindow(IntPtr window, uint flags);
    [DllImport("user32.dll")] static extern bool GetMonitorInfo(IntPtr monitor, ref MonitorInfo info);
    [DllImport("user32.dll")] static extern bool SetProcessDPIAware();
    [DllImport("user32.dll",EntryPoint="GetWindowLongW")] static extern int GetWindowStyle(IntPtr window,int index);
    [StructLayout(LayoutKind.Sequential)] struct Rect { public int Left,Top,Right,Bottom; }
    [StructLayout(LayoutKind.Sequential)] struct MonitorInfo { public int Size; public Rect Monitor,Work; public uint Flags; }
    static bool Fullscreen() {
        try {
            IntPtr window=GetForegroundWindow(); uint pid; GetWindowThreadProcessId(window,out pid);
            if((GetWindowStyle(window,-16)&0x00c00000)!=0)return false;
            using(var process=Process.GetProcessById((int)pid)) {
                if(process.ProcessName.Equals("explorer",StringComparison.OrdinalIgnoreCase)||process.ProcessName.Equals("Karen Desktop Pet",StringComparison.OrdinalIgnoreCase)||process.Id==Process.GetCurrentProcess().Id)return false;
            }
            Rect rect; var info=new MonitorInfo();info.Size=Marshal.SizeOf(info);
            if(!GetWindowRect(window,out rect)||!GetMonitorInfo(MonitorFromWindow(window,2),ref info))return false;
            return rect.Left<=info.Monitor.Left+2&&rect.Top<=info.Monitor.Top+2&&rect.Right>=info.Monitor.Right-2&&rect.Bottom>=info.Monitor.Bottom-2;
        }catch{return false;}
    }
    static object Context(string id, bool environment = false, bool media = true) {
        int state; bool safe = SHQueryUserNotificationState(out state) == 0 && state == 5;
        bool clear = false;
        if(media) try {
            string[] calls = { "teams", "ms-teams", "zoom", "discord", "skype", "phoneexperiencehost", "slack", "webex" };
            clear = !Process.GetProcesses().Any(p => calls.Contains(p.ProcessName.ToLowerInvariant()));
            using (var key = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone")) {
                if (key == null) clear = false;
                else foreach (var app in key.GetSubKeyNames()) using (var sub = key.OpenSubKey(app)) {
                    if (Convert.ToInt64(sub.GetValue("LastUsedTimeStart", 0L)) > 0 && Convert.ToInt64(sub.GetValue("LastUsedTimeStop", 0L)) == 0) clear = false;
                    foreach (var child in sub.GetSubKeyNames()) using (var entry = sub.OpenSubKey(child))
                        if (Convert.ToInt64(entry.GetValue("LastUsedTimeStart", 0L)) > 0 && Convert.ToInt64(entry.GetValue("LastUsedTimeStop", 0L)) == 0) clear = false;
                }
            }
        } catch { clear = false; }
        string category = environment ? (state == 3 ? "game" : "other") : "unknown";
        if (environment) try {
            uint pid; GetWindowThreadProcessId(GetForegroundWindow(), out pid);
            using (var process = Process.GetProcessById((int)pid)) {
                string name = process.ProcessName.ToLowerInvariant();
                if (new [] { "code", "devenv", "pycharm64", "idea64", "rider64", "webstorm64", "cursor" }.Contains(name)) category = "coding";
                else if (new [] { "chrome", "msedge", "firefox", "brave", "opera" }.Contains(name)) category = "browser";
                else if (new [] { "teams", "ms-teams", "zoom", "discord", "skype", "webex" }.Contains(name)) category = "call";
            }
        } catch { category = "unknown"; }
        using (var self = Process.GetCurrentProcess()) return new { type = "result", id = id, ok = true, safeDesktop = safe, callsClear = clear, category = category,fullscreen=Fullscreen(),
            workingSetBytes = self.WorkingSet64, cpuSeconds = self.TotalProcessorTime.TotalSeconds };
    }
    static readonly object Gate = new object(), Output = new object();
    static readonly JavaScriptSerializer Json = new JavaScriptSerializer { MaxJsonLength = 2000000 };
    static readonly Dictionary<GlobalSystemMediaTransportControlsSession, Binding> Sessions = new Dictionary<GlobalSystemMediaTransportControlsSession, Binding>();
    static GlobalSystemMediaTransportControlsSessionManager Manager;
    static Timer Debounce;
    static Action Unsubscribe;
    static int Sequence;
    static bool Closed;
    class Binding { public string Id; public GlobalSystemMediaTransportControlsSession Session; public readonly List<Action> Off = new List<Action>(); }
    static T Wait<T>(IAsyncOperation<T> operation) {
        try {
            var until = DateTime.UtcNow.AddSeconds(5);
            while (operation.Status == AsyncStatus.Started) {
                if (DateTime.UtcNow > until) { operation.Cancel(); throw new TimeoutException(); }
                Thread.Sleep(10);
            }
            return operation.GetResults();
        } finally { operation.Close(); }
    }
    static Action Subscribe(object source, string name, object handler) {
        var type = source.GetType();
        var token = type.GetMethod("add_" + name).Invoke(source, new object[] { handler });
        return () => { try { type.GetMethod("remove_" + name).Invoke(source, new object[] { token }); } catch {} GC.KeepAlive(handler); };
    }
    static void Write(object value) { lock (Output) { Console.WriteLine(Json.Serialize(value)); Console.Out.Flush(); } }
    static void Changed() { if (!Closed) Debounce.Change(80, Timeout.Infinite); }
    static string Hash(string value) {
        using (var sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(value))).Replace("-", "").ToLowerInvariant();
    }
    static string Limited(string value) { return value == null ? null : value.Substring(0, Math.Min(value.Length, 500)); }
    static string Cover(GlobalSystemMediaTransportControlsSessionMediaProperties media) {
        try {
            if (media.Thumbnail == null) return null;
            using (var stream = Wait<IRandomAccessStreamWithContentType>(media.Thumbnail.OpenReadAsync())) {
                if (stream.Size == 0 || stream.Size > 262144 || (stream.ContentType != "image/png" && stream.ContentType != "image/jpeg")) return null;
                using (var reader = new DataReader(stream.GetInputStreamAt(0))) {
                    var load = reader.LoadAsync((uint)stream.Size);
                    var until = DateTime.UtcNow.AddSeconds(2);
                    while (load.Status == AsyncStatus.Started) { if (DateTime.UtcNow > until) { load.Cancel(); return null; } Thread.Sleep(10); }
                    var size = load.GetResults(); load.Close();
                    var bytes = new byte[size]; reader.ReadBytes(bytes);
                    return "data:" + stream.ContentType + ";base64," + Convert.ToBase64String(bytes);
                }
            }
        } catch { return null; }
    }
    static object Snapshot(Binding b) {
        var s = b.Session; var media = Wait<GlobalSystemMediaTransportControlsSessionMediaProperties>(s.TryGetMediaPropertiesAsync());
        var playback = s.GetPlaybackInfo(); var timeline = s.GetTimelineProperties(); var c = playback.Controls;
        var controls = new List<string>();
        if (c.IsPlayEnabled) controls.Add("play"); if (c.IsPauseEnabled) controls.Add("pause");
        if (c.IsNextEnabled) controls.Add("next"); if (c.IsPreviousEnabled) controls.Add("previous");
        if (c.IsPlaybackPositionEnabled) controls.Add("seek"); if (c.IsShuffleEnabled) controls.Add("shuffle"); if (c.IsRepeatEnabled) controls.Add("repeat");
        string title = Limited(media.Title), artist = Limited(media.Artist), album = Limited(media.AlbumTitle);
        return new { sessionId = b.Id, trackId = "metadata:" + Hash(s.SourceAppUserModelId + "\n" + title + "\n" + artist + "\n" + album),
            source = Limited(s.SourceAppUserModelId), title = title ?? "", artist = artist, album = album, cover = Cover(media),
            mediaType = media.PlaybackType.HasValue ? media.PlaybackType.Value.ToString().ToLowerInvariant() : null,
            status = playback.PlaybackStatus == GlobalSystemMediaTransportControlsSessionPlaybackStatus.Playing ? "playing" : playback.PlaybackStatus == GlobalSystemMediaTransportControlsSessionPlaybackStatus.Paused ? "paused" : "stopped",
            position = timeline.Position.TotalSeconds, duration = Math.Max(0, (timeline.EndTime - timeline.StartTime).TotalSeconds),
            updatedAt = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(), controls = controls,
            shuffle = playback.IsShuffleActive, repeat = playback.AutoRepeatMode.HasValue ? playback.AutoRepeatMode.Value.ToString().ToLowerInvariant() : null, evidence = "native" };
    }
    static void Refresh(object unused) {
        lock (Gate) {
            if (Closed) return;
            try {
                var current = new HashSet<GlobalSystemMediaTransportControlsSession>(Manager.GetSessions());
                foreach (var old in Sessions.Keys.Where(s => !current.Contains(s)).ToArray()) { foreach (var off in Sessions[old].Off) off(); Sessions.Remove(old); }
                foreach (var session in current) if (!Sessions.ContainsKey(session)) {
                    var binding = new Binding { Id = "gsmtc-" + (++Sequence), Session = session };
                    binding.Off.Add(Subscribe(session, "MediaPropertiesChanged", new TypedEventHandler<GlobalSystemMediaTransportControlsSession, MediaPropertiesChangedEventArgs>((s,e) => Changed())));
                    binding.Off.Add(Subscribe(session, "PlaybackInfoChanged", new TypedEventHandler<GlobalSystemMediaTransportControlsSession, PlaybackInfoChangedEventArgs>((s,e) => Changed())));
                    binding.Off.Add(Subscribe(session, "TimelinePropertiesChanged", new TypedEventHandler<GlobalSystemMediaTransportControlsSession, TimelinePropertiesChangedEventArgs>((s,e) => Changed())));
                    Sessions.Add(session, binding);
                }
                var rows = new List<object>();
                var active = Manager.GetCurrentSession();
                foreach (var binding in Sessions.Values.OrderByDescending(b => b.Session == active)) { try { rows.Add(Snapshot(binding)); } catch {} }
                Write(new { type = "sessions", sessions = rows });
            } catch { Write(new { type = "error", error = "GSMTC no pudo actualizar las sesiones." }); }
        }
    }
    static void Command(Dictionary<string, object> r) {
        string request = Convert.ToString(r["id"]);
        try {
            if (Convert.ToString(r["action"]) == "context") { Write(Context(request)); return; }
            if (!r.ContainsKey("sessionId") || !r.ContainsKey("action")) throw new ArgumentException();
            lock (Gate) {
                var binding = Sessions.Values.FirstOrDefault(b => b.Id == Convert.ToString(r["sessionId"]));
                if (binding == null) throw new InvalidOperationException();
                var s = binding.Session; var c = s.GetPlaybackInfo().Controls; bool result = false;
                switch (Convert.ToString(r["action"])) {
                    case "play": if (c.IsPlayEnabled) result = Wait<bool>(s.TryPlayAsync()); break;
                    case "pause": if (c.IsPauseEnabled) result = Wait<bool>(s.TryPauseAsync()); break;
                    case "next": if (c.IsNextEnabled) result = Wait<bool>(s.TrySkipNextAsync()); break;
                    case "previous": if (c.IsPreviousEnabled) result = Wait<bool>(s.TrySkipPreviousAsync()); break;
                    case "seek":
                        double seconds = Convert.ToDouble(r["value"]);
                        if (c.IsPlaybackPositionEnabled && !Double.IsNaN(seconds) && !Double.IsInfinity(seconds) && seconds >= 0 && seconds <= s.GetTimelineProperties().EndTime.TotalSeconds)
                            result = Wait<bool>(s.TryChangePlaybackPositionAsync((long)(seconds * TimeSpan.TicksPerSecond))); break;
                    case "shuffle": if (c.IsShuffleEnabled && r["value"] is bool) result = Wait<bool>(s.TryChangeShuffleActiveAsync((bool)r["value"])); break;
                    case "repeat":
                        var value = Convert.ToString(r["value"]);
                        if (c.IsRepeatEnabled && (value == "none" || value == "track" || value == "list")) result = Wait<bool>(s.TryChangeAutoRepeatModeAsync(value == "track" ? MediaPlaybackAutoRepeatMode.Track : value == "list" ? MediaPlaybackAutoRepeatMode.List : MediaPlaybackAutoRepeatMode.None)); break;
                }
                Write(new { type = "result", id = request, ok = result });
            }
            Changed();
        } catch { Write(new { type = "result", id = request, ok = false }); }
    }
    static int Main(string[] args) {
        Console.InputEncoding = new UTF8Encoding(false); Console.OutputEncoding = new UTF8Encoding(false);
        SetProcessDPIAware();
        if (args.Length == 1 && args[0] == "--context-only") {
            string input;
            while ((input = Console.ReadLine()) != null) {
                if (input.Length > 4096) continue;
                try {
                    var request = Json.Deserialize<Dictionary<string, object>>(input);
                    if (Convert.ToString(request["action"]) == "context") Write(Context(Convert.ToString(request["id"]),request.ContainsKey("environment")&&Convert.ToBoolean(request["environment"]),false));
                } catch {}
            }
            return 0;
        }
        try {
            Manager = Wait<GlobalSystemMediaTransportControlsSessionManager>(GlobalSystemMediaTransportControlsSessionManager.RequestAsync());
            Debounce = new Timer(Refresh, null, Timeout.Infinite, Timeout.Infinite);
            Unsubscribe = Subscribe(Manager, "SessionsChanged", new TypedEventHandler<GlobalSystemMediaTransportControlsSessionManager, SessionsChangedEventArgs>((s,e) => Changed()));
            Refresh(null);
            string line;
            while ((line = Console.ReadLine()) != null) {
                if (line.Length > 4096) continue;
                try { Command(Json.Deserialize<Dictionary<string, object>>(line)); } catch {}
            }
            return 0;
        } catch { Write(new { type = "error", error = "GSMTC no está disponible en este equipo." }); return 1; }
        finally { lock (Gate) { Closed = true; if (Debounce != null) Debounce.Dispose(); if (Unsubscribe != null) Unsubscribe(); foreach (var b in Sessions.Values) foreach (var off in b.Off) off(); Sessions.Clear(); } }
    }
}
