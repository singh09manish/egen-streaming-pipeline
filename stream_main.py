# -*- coding: utf-8 -*-
"""stream_main.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/14wDDL7L89v2bA2e7VjyoTx-wNOMx6r8i
"""

from apache_beam.options.pipeline_options import PipelineOptions
from google.cloud import pubsub_v1
from google.cloud import bigquery
import apache_beam as beam
import logging
import argparse
import sys
import re


PROJECT="egen-streaming-pipeline"
schema = 'remote_addr:STRING, timelocal:STRING, request_type:STRING, status:STRING, body_bytes_sent:STRING, http_referer:STRING, http_user_agent:STRING'
TOPIC = "projects/egen-streaming-pipeline/topics/userlogs"


def regex_clean(data):

    PATTERNS =  [r'(^\S+\.[\S+\.]+\S+)\s',r'(?<=\[).+?(?=\])',
           r'\"(\S+)\s(\S+)\s*(\S*)\"',r'\s(\d+)\s',r"(?<=\[).\d+(?=\])",
           r'\"[A-Z][a-z]+', r'\"(http|https)://[a-z]+.[a-z]+.[a-z]+']
    result = []
    for match in PATTERNS:
      try:
        reg_match = re.search(match, data).group()
        if reg_match:
          result.append(reg_match)
        else:
          result.append(" ")
      except:
        print("There was an error with the regex search")
    result = [x.strip() for x in result]
    result = [x.replace('"', "") for x in result]
    res = ','.join(result)
    return res


class Split(beam.DoFn):

    def process(self, element):
        from datetime import datetime
        element = element.split(",")
        d = datetime.strptime(element[1], "%d/%b/%Y:%H:%M:%S")
        date_string = d.strftime("%Y-%m-%d %H:%M:%S")
        
        return [{ 
            'remote_addr': element[0],
            'timelocal': date_string,
            'request_type': element[2],
            'body_bytes_sent': element[3],
            'status': element[4],
            'http_referer': element[5],
            'http_user_agent': element[6]
    
        }]

def main(argv=None):

   parser = argparse.ArgumentParser()
   parser.add_argument("--input_topic")
   parser.add_argument("--output")
   known_args = parser.parse_known_args(argv)


   p = beam.Pipeline(options=PipelineOptions())

   (p
      | 'ReadData' >> beam.io.ReadFromPubSub(topic=TOPIC).with_output_types(bytes)
      | "Decode" >> beam.Map(lambda x: x.decode('utf-8'))
      | "Clean Data" >> beam.Map(regex_clean)
      | 'ParseCSV' >> beam.ParDo(Split())
      | 'WriteToBigQuery' >> beam.io.WriteToBigQuery('{0}:Logdata.logdata'.format(PROJECT), schema=schema,
        write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND)
   )
   result = p.run()
   result.wait_until_finish()

if __name__ == '__main__':
  logger = logging.getLogger().setLevel(logging.INFO)
  main()