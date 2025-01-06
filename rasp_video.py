import time
import os
from datetime import datetime

class VideoRecorder:
    def __init__(self):
        self.video_process = None  # Video sürecinin durumu

        self.video_dir = f"/home/{os.getlogin()}/Videolar"
        if not os.path.exists(self.video_dir):
            os.makedirs(self.video_dir)
        
    def change_directory(self):
        try:
            os.chdir(self.video_dir)
            print(f"Dizin değiştirildi: {self.video_dir}")
        except Exception as e:
            print(f"Dizin değiştirilemedi: {e}")

    def start_recording(self):
        if self.video_process is None:
            # Video kaydına başlama
            self.change_directory()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_filename = f"video_{timestamp}.h264"
            print(f"Video Kaydı Başlatıldı: {video_filename}")
            try:
                self.video_process = os.popen(f"libcamera-vid -o {video_filename} -t 0")
            except Exception as e:
                print(f"Video başlatılamadı: {e}")
        else:
            print("Zaten Kayıt Yapılıyor.")

    def stop_recording(self):
        if self.video_process is not None:
            # Video kaydını durdurma
            print("Video Kaydı Durduruldu.")
            try:
                self.video_process.close()
            except Exception as e:
                print(f"Video durdurulamadı: {e}")
            finally:
                self.video_process = None
        else:
            print("Şu an Kayıt Yapılmıyor.")

def main():

    video_recorder = VideoRecorder()
    
    start_time = time.time()
    
    video_recorder.start_recording()

    while True:
        time_elapsed = int(time.time() - start_time)
        
        if time_elapsed >= 10:  # 10 saniye geçtiyse
            video_recorder.stop_recording()
            break
 
if __name__ == "__main__":
    main()
