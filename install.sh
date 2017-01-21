apt-get update
apt-get -y install git
git clone https://github.com/kor-ka/uproar_client.git
cd uproar_client

apt-get -y install python-pip
apt-get -y install mpg123
pip install -r requirements.txt

chmod +x start_client.py

cp utils/uproar /etc/init.d/uproar
sed -i "s@uproardir@$PWD@g" "/etc/init.d/uproar"
chmod +x /etc/init.d/uproar
sudo update-rc.d uproar defaults 100

mv file_163.mp3 /media/startup.mp3

/etc/init.d/uproar start
