import os
import signal



if __name__ == '__main__':
    try:
        pid = 59830
        os.kill(59830, signal.SIGTERM)
        print(f"Sent SIGTERM signal to process {pid}")
    except OSError:
        print(f"Failed to send SIGTERM signal to process {pid}")