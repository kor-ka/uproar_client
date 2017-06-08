# install git, clone and open project
apt-get update
apt-get -y install git
git clone https://github.com/kor-ka/uproar_client.git
cd uproar_client

# install deps
apt-get -y install python-pip
apt-get -y install mpg123
apt-get -y install mplayer
pip install -r requirements.txt

# install blink - shoudown with button
apt-get install i2c-tools
cd blink
cp gpio.sh /usr/local/bin/gpio.sh
cp blink.sh /usr/local/bin/blink.sh
chmod +x /usr/local/bin/blink.sh
cp blink.service /etc/systemd/system/blink.service
systemctl enable /etc/systemd/system/blink.service
cp blink.cfg /usr/local/etc/blink.cfg
sudo service blink start
cd ..

# make executable
chmod +x start_client.py
sed -i "s@YOUR_TOKEN_HERE@$1@g" "config.py"

# add daemon
cp utils/uproar /etc/init.d/uproar
sed -i "s@uproardir@$PWD@g" "/etc/init.d/uproar"
chmod +x /etc/init.d/uproar
sudo update-rc.d uproar defaults 100

# copy startup sound
mkdir /usr/uproar
cp startup.mp3 /usr/uproar/startup.mp3

# start daemon
/etc/init.d/uproar start
