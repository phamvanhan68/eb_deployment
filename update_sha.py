import datetime
import os

main_path = os.path.dirname(os.path.realpath(__file__))
file = open('{}/sha.txt'.format(main_path), 'w')
file.write(str(datetime.datetime.now()))
