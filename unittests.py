import unittest
import sys
from datetime import datetime
from process import handle_message_receipt, get_recipients, log_message_send 
from viz import get_clock_updates, get_queue_lengths, get_start_time, get_ticks, get_datetime, get_diff

class Tests(unittest.TestCase):
    def test_handle_message_receipt_clock_update(self):
        queue = [5]
        with open("testlog.txt", "w") as logFile:
            updated_clock = handle_message_receipt(queue, 3, logFile)
            self.assertEqual(updated_clock, 6)
        with open("testlog.txt", "r") as logFile:
            lines = logFile.readlines()
            l = lines[-1]
            self.assertTrue("[MESSAGE RECEIVED]" in l)
            self.assertTrue("Queue Length - 0" in l)
            self.assertTrue("Clock Time - 6" in l)
        
    def test_handle_message_receipt_clock_no_update(self):
        queue = [1]
        with open("testlog.txt", "w") as logFile:
            updated_clock = handle_message_receipt(queue, 3, logFile)
            self.assertEqual(updated_clock, 4)
        with open("testlog.txt", "r") as logFile:
            lines = logFile.readlines()
            l = lines[-1]
            self.assertTrue("[MESSAGE RECEIVED]" in l)
            self.assertTrue("Queue Length - 0" in l)
            self.assertTrue("Clock Time - 4" in l)
            
    def test_handle_message_receipt_clock_larger_queue(self):
        queue = [4, 6, 7]
        with open("testlog.txt", "w") as logFile:
            updated_clock = handle_message_receipt(queue, 1, logFile)
            self.assertEqual(updated_clock, 5)
        with open("testlog.txt", "r") as logFile:
            lines = logFile.readlines()
            l = lines[-1]
            self.assertTrue("[MESSAGE RECEIVED]" in l)
            self.assertTrue("Queue Length - 2" in l)
            self.assertTrue("Clock Time - 5" in l)
    
    def test_get_recipients(self):
        self.assertEqual(get_recipients(1), [0])
        self.assertEqual(get_recipients(2), [1])
        self.assertEqual(get_recipients(3), [0, 1])
        self.assertEqual(get_recipients(-1), [])
        self.assertEqual(get_recipients(4), [])
        
    def test_log_message_send(self):
        with open("testlog.txt", "w") as logFile:
            log_message_send([0], [0, 1], 3, logFile)
        with open("testlog.txt", "r") as logFile:
            lines = logFile.readlines()
            l = lines[-1]
            self.assertTrue("[MESSAGE(S) SENT]" in l)
            self.assertTrue("Receiver(s) - [0]" in l)
            self.assertTrue("Clock Time - 3" in l)
            
    def test_log_message_send_receiver_list(self):
        with open("testlog.txt", "w") as logFile:
            log_message_send([1], [0, 2], 2, logFile)
        with open("testlog.txt", "r") as logFile:
            lines = logFile.readlines()
            l = lines[-1]
            self.assertTrue("[MESSAGE(S) SENT]" in l)
            self.assertTrue("Receiver(s) - [2]" in l)
            self.assertTrue("Clock Time - 2" in l)
            
    def test_log_message_send_many_recipients(self):
        with open("testlog.txt", "w") as logFile:
            log_message_send([0, 1], [1, 2], 3, logFile)
        with open("testlog.txt", "r") as logFile:
            lines = logFile.readlines()
            l = lines[-1]
            self.assertTrue("[MESSAGE(S) SENT]" in l)
            self.assertTrue("Receiver(s) - [1, 2]" in l)
            self.assertTrue("Clock Time - 3" in l)
            
    def test_log_message_send_no_recipients(self):
        with open("testlog.txt", "w") as logFile:
            log_message_send([], [1, 2], 5, logFile)
        with open("testlog.txt", "r") as logFile:
            lines = logFile.readlines()
            l = lines[-1]
            self.assertTrue("[INTERNAL]" in l)
            self.assertTrue("No Messages Sent" in l)
            self.assertTrue("Clock Time - 5" in l)
            
    def test_get_datetime(self):
        self.assertEqual(datetime.strftime(get_datetime("00:00:00.001000"), "%H-%M-%S:%f"), "00-00-00:001000")
    
    def test_get_diff(self):
        d1 = get_datetime("00:01:10.000000")
        d2 = get_datetime("00:00:00.000000")
        self.assertEqual(get_diff(d1, d2), 70.)
        
    def test_get_clock_updates(self):
        res = get_clock_updates("testlogread.txt", get_datetime("00:00:00.000000"))
        self.assertEqual(len(res), 4)
        self.assertEqual(len(res[0]), 2)
        self.assertEqual(res, [(34., 2), (34.4, 4), (35.2, 8), (35.8, 11)])
        
    def test_get_queue_lengths(self):
        res = get_queue_lengths("testlogread.txt", get_datetime("00:00:00.000000"))
        self.assertEqual(len(res), 1)
        self.assertEqual(len(res[0]), 2)
        self.assertEqual(res, [(35.8, 0)])
    
if __name__ == "__main__":
    unittest.main()
    sys.exit(0)