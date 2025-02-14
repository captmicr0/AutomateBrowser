from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

import os, sys, threading, tempfile
import pickle, pprint, time, signal

class AutomateBrowser:
    def __init__(self,
                 baseUrl,
                 cookieFile,
                 closeTimeout=0,
                 headless=True,
                 undetectedDriver=False,
                 browser_executable_path='',
                 driver_executable_path=''):
        print("[AutomateBrowser.__init__]")

        # Save for later
        self.cookieFile = cookieFile
        self.baseUrl = baseUrl

        # Browser close timeout
        self.closeTimeout = closeTimeout
        self.lastCheckedOpen = time.time()
        self.timeoutThreadRunning = True
        self.timeoutThread = threading.Thread(target=self.browserCloseTimeout)
        self.timeoutThread.start()

        self.headless = headless

        self.undetectedDriver = undetectedDriver
        if undetectedDriver:
            import undetected_chromedriver as uc_driver
            self.driver = uc_driver
        else:
            from selenium import webdriver as sl_driver
            self.driver = sl_driver
        
        self.browser_executable_path = browser_executable_path
        self.driver_executable_path = driver_executable_path

        # Configure chrome options
        self.chrome_options = self.driver.ChromeOptions()
        self.chrome_options.add_argument('--no-sandbox')
        if (self.headless): self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--disable-gpu')
        if sys.platform != "win32":
            # this causes the browser to instantly close on windows, at least without headless
            self.chrome_options.add_argument('--single-process')
        self.chrome_options.add_argument('--no-zygote')
        self.chrome_options.add_argument("--window-size=1280,720")
        
        # Disable "Save password?" popup dialog
        self.chrome_options.add_experimental_option("prefs", {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False
        })

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
        if self.undetectedDriver:
            if (self.browser_executable_path and self.driver_executable_path):
                self.webdriver = self.driver.Chrome(
                    options=self.chrome_options,
                    browser_executable_path=self.browser_executable_path,
                    driver_executable_path=self.driver_executable_path)
            else:
                self.webdriver = self.driver.Chrome(
                    options=self.chrome_options)
        else:
            self.webdriver = self.driver.Chrome(
                options=self.chrome_options)
        
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
            temp = self.webdriver.window_handles
            return True
        except Exception as e:
            return False

    def ensureBrowserOpen(self):
        # Make sure browser is open
        if not self.checkBrowserOpen():
            self.openBrowser()

        self.lastCheckedOpen = time.time()
    
    def closeBrowser(self):
        # Exit browser
        try:
            if self.checkBrowserOpen():
                try:
                    self.webdriver.quit()
                except Exception as e:
                    print("[AutomateBrowser.closeBrowser] self.webdriver.quit() failed")
                    raise Exception(e)
            else:
                print("[AutomateBrowser.closeBrowser] browser not open")
        except Exception as e:
            print(f"[AutomateBrowser.closeBrowser] error: {e}")
            pass
    
    def shutdown(self):
        self.saveCookies()
        self.timeoutThreadRunning = False
        try:
            self.closeBrowser()
        except Exception as e:
            print(f"[AutomateBrowser.shutdown] error shutting down: {e}")
    
    def saveCookies(self):
        if not self.checkBrowserOpen():
            print("[AutomateBrowser.saveCookies] browser not open")
            return

        print("[AutomateBrowser.saveCookies] saving cookies in " + self.cookieFile)
        pickle.dump(self.webdriver.get_cookies() , open(self.cookieFile,"wb"))
        #pprint.pp(self.webdriver.get_cookies())

    def loadCookies(self):
        if not self.checkBrowserOpen():
            print("[AutomateBrowser.loadCookies] browser not open")
            return
        
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

    def inNewTabStart(self):
        # Open a new tab
        numWindowsBefore = len(self.webdriver.window_handles)
        windowBefore = self.webdriver.current_window_handle

        self.webdriver.switch_to.new_window('tab')

        # Wait until new tab is open
        self.wait.until(EC.number_of_windows_to_be(numWindowsBefore + 1))

        return (numWindowsBefore, windowBefore)

    def inNewTabEnd(self, newTabData):
        numWindowsBefore, windowBefore = newTabData

        # Close tab and switch to original window
        self.webdriver.close()
        self.webdriver.switch_to.window(windowBefore)
    
    def handleUnknowFormSituation(self):
        # Return a path to screenshot of current page
        # and a list of <form> <input>'s IDs and types
        print("[AutomateBrowser.handleUnknowFormSituation] Unknown <form> sitation handler")
        
        # Take screenshot of webpage
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            self.webdriver.save_screenshot(temp_file)
            print(f"[AutomateBrowser.handleUnknowFormSituation] Saved screenshot to {temp_file}")

        # Gather list of <form> inputs by ID
        print("[AutomateBrowser.handleUnknowFormSituation] List of <form> <input>'s on page")
        form_inputs = []
        try:
            forms = self.wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, "form")))
            for form in forms:
                inputs = form.find_elements(By.TAG_NAME, "input")
                for input_element in inputs:
                    input_name = input_element.get_attribute("name")
                    input_type = input_element.get_attribute("type")
                    input_hidden = input_element.get_attribute("hidden")
                    if input_name and (input_type != 'hidden') and (not input_hidden):
                        form_inputs.append((input_name, input_type))
                        print(f"[AutomateBrowser.handleUnknowFormSituation] <input name='{input_name}' type='{input_type}'/>")
        except Exception as e:
            print(f"[AutomateBrowser.handleUnknowFormSituation] Error finding form inputs: {str(e)}")
        
        return temp_file, form_inputs
