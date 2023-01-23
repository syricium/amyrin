SERVICE_FILE=./web.service
if [ ! -f "$SERVICE_FILE" ]; then
    echo "web.service file has not yet been configured, please execute \"mv web.service.example web.service\" and then " \
    "configure it with an editor like nano or vim"
    exit 0
fi

sudo apt update -y
sudo apt upgrade -y
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install -y python3.11

curl -fsSL https://deb.nodesource.com/setup_19.x | sudo -E bash -
sudo apt-get install -y nodejs

mv web.service /etc/systemd/user/web.service

echo "Script is done running, if you have run the bot's setup.sh script already, please remove " \
"sudo privileges from the user running the bot, and if you don't have one, please create one"