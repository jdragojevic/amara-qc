### Simple script for converting Amara output dfxp to NF compliant dfxp.

###To install:
 * ```$ virtualenv env-qc ```
 * ``` source env-qc/bin/activate ```
 * ``` pip install -r requirements.txt ```
 * Update api_key.py with your Amara username and api key

### ```usage: python nf_output.py [-h] -i VIDEO_ID [-l LANGS] [-t]```

```

Reformat dfxp subtitles to be NF compliant ttml

optional arguments:

  -h, --help            show this help message and exit

  -i VIDEO_ID, --id VIDEO_ID
                        One or more (comma separated) Amara video ids

  -l LANGS, --langs LANGS
                        List of language codes (ex: en, fr) to process, leave
                        blank to process all available

  -t, --timeshift       Warning: assumes all videos listed are 23.98 fps and
                        converts to 24 fps

```
