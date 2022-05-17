import time
import json
import os
import logging
import csv
import threading
import queue
import boto3
from io import BytesIO

from selenium import webdriver
# from bs4 import BeautifulSoup
from dotenv import load_dotenv
from datetime import datetime
from selenium.webdriver.chrome.options import Options

from Crawler import Crawler

from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()
SHOULD_STOP = False

class Worker(threading.Thread):
    def __init__(self, q, *args, **kwargs):
        global SHOULD_STOP
        
        self.q = q
        super().__init__(*args, **kwargs)
    def run(self):
        while True:
            try:
                work = self.q.get(timeout=5)  # 5s timeout
                arg_input = work['arg']
                
                work['func'](arg_input['json_object'], arg_input['bucket_name'], arg_input['path'], arg_input['filename'], arg_input['s3_client'])
                self.q.task_done()
            except queue.Empty:
                time.sleep(2)
                
                if SHOULD_STOP:
                    text = "Stopped the thread"
                    logging.info(text)
                    print(text)
                    return


def main():
    global SHOULD_STOP # Use for controling the thread that loads result JSON file into S3
    
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    TODAY = str(datetime.today())
    main_path = os.path.dirname(os.path.realpath(__file__))
    logging.basicConfig(filename='{}/logs/{}.log'.format(main_path, TODAY), level=logging.INFO)
    
    # Generating 2 threads for loading files to S3
    q = queue.Queue()
    for id, _ in enumerate(range(2)):
        text = "Generating thread: {}".format(id + 1)
        logging.info(text)
        print(text)
        # Execute the function that sends file to S3
        Worker(q).start()
    q.join()  # blocks until the queue is empty

    # S3 client
    s3_client = boto3.client(
        's3',
        aws_access_key_id = AWS_ACCESS_KEY_ID,
        aws_secret_access_key = AWS_SECRET_ACCESS_KEY
    )
    
    DRIVER_LOCATION = '/usr/bin/chromedriver'

    options = Options()
    options.add_argument("--headless")
    options.add_argument("window-size=1400,1500")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("start-maximized")
    options.add_argument("enable-automation")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(executable_path=ChromeDriverManager().install(), options=options)
    
    # driver = webdriver.Chrome(options=options)
    driver.binary_location = DRIVER_LOCATION
    
    OUTPUT_FOLDER = os.getenv('OUTPUT_FOLDER')
    GOOGLE_LINK = os.getenv('GOOGLE_LINK')
    STAGE = os.getenv('STAGE', 'dev')
    INPUT_SOURCE = os.getenv('INPUT_SOURCE', 'S3')
    TEST_MODE = bool(int(os.getenv('TEST_MODE', 0)))
    S3_TRIGGER = bool(int(os.getenv('S3_TRIGGER', 1)))
    PRINT_OUTPUT = bool(int(os.getenv('PRINT_OUTPUT', 0)))
    
    
    DEVELOPMENT_MODE = True if STAGE == 'dev' else False
    FREFIX_FILE = ('review_dev_' if DEVELOPMENT_MODE else 'review_prod_') if S3_TRIGGER else 'test_'
    BUCKET = 'space-google-review-crawler-dev' if DEVELOPMENT_MODE else 'space-google-review-crawler'
    
    dev_mode_string = ">>> Running on development mode (output file name won't be hashed): {}".format(DEVELOPMENT_MODE)
    test_mode_string = ">>> Running on test mode (run first 10 centres from input) : {}".format(TEST_MODE)
    s3_trigger = ">>> Trigger S3: {} - Prefix: {}".format(S3_TRIGGER, FREFIX_FILE)
    input_data_source = ">>> Input data source: {}".format(INPUT_SOURCE)

    print(dev_mode_string)
    print(test_mode_string)
    print(s3_trigger)
    print(input_data_source)
    
    logging.info(dev_mode_string)
    logging.info(test_mode_string)
    logging.info(s3_trigger)
    logging.info(input_data_source)

    # Get data from input file
    place_ids = []
    data_length = 0
        
    # Get data source
    if INPUT_SOURCE != "S3":
        try:
            place_ids_file = open('{}/input/input.json'.format(main_path), 'r')
            place_ids = json.load(place_ids_file)
            data_length = len(place_ids)
        except Exception as e:
            logging.error(">>> ", str(e))            
    else:
        try:
            f = BytesIO()
            s3_client.download_fileobj(BUCKET, "_input_config.json", f)
            data = json.loads(f.getvalue())
            if len(data) > 0:
                place_ids = data
                data_length = len(data)
        except Exception as e:
            print(e)
            
    if len(place_ids) <= 0:
        text = 'Data source: {} - There is no input data'.format(INPUT_SOURCE)
        print(text)
        logging.warning(text)
        SHOULD_STOP = True
        return
    

    # Check if running in TEST_MODE 
    if TEST_MODE:
        place_ids = place_ids[0: 10]
        data_length = len(place_ids)
        
        
    overview_csv_json = []
    recall_array = []
    start_time = datetime.now()

    for idx, place_object in enumerate(place_ids):        
        service_number = place_object['serviceApprovalNumber']
        place_id = place_object['placeId']
        
        print('Current progress: {}/{}'.format(idx+1, data_length))
        logging.info(">>> {} - Working on {}".format(idx, place_id))
        
        url = '{}?api=1&query=Google&query_place_id={}'.format(
        GOOGLE_LINK,
        place_id
        )
        driver.get(url)
        
        crawler = Crawler(driver, place_id, logging, service_number)
        crawler.click_review_btn();
        [json_string, filename] = crawler.crawl(overview_csv_json, DEVELOPMENT_MODE, OUTPUT_FOLDER, main_path, recall_array)
        if json_string and filename:
            q.put_nowait({
                'func': crawler.write_json_to_s3,
                'arg': {
                    'json_object': json_string,
                    'bucket_name': BUCKET,
                    'path': '',
                    'filename': FREFIX_FILE + filename,
                    's3_client': s3_client
                }
            })
    
    
    if len(recall_array) > 0:
        filename = 'ERROR_{}'.format(TODAY)
        error_text = 'Creating error file named: {}'.format(filename)
        logging.error(error_text)
        print(error_text)

        json_string_error = json.dumps(recall_array)
        json_file = open('{}/{}{}.json'.format(main_path, OUTPUT_FOLDER, filename), 'w')
        json_file.write(json_string_error)
        json_file.close()
        
    driver.close()

    if PRINT_OUTPUT:
        count = 0
        data_file = open('{}/{}overview_csv_{}.csv'.format(main_path, OUTPUT_FOLDER, TODAY), 'w')
        csv_writer = csv.writer(data_file)

        for record in overview_csv_json:
            if count == 0:
                header = record.keys()
                csv_writer.writerow(header)
                count += 1
            csv_writer.writerow(record.values())
        
    end = datetime.now() - start_time
    print("Took {}".format(end))
    logging.info("Took {}".format(end))
    
    SHOULD_STOP = True
