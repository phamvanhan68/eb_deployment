import datetime
import os
import boto3

# Conrjob
if __name__ == '__main__':
  main_path = os.path.dirname(os.path.realpath(__file__))
  file = open('{}/sha.txt'.format(main_path), 'w')
  file.write(str(datetime.datetime.now()))
