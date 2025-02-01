#from selenium import webdriver
import undetected_chromedriver as driver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

import os, threading
import pickle, pprint, time

class AutomateBrowser:
    def __init__(self, baseUrl, cookieFile, closeTimeout=5*60, headless=True):
        print("[AutomateBrowser.__init__]")

        # Save for later
        self.cookieFile = cookieFile
        self.baseUrl = baseUrl

        self.closeTimeout = closeTimeout
        self.lastCheckedOpen = time.time()
        self.timeoutThreadRunning = True
        self.timeoutThread = threading.Thread(target=self.browserCloseTimeout)
        self.timeoutThread.start()

        # Configure chrome options
        self.chrome_options = driver.ChromeOptions()
        self.chrome_options.add_argument('--no-sandbox')
        if (headless): self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--disable-gpu')
        self.chrome_options.add_argument('--single-process')
        self.chrome_options.add_argument('--no-zygote')
        self.chrome_options.add_argument("--window-size=1280,720")

        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument("--disable-extensions")
        self.chrome_options.add_argument("--disable-renderer-backgrounding")
        self.chrome_options.add_argument("--disable-background-timer-throttling")
        self.chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        self.chrome_options.add_argument("--disable-client-side-phishing-detection")
        self.chrome_options.add_argument("--disable-crash-reporter")
        self.chrome_options.add_argument("--disable-oopr-debug-crash-dump")
        self.chrome_options.add_argument("--no-crash-upload")
        self.chrome_options.add_argument("--silent")
        self.chrome_options.add_argument('log-level=3')
    
    def browserCloseTimeout(self):
        # Check if the browser had any activity for the last
        # closeTimeout period, and if not close the browser
        while self.timeoutThreadRunning:
            if (self.closeTimeout > 0): # only check if the closeTimeout is non-zero
                if ((time.time() - self.lastCheckedOpen) > self.closeTimeout):
                    if self.checkBrowserOpen():
                        print("[AutomateBrowser.browserCloseTimeout] closing browser")
                        self.closeBrowser()
                time.sleep(1)
            else:
                time.sleep(10)
    
    def openBrowser(self):
        # Open browser
        self.webdriver = driver.Chrome(options=self.chrome_options)
        self.webdriver.command_executor.set_timeout(10)

        # Setup wait for later
        self.wait = WebDriverWait(self.webdriver, 10)

        # Wait for it to open
        self.webdriver.get(self.baseUrl)
        #self.wait.until(EC.number_of_windows_to_be(1))
        
        # Wait for body tag again
        #self.wait.until(
        #    EC.presence_of_element_located((By.TAG_NAME, "body"))
        #)

        # Load cookies
        self.loadCookies()
        
        # Save the time for close timeout
        self.lastCheckedOpen = time.time()
    
    def checkBrowserOpen(self):
        try:
            # This will raise an exception if browser is not open
            temp = self.webdriver.window_handles
            return True
        except:
            return False

    def ensureBrowserOpen(self):
        # Make sure browser is open
        try:
            # This will raise an exception if browser is not open
            temp = self.webdriver.current_url
        except:
            self.openBrowser()
        finally:
            # Save the time for close timeout
            self.lastCheckedOpen = time.time()
    
    def closeBrowser(self):
        # Exit browser
        try:
            if self.checkBrowserOpen(): self.webdriver.quit()
        except:
            # Already closed
            pass
    
    def shutdown(self):
        self.timeoutThreadRunning = False
        self.closeBrowser()
    
    def saveCookies(self):
        if not self.checkBrowserOpen(): return

        print("[AutomateBrowser.saveCookies] saving cookies in " + self.cookieFile)
        pickle.dump(self.webdriver.get_cookies() , open(self.cookieFile,"wb"))
        pprint.pp(self.webdriver.get_cookies())

    def loadCookies(self):
        if not self.checkBrowserOpen(): return
        
        if os.path.exists(self.cookieFile) and os.path.isfile(self.cookieFile):
            print("[AutomateBrowser.loadCookies] loading cookies from " + self.cookieFile)
            cookies = pickle.load(open(self.cookieFile, "rb"))

            # Enables network tracking so we may use Network.setCookie method
            self.webdriver.execute_cdp_cmd('Network.enable', {})

            # Iterate through pickle dict and add all the cookies
            for cookie in cookies:
                # Fix issue Chrome exports 'expiry' key but expects 'expire' on import
                if 'expiry' in cookie:
                    cookie['expires'] = cookie['expiry']
                    del cookie['expiry']

                # Set the actual cookie
                self.webdriver.execute_cdp_cmd('Network.setCookie', cookie)

            # Disable network tracking
            self.webdriver.execute_cdp_cmd('Network.disable', {})
            return True

        print("[AutomateBrowser.loadCookies] cookie file " + self.cookieFile + " does not exist.")
        return False
