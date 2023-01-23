SERVICE_FILE=./bot.service
BASHRC_FILE=~/.bashrc
BASHRC_LINE="export XDG_RUNTIME_DIR=/run/user/$(id -u)"

if [ ! -f "$SERVICE_FILE" ]; then
    echo "bot.service file does not exist, please create it with \"touch bot.service\" and then" \
    "configure it with an editor like nano or vim"
    exit 0
fi

sudo apt update -y
sudo apt upgrade -y
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install -y python3.11

python3.11 -m pip install -r requirements.txt
python3.11 -m playwright install chromium
python3.11 -m playwright install-deps

mkdir -p ~/.config/systemd/user
sudo mv bot.service ~/.config/systemd/user/bot.service

echo "Script is done running, if you have run the web's setup.sh script already, please remove " \
"sudo privileges from the user running the bot, and if you don't have one, please create one"