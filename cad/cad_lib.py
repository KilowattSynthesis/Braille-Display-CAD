def float_range(start: float, stop: float, step: float):
    while start < stop:
        # Round to avoid floating-point precision issues
        yield round(start, 10)
        start += step
