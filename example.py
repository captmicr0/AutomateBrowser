from AutomateBrowser import AutomateBrowser
import os, sys, signal, threading, time
from functools import partial


os.environ['FOR_DISABLE_CONSOLE_CTRL_HANDLER'] = '1'

def shutdownSignalHandler(args, signum=99999, frame=None):
    ab, httpsrv = args
    print(f"[*] received signal {signum}. shutting down.")
    print("[*] shutting down SomeHTTPServer")
    httpsrv.shutdown()
    print("[*] shutting down AutomateBrowser")
    ab.shutdown()
    return True


from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

def runServer(server):
    server.serve_forever()

class SomeHTTPServer(BaseHTTPRequestHandler):
    def __init__(self, passed_argument, *args, **kwargs):
        self.passed_argument = passed_argument
        # BaseHTTPRequestHandler calls do_GET **inside** __init__ !!!
        # So we have to call super().__init__ after setting attributes.
        super().__init__(*args, **kwargs)
    
    #def log_message(self, format, *args):
    #    return

    def do_GET(self):
        print(f"[SomeHTTPServer] request INVALID")
        self.send_response(500)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(bytes("request invalid", "utf-8"))

if __name__ == "__main__":
    print("[*] AutomateBrowser example starting...")

    ab = AutomateBrowser("http://amazon.com",
                         './cookies.json',
                         headless=False,
                         undetectedDriver=True,
                         binary_location='K:/GitRepo/atozaccepter/chrome-win64/chrome.exe',
                         executeable_path='K:/GitRepo/atozaccepter/chromedriver-win64/chromedriver.exe')
    ab.openBrowser()
    
    # Setup SomeHTTPServer instance
    httpServerAddr = ('localhost', 8080)
    print("[*] httpServer init [ %s:%d ]" % httpServerAddr)
    httpServer = ThreadingHTTPServer(httpServerAddr, partial(SomeHTTPServer, "some argument to pass"))

    # Register the signal handler for SIGTERM
    signal.signal(signal.SIGTERM, partial(shutdownSignalHandler, (ab, httpServer)))
    signal.signal(signal.SIGINT, partial(shutdownSignalHandler, (ab, httpServer)))

    # Windows specific signal handler fix
    if sys.platform == "win32":
        import win32api
        win32api.SetConsoleCtrlHandler(partial(shutdownSignalHandler, (ab, httpServer)), True)
    
    # Create threads
    print("[*] creating threads")
    httpServerThread = threading.Thread(target=runServer, args=(httpServer,))

    # Start threads
    print("[*] starting threads")
    httpServerThread.start()

    # Wait for the server thread to finish
    httpServerThread.join()

    print("[*] AutomateBrowser example exiting...")
