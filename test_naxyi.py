import eyed3
from eyed3.id3.frames import ImageFrame

audiofile = eyed3.load('song.mp3')
if (audiofile.tag == None):
    audiofile.initTag()
audiofile.tag.title = u'хахахаха'
audiofile.tag.album = u'пидор блять'
audiofile.tag.images.set(3, open("img.jpg", 'rb').read(), 'image/png')
audiofile.tag.save(version=eyed3.id3.ID3_V2_3)