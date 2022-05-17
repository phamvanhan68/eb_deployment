sudo chmod 777 /var/app/current
sudo chmod 777 /var/app/current/logs

cd /var/app/current
virtualenv -p python3 /var/app/current/venv
source /var/app/current/venv/bin/activate
pip install -r requirements.txt 


