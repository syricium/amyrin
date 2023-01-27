SERVICE_FILE=./web.service
BASHRC_FILE=/home/$USER/.bashrc
BASHRC_LINE="export XDG_RUNTIME_DIR=/run/user/$(id -u)"

if [ $(echo $USER) = "root" ]; then
    echo "Running this script as root is not recommended, please create" \
    "a dedicated user with \"adduser username\", add it to the sudo group with" \
    "\"usermod -aG sudo username\" and remove it from the group with \"deluser username sudo\"" \
    "after running both setup scripts"
    exit 0
fi

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

echo "Script is done running, if you have run the bot's setup.sh script already, please remove" \
"sudo privileges from the user running the bot"
echo "Note: If you get \"Failed to connect to bus: Permission denied\" when trying to run systemctl --user," \
"try appending \"$BASHRC_LINE\" to your \"$BASHRC_FILE\" file"