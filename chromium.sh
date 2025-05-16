#!/bin/bash
echo "Checking for Chrome and Chromedriver..."
google-chrome --version
chromedriver --version
which chromedriver
which google-chrome-stable

echo "Creating symlinks if needed..."
if [ ! -f /usr/bin/chromedriver ]; then
    CHROMEDRIVER_PATH=$(which chromedriver 2>/dev/null)
    if [ -n "$CHROMEDRIVER_PATH" ]; then
        echo "Found chromedriver at $CHROMEDRIVER_PATH, creating symlink"
        ln -sf $CHROMEDRIVER_PATH /usr/bin/chromedriver
    else
        echo "Searching for chromedriver..."
        find / -name chromedriver 2>/dev/null
    fi
fi