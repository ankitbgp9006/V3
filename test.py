import subprocess
import os
import sys

def download_with_ffmpeg(url, output_title=None):
    if not output_title:
        output_title = 'video'
        
    # Clean filename
    output_title = "".join(x for x in output_title if x.isalnum() or x in (' ', '-', '_')).strip()
    output_file = f'downloads/{output_title}.mp4'
    
    # Create downloads directory if it doesn't exist
    os.makedirs('downloads', exist_ok=True)
    
    # Prepare ffmpeg command
    ffmpeg_command = [
        'ffmpeg',
        '-i', url,
        '-c', 'copy',  # Copy streams without re-encoding
        '-bsf:a', 'aac_adtstoasc',  # Fix for aac audio
        '-y',  # Overwrite output file
        output_file
    ]
    
    try:
        print(f"\nStarting download of: {output_title}")
        process = subprocess.Popen(
            ffmpeg_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Monitor progress
        while True:
            line = process.stderr.readline()
            if not line and process.poll() is not None:
                break
            if 'time=' in line:  # This is a progress line
                sys.stdout.write('\r' + line.strip())
                sys.stdout.flush()
        
        if process.returncode == 0:
            print("\nDownload completed successfully!")
            return True
        else:
            error = process.stderr.read()
            print(f"\nDownload failed with error: {error}")
            return False
            
    except Exception as e:
        print(f"\nError during download: {str(e)}")
        return False

def test_download(url):
    success = download_with_ffmpeg(url)
    if not success:
        print("Download failed.")

if __name__ == "__main__":
    test_url = input("Enter the m3u8 URL to test: ")
    test_download(test_url) 