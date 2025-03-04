# MusicSync
A python script to synchronize + convert flac files to mp3 from A to B.

### Works
Converts new files in A.
Compares the existing files based on last modification time and converts/copies from A if newer.
Deletes files that dont exist anymore in A from B.

### Extra Stuff
To side step 2 ffmpeg problems with file metadata there are 2 extra scripts that get executed alongside:
- The metadata image sometimes makes the file 2x as large as it should be. This gets solved by converting without the image and adding it again after.
- The metadata fields that use multiple values get joined into a single one. Gets solved by reapplying the metadta again
