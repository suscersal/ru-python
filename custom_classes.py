import time
class Timer:
    def __init__(self):
        self.start_time = time.time()

    def get_time(self):
        return round(time.time() - self.start_time,5)
        


t=Timer()
print(t.get_time())