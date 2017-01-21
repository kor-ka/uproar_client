apt-get update
apt-get install git
git clone https://github.com/kor-ka/uproar_client.git
cd uproar_client

apt-get -y install python-pip
apt-get -y install mpg123
pip install -r requirements.txt

cp utils/uproar /etc/init.d/uproar
sed -i "s@uproardir@$PWD@g" "/etc/init.d/uproar"
chmod +x /etc/init.d/uproar
sudo update-rc.d uproar defaults 100

chmod +x start_client.py
