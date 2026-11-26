// Test-only muted source. Never packaged or used by production.
using System;
using System.Threading;
using Windows.Foundation;
using Windows.Media;
using Windows.Media.Core;
using Windows.Media.Playback;
using Windows.Storage;
class MusicFixture {
    static T Wait<T>(IAsyncOperation<T> operation) { while (operation.Status == AsyncStatus.Started) Thread.Sleep(10); var result = operation.GetResults(); operation.Close(); return result; }
    static int Main(string[] args) {
        using (var player = new MediaPlayer()) {
            player.IsMuted = true; player.IsLoopingEnabled = true; player.CommandManager.IsEnabled = false;
            player.Source = MediaSource.CreateFromStorageFile(Wait<StorageFile>(StorageFile.GetFileFromPathAsync(args[0])));
            var controls = player.SystemMediaTransportControls;
            controls.IsEnabled = true; controls.IsPlayEnabled = true; controls.IsPauseEnabled = true;
            controls.IsNextEnabled = true; controls.IsPreviousEnabled = true;
            int track = 0;
            Action update = () => {
                controls.DisplayUpdater.Type = MediaPlaybackType.Music;
                controls.DisplayUpdater.MusicProperties.Title = track == 0 ? "Karen Music QA A" : "Karen Music QA B";
                controls.DisplayUpdater.MusicProperties.Artist = "Synthetic QA";
                controls.DisplayUpdater.MusicProperties.AlbumTitle = "Temporary fixture";
                controls.DisplayUpdater.Update();
            };
            var handler = new TypedEventHandler<SystemMediaTransportControls,SystemMediaTransportControlsButtonPressedEventArgs>((s,e) => {
                if (e.Button == SystemMediaTransportControlsButton.Pause) { player.Pause(); controls.PlaybackStatus = MediaPlaybackStatus.Paused; }
                if (e.Button == SystemMediaTransportControlsButton.Play) { player.Play(); controls.PlaybackStatus = MediaPlaybackStatus.Playing; }
                if (e.Button == SystemMediaTransportControlsButton.Next) { track = 1; update(); }
                if (e.Button == SystemMediaTransportControlsButton.Previous) { track = 0; update(); }
            });
            var token = typeof(SystemMediaTransportControls).GetMethod("add_ButtonPressed").Invoke(controls,new object[]{handler});
            player.Play(); controls.PlaybackStatus = MediaPlaybackStatus.Playing; update();
            Console.WriteLine("READY"); Console.Out.Flush(); Console.ReadLine();
            typeof(SystemMediaTransportControls).GetMethod("remove_ButtonPressed").Invoke(controls,new object[]{token});
            player.Pause(); controls.IsEnabled = false; GC.KeepAlive(handler);
        }
        return 0;
    }
}
