import os
import sys
import codecs
import requests
from optparse import OptionParser
import argparse

from lxml import etree

from babelsubs.storage import time_expression_to_milliseconds
from babelsubs.storage import milliseconds_to_time_clock_exp

import api_key

class NFOutput(object):

    NF_HEAD = u"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
    <tt xmlns="http://www.w3.org/ns/ttml" 
        xmlns:ttp="http://www.w3.org/ns/ttml#parameter" 
        xmlns:tts="http://www.w3.org/ns/ttml#styling" 
        xml:lang="{0}">

    <head>
        <styling>
            <style textStyle="italic" xml:id="emphasis"/>
            <style fontWeight="bold" xml:id="strong"/>
            <style textDecoration="underline" xml:id="underlined"/>
        </styling>
        <layout>
            <region xml:id="top" 
                    tts:backgroundColor="transparent" 
                    tts:showBackground="whenActive"
                    tts:extent="100% 100%"
                    tts:origin="0% 0%"
                    tts:textAlign='center'/> 
        </layout>
    </head>
"""

    NF_END = "</tt>"


    def api_get_request(self, url_part, output_type='json'):
        url = 'http://www.amara.org' + url_part
    
        headers = { 'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-apikey': api_key.key,
                    'X-api-username': api_key.username,
                  }
        try:
            r = requests.get(url, headers=headers)
        except requests.exceptions.ConnectionError as e:
            print ('Connection error, check your configured username and key '
                   'in api_key.py and / or try again later')
            sys.exit()

        if r.reason == 'NOT FOUND':
            print 'Request failed for %s, check your video id and/or languages' % url_part
            sys.exit()

        if output_type == 'json':
            try:
                return r.json()
            except:
                print 'Error:  %s' % r.content
                print 'Check your configured username and key in api_key.py'
                sys.exit()
        else:
            return r.content


    def _convert_to_24fps(self, time_str):
        ms = time_expression_to_milliseconds(time_str)
        fps_24 = ms/1.001001001
        return milliseconds_to_time_clock_exp(fps_24)

    def process_subs(self, subs, timeshift=None):
        """Update the dfxp subs to NF ttml.

           -- change $$ to set the region attribute on paragraph to top.
           -- grab the lang code and add it to NF header
           -- remove any empty subtitle lines
           -- If video is at 23.86 fps - shift subs to 24 fps, if required.
        """
  
        root = etree.fromstring(subs)
        body = root[1]
        body.attrib["{http://www.w3.org/ns/ttml#styling}textAlign"] = 'center'
        if 'region' in body.attrib:
            del body.attrib['region']
        top = '$$'
        lang = root.get("{http://www.w3.org/XML/1998/namespace}lang")

        for p in body.iter("{http://www.w3.org/ns/ttml}p"):
            #Remove blank lines
            line_text = p.xpath("string()").strip()
            if len(line_text) < 1:
                p.getparent().remove(p)
                continue


            brs = [x for x in p if x.tag.endswith('br')]
            spans = [x for x in p if x =='{http://www.w3.org/1999/xhtml}span']
            for t in spans:
                if '$$' in t.text:
                    t.text = t.text.replace(top, "")
                if t.tag == "{http://www.w3.org/1999/xhtml}br":
                    brs.append(t)
            if top in unicode(p.text):
                p.attrib['region'] = 'top'
                ## Look for extra $$s in the text that come in of after span formatting.
                for el in p.iter():
                    try:
                        el.text = el.text.replace(top, "")
                        el.tail.replace(top, "")
                    except:
                        pass
            # Videos with 23.98 fps need to be shifted to 24fps output files         
            if timeshift:
                p.attrib['begin'] = self._convert_to_24fps(p.attrib['begin'])
                p.attrib['end'] = self._convert_to_24fps(p.attrib['end'])
        #update the heading with the correct language
        head = self.NF_HEAD.format(lang)
        return head, body

    

    def output_for_nf(self, vid, lc, title, timeshift):
        fn = '%s.%s.dfxp' %(title, lc)
        req_url = ('/api2/partners/videos/%s/languages/%s/subtitles/'
                   '?format=dfxp'% (vid, lc))
        subs = self.api_get_request(req_url, output_type='content')
        head, body = self.process_subs(subs, timeshift)
        processed_body = etree.tostring(body, pretty_print=True)
        processed_subs =  u''.join([head, processed_body, self.NF_END])
        f = codecs.open(fn, 'w', encoding="utf-8")
        f.write(unicode(processed_subs))
        f.close()
        print processed_subs

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Reformat dfxp subtitles to be NF compliant')
    #parser = OptionParser()
    parser.add_argument("-i", "--id", dest="video_id", required=True,
                        action='store', help=("One or more (comma separated) "
                                            "Amara video ids"))
    parser.add_argument("-l", "--langs", action="store", dest="langs",
                        help=("List of language codes (ex: en, fr) to process, "
                              "leave blank to process all available"))
    parser.add_argument("-t", "--timeshift", dest="ts",
                        action='store_true', help=('Warning: assumes all videos '
                        'listed are 23.98 fps and converts to 24 fps'))

    options = parser.parse_args()
    #(options, args) = parser.parse_args()
    videos = [v for v in options.video_id.split(',')]
    timeshift = options.ts
    n = NFOutput()
    for video in videos:
        details = n.api_get_request('/api2/partners/videos/%s/' % video)
        title = getattr(details, 'title', details['all_urls'][0].split('/')[-1])
        if options.langs:
            langs = [l for l in options.langs.split(',')]
        else:
            langs = [l['code'] for l in details['languages']]
        for lc in langs:
            n.output_for_nf(video, lc, title, timeshift)
