SERVICE_FILE=./bot.service
if [ ! -f "$SERVICE_FILE" ]; then
    echo "bot.service file has not yet been configured, please execute \"mv bot.service.example bot.service\" and then " \
    "configure it with an editor like nano or vim"
    exit 0
fi

sudo apt update -y
sudo apt upgrade -y
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install -y python3.11

python3.11 -m pip install -r requirements.txt
sudo playwright install chromium
sudo playwright install-deps

mv bot.service /etc/systemd/user/bot.service

echo "Script is done running, if you have run the bot's setup.sh script already, please remove " \
"sudo privileges from the user running the bot, and if you don't have one, please create one"