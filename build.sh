#!/usr/bin/env bash
# Install Chrome and Chromedriver for Selenium on Render

echo "Starting Chrome and Chromedriver installation..."

# Exit on any error
set -e

# Install dependencies
apt-get update
apt-get install -y wget unzip apt-transport-https ca-certificates curl gnupg

# Install Chrome
echo "Installing Google Chrome..."
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google.list
apt-get update
apt-get install -y google-chrome-stable

# Print Chrome version for debugging
CHROME_VERSION=$(google-chrome --version)
echo "Installed Chrome version: $CHROME_VERSION"

# Extract major version number
CHROME_MAJOR_VERSION=$(echo "$CHROME_VERSION" | awk '{print $3}' | cut -d. -f1)
echo "Chrome major version: $CHROME_MAJOR_VERSION"

# Install matching chromedriver
echo "Installing Chromedriver..."
CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_MAJOR_VERSION")
echo "Using Chromedriver version: $CHROMEDRIVER_VERSION"

wget -q "https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip"
unzip chromedriver_linux64.zip
mv chromedriver /usr/local/bin/
chmod +x /usr/local/bin/chromedriver

# Print chromedriver version for debugging
CHROMEDRIVER_VERSION_INSTALLED=$(chromedriver --version)
echo "Installed Chromedriver: $CHROMEDRIVER_VERSION_INSTALLED"

# Clean up
rm chromedriver_linux64.zip

echo "Chrome and Chromedriver installation completed."

# Continue with your normal build steps
echo "Installing Python requirements..."
pip install -r requirements.txt

echo "Build script completed successfully."