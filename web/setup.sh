SERVICE_FILE=./web.service
BASHRC_FILE=~/.bashrc
BASHRC_LINE="export XDG_RUNTIME_DIR=/run/user/$(id -u)"

if [ ! -f "$SERVICE_FILE" ]; then
    echo "web.service file does not exist, please create it with \"touch web.service\" and then" \
    "configure it with an editor like nano or vim"
    exit 0
fi

sudo apt update -y
sudo apt upgrade -y
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install -y python3.11

curl -fsSL https://deb.nodesource.com/setup_19.x | sudo -E bash -
sudo apt-get install -y nodejs

mkdir -p ~/.config/systemd/user
sudo mv web.service ~/.config/systemd/user/web.service

echo "Script is done running, if you have run the bot's setup.sh script already, please remove " \
"sudo privileges from the user running the bot, and if you don't have one, please create one"