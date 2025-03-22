from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
import subprocess
import os
import sys

app = FastAPI()

# Konfigurasi folder dan path
DEFAULT_DOWNLOAD_FOLDER = "temp"

# Gunakan path absolut untuk mencegah error WinError 2
# Path FFMPEG - pastikan ini mengarah ke file ffmpeg yang benar
FFMPEG_PATH = os.path.abspath("./ffmpeg/bin/ffmpeg.exe")

# Path spotdl - Gunakan panggilan Python langsung alih-alih exe file
# Ini akan menjalankan modul spotdl dalam Python environment yang sama
# Alternatif 1: Menggunakan Python untuk memanggil modul spotdl
# SPOTDL_COMMAND = [sys.executable, "-m", "spotdl"]

# Alternatif 2: Menggunakan path absolut ke spotdl.exe (pastikan path ini benar)
SPOTDL_PATH = os.path.abspath("venv/Scripts/spotdl.exe")  # Hapus slash di awal

# Pastikan folder download default ada
os.makedirs(DEFAULT_DOWNLOAD_FOLDER, exist_ok=True)

class DownloadRequest(BaseModel):
    spotify_url: str
    download_folder: str = DEFAULT_DOWNLOAD_FOLDER

@app.get('/download')
def download_music(
    spotify_url: str = Query(..., description="Spotify track URL"),
    download_folder: str = Query(DEFAULT_DOWNLOAD_FOLDER, description="Custom download folder path (optional)")
):
    try:
        # Validasi dan persiapkan folder download
        if not download_folder:
            download_folder = DEFAULT_DOWNLOAD_FOLDER
        
        # Konversi ke path absolut jika diperlukan
        if not os.path.isabs(download_folder):
            download_folder = os.path.abspath(download_folder)
            
        # Pastikan folder download ada
        os.makedirs(download_folder, exist_ok=True)
        
        # Print working directory dan cek file ada
        current_dir = os.getcwd()
        print(f"Current directory: {current_dir}")
        print(f"Using download folder: {download_folder}")
        
        if not os.path.exists(FFMPEG_PATH):
            print(f"FFMPEG tidak ditemukan di: {FFMPEG_PATH}")
            raise HTTPException(status_code=500, detail=f"FFMPEG tidak ditemukan di: {FFMPEG_PATH}")
        
        if not os.path.exists(SPOTDL_PATH):
            print(f"SPOTDL tidak ditemukan di: {SPOTDL_PATH}")
            raise HTTPException(status_code=500, detail=f"SPOTDL tidak ditemukan di: {SPOTDL_PATH}")
            
        # Jalankan spotdl
        # Alternatif 1: Menggunakan Python Module
        """
        command = SPOTDL_COMMAND + [
            spotify_url,
            "--output", os.path.join(download_folder, "{artist} - {title}.mp3"),
            "--ffmpeg", FFMPEG_PATH
        ]
        """
        
        # Alternatif 2: Menggunakan spotdl.exe
        command = [
            SPOTDL_PATH,
            spotify_url,
            "--output", os.path.join(download_folder, "{artist} - {title}.mp3"),
            "--ffmpeg", FFMPEG_PATH
        ]
        
        print("Running command:", " ".join(command))

        # Gunakan subprocess dengan shell=True untuk Windows
        process = subprocess.run(command, check=True, capture_output=True, text=True)
        print("Output:", process.stdout)
        
        if process.stderr:
            print("Error output:", process.stderr)

        # Cari file hasil download (ambil yang terbaru)
        files = sorted(
            [f for f in os.listdir(download_folder) if f.endswith('.mp3')],
            key=lambda x: os.path.getmtime(os.path.join(download_folder, x)),
            reverse=True
        )

        if not files:
            raise HTTPException(status_code=404, detail="No file was downloaded.")

        latest_file = os.path.join(download_folder, files[0])
        print(f"File yang akan dikirim: {latest_file}")

        return FileResponse(latest_file, filename=files[0], media_type="audio/mpeg")

    except subprocess.CalledProcessError as e:
        print("Download error:", e)
        if hasattr(e, 'stdout'):
            print("Process stdout:", e.stdout)
        if hasattr(e, 'stderr'):
            print("Process stderr:", e.stderr)
        raise HTTPException(status_code=500, detail=f"Error downloading track: {str(e)}")
    except Exception as e:
        print("Unexpected error:", e)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Untuk debugging, tambahkan endpoint untuk cek path
@app.get("/check-paths")
def check_paths(download_folder: str = Query(DEFAULT_DOWNLOAD_FOLDER, description="Custom download folder to check")):
    if not os.path.isabs(download_folder):
        download_folder = os.path.abspath(download_folder)
        
    return {
        "current_directory": os.getcwd(),
        "ffmpeg_path": FFMPEG_PATH,
        "ffmpeg_exists": os.path.exists(FFMPEG_PATH),
        "spotdl_path": SPOTDL_PATH,
        "spotdl_exists": os.path.exists(SPOTDL_PATH),
        "default_download_folder": os.path.abspath(DEFAULT_DOWNLOAD_FOLDER),
        "default_folder_exists": os.path.exists(DEFAULT_DOWNLOAD_FOLDER),
        "custom_download_folder": download_folder,
        "custom_folder_exists": os.path.exists(download_folder),
        "python_executable": sys.executable
    }