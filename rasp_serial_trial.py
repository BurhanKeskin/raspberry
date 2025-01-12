# Raspberry Üzerinde Serial Porttan Sürekli Sorgu Yaparak Sadece Video Kaydı Başlatma ve Durdurma

import serial
import time
import os
from datetime import datetime
import subprocess


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
            self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.video_filename = f"video_{self.timestamp}.h264"
            print(f"Video Kaydı Başlatıldı: {self.video_filename}")
            try:
                # Süresiz kayıt için libcamera-vid komutunu başlat
                self.video_process = subprocess.Popen(
                    ["libcamera-vid", "-o", self.video_filename, "-t", "0"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            except Exception as e:
                print(f"Video başlatılamadı: {e}")
        else:
            print("Zaten Kayıt Yapılıyor.")

    def stop_recording(self):
        if self.video_process is not None:
            # Video kaydını durdurma
            print("Video Kaydı Durduruluyor...")
            try:
                self.video_process.terminate()  # İşlemi sonlandır
                self.video_process.wait()      # İşlemin tamamen kapandığından emin ol
                print("Video Kaydı Durduruldu.")
            except Exception as e:
                print(f"Video durdurulamadı: {e}")
            finally:
                self.video_process = None
        else:
            print("Şu an Kayıt Yapılmıyor.")

    
    def convertFromH264_to_MP4(self):
        
        h264_file = f"/home/{os.getlogin()}/Videolar/{self.video_filename}"
        self.mp4_file = f"/home/{os.getlogin()}/Videolar/video_{self.timestamp}.mp4"
        self.outputVideo = f"/home/{os.getlogin()}/Videolar/video_{self.timestamp}_processed.mp4"
        

        try:
            subprocess.run(
                ["ffmpeg", "-i", h264_file, "-c:v", "copy", self.mp4_file],
                check=True
            )
            print(f"Dönüştürme başarılı: {self.mp4_file}")
        except subprocess.CalledProcessError as e:
            print(f"Dönüştürme başarısız: {e}")
        except FileNotFoundError:
            print("FFmpeg yüklenmemiş. Lütfen önce FFmpeg'i yükleyin.")


def main():

    try:
        ser = serial.Serial('/dev/serial0', 115200, timeout=1)  # UART üzerinden Arduino ile haberleşme
    except serial.SerialException as e:
        print(f"Seri port hatası: {e}")
        exit(1)
    except Exception as e:
        print(f"Bilinmeyen bir hata oluştu: {e}")
        exit(1)

    state = "BEKLEME"  # Başlangıç durumu
    video_recorder = VideoRecorder()
    
    try:
        print("Arduinodan komut bekleniyor...")
        while True:
            if ser.in_waiting > 0:
                command = ser.read().decode().strip()  # Arduino'dan gelen komut
                
                if state == "BEKLEME" and command == 'S':
                    print("Video kaydı başlatılıyor...")
                    video_recorder.start_recording()
                    state = "KAYITTA"
                
                elif state == "KAYITTA" and command == 'E':
                    print("Video kaydı durduruluyor...")
                    video_recorder.stop_recording()
                    print("Video işleniyor...")
                    time.sleep(2)
                    video_recorder.convertFromH264_to_MP4()
                    time.sleep(2)
                    
                    state = "BEKLEME"
                    print("Bekleme durumuna dönüldü.")
                
                elif state == "BEKLEME" and command == 'E':
                    print("Henüz kayıt başlatılmadı. Sinyal bekleniyor.")
                
                elif state == "KAYITTA" and command not in ['S', 'E']:
                    print("Kayıt sırasında tanımlanamayan komut alındı.")
                
                else:
                    print(f"Tanımlanamayan durum: {state} ve komut: {command}")
    except Exception as e:
        print(f"Hata oluştu: {e}")
    
if __name__ == "__main__":
    main()
