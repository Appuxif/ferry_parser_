sudo apt-get install unzip
sudo apt-get install -y libglib2.0-0 libnss3 libgconf-2-4  libfontconfig1

wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
sudo apt-get update -y
sudo apt-get install google-chrome-stable -y

rm ./chromedriver_linux64.zip
sudo rm /usr/local/bin/chromedriver

# Install ChromeDriver.
CHROME_LATEST_RELEASE="`wget -qO- https://chromedriver.storage.googleapis.com/LATEST_RELEASE`"
wget -N https://chromedriver.storage.googleapis.com/$CHROME_LATEST_RELEASE/chromedriver_linux64.zip -P ./
unzip ./chromedriver_linux64.zip -d ./
rm ./chromedriver_linux64.zip
sudo cp -f ./chromedriver /usr/local/bin/chromedriver
sudo chown root:root /usr/local/bin/chromedriver
sudo chmod 0755 /usr/local/bin/chromedriver

sudo cp -f ./chromedriver /usr/bin/chromedriver
sudo chown root:root /usr/bin/chromedriver
sudo chmod 0755 /usr/bin/chromedriver
