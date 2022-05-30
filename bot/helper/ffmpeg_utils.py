import os
import sys
import json
import time
import ffmpeg
import cv2
from bot import tmp_dir
from subprocess import call, check_output
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from time import sleep


def get_codec(filepath, channel='v:0'):
    output = check_output(['ffprobe', '-v', 'error', '-select_streams', channel,
                            '-show_entries', 'stream=codec_name,codec_tag_string', '-of', 
                            'default=nokey=1:noprint_wrappers=1', filepath])
    return output.decode('utf-8').split()

def encode(filepath):
    basefilepath, extension = os.path.splitext(filepath)
    basepath = os.path.dirname(os.path.dirname(filepath))

    
    crawler_path = 'crawler.mp4'
    ready_crawler_filepath = os.path.join(basepath, tmp_dir,'ready_crawler.mp4' )
    crawler_gif_filepath = os.path.join(basepath, tmp_dir, 'crawler.gif')
    palette_filepath = os.path.join(basepath, tmp_dir, 'palette.png')


    output_filepath = basefilepath + '.masked' + '.mp4'

    assert(output_filepath != filepath)
    if os.path.isfile(output_filepath):
        print('Skipping "{}": file already exists'.format(output_filepath))
        return None

    print(filepath)
    # Get the video channel codec
    video_codec = get_codec(filepath, channel='v:0')
    if video_codec == []:
        print('Skipping: no video codec reported')
        return None

    #Video Dimension
    vcap = cv2.VideoCapture(filepath)
    if vcap.isOpened():
        video_width = vcap.get(cv2.CAP_PROP_FRAME_WIDTH)
        video_height = vcap.get(cv2.CAP_PROP_FRAME_HEIGHT)

    #Convert Crawler MP4 to Corresponding Dimension
    crawler_opts = f'-vf scale={video_width}:-2,setsar=1:1 -c:v libx264 -c:a copy'
    call(['ffmpeg', '-y', '-i', crawler_path] + crawler_opts.split() + [ready_crawler_filepath])

    
    #Get Ready Crawler Height
    vcap2 = cv2.VideoCapture(ready_crawler_filepath)
    if vcap2.isOpened():
        crawler_height = vcap2.get(cv2.CAP_PROP_FRAME_HEIGHT)


    #Generate Platte 
    palette_opts = '-vf palettegen'
    call(['ffmpeg', '-y', '-i', ready_crawler_filepath] + palette_opts.split() + [palette_filepath])

    #Convert Ready Crawler to GIF
    gif_opts = f'-i {palette_filepath} -filter_complex paletteuse -r 20'
    call(['ffmpeg', '-y', '-i', ready_crawler_filepath] + gif_opts.split() + [crawler_gif_filepath])


    #Add Crawler to Video
    final_opts = f'-stream_loop -1 -i {crawler_gif_filepath} -filter_complex pad=iw:(ih+{crawler_height}):0:{crawler_height},overlay=x=(main_w-overlay_w):y=(main_h-overlay_h)/(main_h-overlay_h):shortest=1[out] -map [out] -map 0:a? -c:v h264_nvenc -c:a copy'
    call(['ffmpeg', '-y', '-i', filepath] + final_opts.split() + [output_filepath])


    os.remove(filepath)
    os.remove(ready_crawler_filepath)
    os.remove(crawler_gif_filepath)
    os.remove(palette_filepath)

    return output_filepath

def get_thumbnail(in_filename, path, ttl):
    out_filename = os.path.join(path, str(time.time()) + ".jpg")
    open(out_filename, 'a').close()
    try:
        (
            ffmpeg
            .input(in_filename, ss=ttl)
            .output(out_filename, vframes=1)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        return out_filename
    except ffmpeg.Error as e:
      return None

def get_duration(filepath):
    metadata = extractMetadata(createParser(filepath))
    if metadata.has("duration"):
      return metadata.get('duration').seconds
    else:
      return 0

def get_width_height(filepath):
    metadata = extractMetadata(createParser(filepath))
    if metadata.has("width") and metadata.has("height"):
      return metadata.get("width"), metadata.get("height")
    else:
      return 1280, 720