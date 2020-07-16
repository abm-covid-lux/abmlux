"""Tool to join PNG images into a video.  Used to stitch together the output from many reporters
that produce map pictures per time tick"""


import os
import os.path as osp
import logging

from tqdm import tqdm
import cv2


log = logging.getLogger("join_images")

DESCRIPTION = "Joins directories of images together"
HELP        = """DIRECTORY [VIDEO_FILENAME] [FPS]"""

#pylint: disable=unused-argument
def main(config, directory, video_filename="video.avi", fps=20):
    """Entry point for the image joining tool.

    Parameters:
      config (abmlux.Config):The config object describing the current simulation
      directory (str):The directory where files to join reside
      video_filename (str):The video filename to output to.  Defaults to 'video.avi'
      fps (float):The FPS to use when generating a video.  Defaults to 20
    """

    log.info("Looking for PNGs in %s, writing video to %s", directory, video_filename)

    images = [img for img in os.listdir(directory) if img.endswith(".png")]
    images.sort()
    log.info("Found %i images", len(images))

    # Produce
    frame = cv2.imread(os.path.join(directory, images[0]))
    height, width, _ = frame.shape

    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    video = cv2.VideoWriter(video_filename, fourcc, float(fps), (width, height))
    for image in tqdm(images):
        video.write(cv2.imread(osp.join(directory, image)))

    cv2.destroyAllWindows()
    video.release()
    log.info("Done!")
