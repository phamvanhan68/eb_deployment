import time
import json
import os
import hashlib

from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

REVIEW_BUTTON = os.getenv('REVIEW_BUTTON')
SCROLLABLE_DIV = os.getenv('SCROLLABLE_DIV')
CLASS_REVIEW_DIV = os.getenv('CLASS_REVIEW_DIV')
CLASS_REVIEW_RATE = os.getenv('CLASS_REVIEW_RATE_SPAN')
CLASS_REVIEW_TIME = os.getenv('CLASS_REVIEW_TIME_SPAN')
CLASS_REVIEW_TEXT = os.getenv('CLASS_REVIEW_TEXT_SPAN')
CLASS_FULL_NAME = os.getenv('CLASS_FULL_NAME_DIV')
CLASS_AVATAR = os.getenv('CLASS_AVATAR_IMG')

class Crawler:
    number_of_review = 0
    is_valid = False

    def __init__(self, driver, place_id, logging, service_number):
        self.driver = driver
        self.place_id = place_id
        self.logging = logging
        self.service_number = service_number
        
        
    def get_review_button(self):
        """Get the all review button"""
        try:
            return self.driver.find_element_by_xpath(REVIEW_BUTTON)
        except Exception as e:
            return None
    
    
    def get_scroll_div(self):
        """Get scroll element"""
        try:
            return self.driver.find_elements_by_xpath(SCROLLABLE_DIV)
        except Exception as e:
            return []
    
    def beautifulsoup_parser(self):
        """Parse HTML into BeautifulSoup"""
        response = BeautifulSoup(self.driver.page_source, 'html.parser')
        reviews = response.find_all('div', class_=CLASS_REVIEW_DIV)
        return reviews
        
    def click_review_btn(self):
        """
        Click the all review button
        """
        try:
            first_review_button = self.get_review_button()

            if first_review_button:
                if isinstance(first_review_button, list):
                    first_review_button = first_review_button[0]

                first_review_button_text = ''

                first_review_button_text = first_review_button.text.split(' ')[0]

                if first_review_button_text.isnumeric():
                    self.number_of_review = int(first_review_button_text)

                if self.number_of_review > 0:
                    try:
                        first_review_button.click()
                        self.logging.info('       First review button works')
                        self.is_valid = True
                    except Exception as e:
                        self.logging.error('       Error when clicking irst review button', str(e))
            else:
                raise Exception('Can not find out first review button')

        except Exception as e:
            self.is_valid = False
            
    def crawl(self, overview_csv_json, DEVELOPMENT_MODE, OUTPUT_FOLDER, main_path, recall_array = None):
        """Do scroll and crawl out the data reviews
        :param overview_csv_json: json data for tracking the output
        :param DEVELOPMENT_MODE: dev or prod mode
        :param OUTPUT_FOLDER: path to put data review at local
        :param main_path: path to directly working folder
        :param recall_array: error array that process will re-run again 1 more time at the end
        :return 
        """
        json_string = None
        file_name = None
        
        if self.is_valid:
            self.logging.info('       Found {} review(s) at first'.format(self.number_of_review))
            self.logging.info('       Waiting for getting the reviews')
            time.sleep(1)
            
            # Scrolldown until we get the review fully
            scrollable_div = self.get_scroll_div()
            scroll_count = 0
            loaded_review = 0
            estimate = 0
            
            while len(scrollable_div) > 0 and loaded_review < self.number_of_review:
                self.logging.info('       Scrolling down...{}'.format(scroll_count))
                scrollable_div[0].location_once_scrolled_into_view
                time.sleep(1)
                scrollable_div = self.get_scroll_div()
                reviews = self.beautifulsoup_parser()
                loaded_review = len(reviews)
                
                
                scroll_count += 1
                estimate = scroll_count * 2
                
                if estimate > self.number_of_review and len(scrollable_div) > 0:
                    scrollable_div = []
                    scroll_count = 0
                
                    if recall_array is not None:
                        recall_array.append({
                            "serviceApprovalNumber": self.service_number,
                            "placeId": self.place_id,
                        })
                        text = ' Error - Process will run it again - at {} - {}'.format(self.service_number, self.place_id)
                        print(text)
                        self.logging.error(text)
                    
                    return [None, None]
            else:
                if scroll_count > 0:
                    self.logging.info('       Loaded full review.')
                else:
                    self.logging.warning("       Can not find out the scroll div, perhaps we've got full reviews or there is no review.")


            reviews = self.beautifulsoup_parser()

            review_data = []

            for result in reviews:
                button_see_more = result.find('button', text='More')

                if button_see_more:
                    more_button_class_array = button_see_more['class']
                    more_button_class = more_button_class_array
                    
                    if isinstance(more_button_class_array, list):
                        more_button_class = ' '.join(more_button_class_array)
                    
                    more_btn = self.driver.find_elements_by_xpath("//button[@class='{}' and @data-review-id='{}' and @jsan='{}']".format(
                        more_button_class, button_see_more['data-review-id'], button_see_more['jsan']
                    ))

                    if len(more_btn) > 0:
                        more_btn[0].click()
                    
            time.sleep(1)

            # repeat the code to make it run faster
            reviews = self.beautifulsoup_parser()

            for result in reviews:
                review_rate = result.find('span', class_=CLASS_REVIEW_RATE)["aria-label"]
                review_time = result.find('span', class_=CLASS_REVIEW_TIME).text
                review_text = result.find('span', class_=CLASS_REVIEW_TEXT).text
                fullname = result.find('div', class_=CLASS_FULL_NAME).text
                avatar = result.find('img', class_=CLASS_AVATAR)['src']
                
                review_data.append({
                    'totalRating': review_rate.strip(),
                    'fullname': fullname.strip(),
                    'reviewDescription': review_text.strip(),
                    'time': review_time.strip(),
                    'avatar': avatar,
                })
            if len(review_data) > 0:
                file_name = self.service_number if DEVELOPMENT_MODE else hashlib.md5(self.service_number.encode()).hexdigest()
                json_string = {
                    'service_number': self.service_number,
                    'data':review_data
                }
                # jsonFile = open('{}/{}{}.json'.format(main_path, OUTPUT_FOLDER, file_name), 'w')
                # jsonFile.write(json.dumps(json_string))
                # jsonFile.close()
                self.logging.info('       Got {} reviews, wrote to file named {}'.format(len(review_data), file_name))
                overview_csv_json.append({
                    'number_of_reviews': len(review_data),
                    'service_number': self.service_number
                })
                
            return [json_string, file_name]
        else:
            self.logging.warning("       Can't find the review, perhaps there is no review or invalid place id.")
            return [None, None]
            
    def write_json_to_s3(self, json_object, bucket_name, path, filename = None, s3_client = None):
        """Upload a json object to S3 bucket
        :param json_object: json data to upload
        :param bucket: s3 bucket to upload to
        :param path: path to upload to
        :param filename: S3 object name. If not specified then filename is used
        :param s3_client: S3 client. If not specified then return error
        :return: True if file was uploaded, else False
        """
        
        if s3_client:
            try:
                s3_client.put_object(
                    Body = str(json.dumps(json_object)),
                    Bucket = bucket_name,
                    Key = path + filename + '.json'
                )
                return True
            except Exception as error:
                self.logging.error(str(error))
                
        else:
            self.logging.error("Cannot find out the S3 Client! Please check write_json_to_s3 func again!")
        
        return False