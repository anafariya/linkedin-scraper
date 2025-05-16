# chrome_version.py
import subprocess
import platform
import os
import logging

def get_chrome_version():
    """Get the installed Chrome version on various platforms"""
    logger = logging.getLogger(__name__)
    
    try:
        system = platform.system()
        logger.info(f"Detecting Chrome version on {system}")
        
        # Windows detection
        if system == "Windows":
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Google\Chrome\BLBeacon')
                version, _ = winreg.QueryValueEx(key, 'version')
                return version
            except:
                logger.warning("Could not get Chrome version from registry")
        
        # macOS detection
        elif system == "Darwin":
            try:
                process = subprocess.Popen(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--version'], 
                                          stdout=subprocess.PIPE)
                version = process.communicate()[0].decode('UTF-8').replace('Google Chrome ', '').strip()
                return version
            except:
                logger.warning("Could not get Chrome version on macOS")
        
        # Linux detection
        elif system == "Linux":
            try:
                # Try different Chrome binaries
                for binary in ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser']:
                    try:
                        process = subprocess.Popen([binary, '--version'], 
                                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        out, err = process.communicate()
                        out = out.decode('UTF-8')
                        if out:
                            version = out.replace('Google Chrome ', '').replace('Chromium ', '').strip()
                            return version
                    except:
                        continue
            except:
                logger.warning("Could not get Chrome version on Linux")
                
        logger.warning("Could not detect Chrome version using standard methods")
        
        # Try the chrome-version package if available
        try:
            from chrome_version import get_chrome_version as get_pkg_version
            version = get_pkg_version()
            if version:
                return version
        except:
            logger.warning("chrome-version package not available")
        
        return None
    
    except Exception as e:
        logger.error(f"Error detecting Chrome version: {e}")
        return None

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Print the detected Chrome version
    version = get_chrome_version()
    print(f"Detected Chrome version: {version}")