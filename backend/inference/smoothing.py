from collections import deque


class SlidingWindowSmoother:
    def __init__(self, window_size):
        self.values = deque(maxlen=max(1, int(window_size)))

    def add(self, value):
        self.values.append(float(value))
        return sum(self.values) / len(self.values)
